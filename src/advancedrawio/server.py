"""Servidor MCP de AdvanceDrawIO."""
from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from . import builder, drawio_cli, examples, icons
from .lint import lint

SPEC_DOC = """Spec JSON (tú defines estructura; el layout, estilos e iconos los pone el servidor):
{
  "title": "Plataforma IA",                  // opcional
  "direction": "RIGHT" | "DOWN",             // opcional, default RIGHT
  "layers": [{"id":"datos","name":"Flujo de datos","visible":true,"color":"#34A853"}],
  "zones":  [{"id":"gcp","label":"Google Cloud","kind":"cloud|zone|external|plain","parent":null}],
  "nodes":  [{"id":"bq","label":"Analítica","product":"BigQuery","kind":"card|box|actor|database","zone":"gcp"}],
  "edges":  [{"from":"a","to":"b","label":"REST","layer":"datos","dashed":false,"bidirectional":false,"step":1}],
  "notes":  [{"text":"SLA 99.9%","near":"bq"}]
}
Estilos libres (copiados de get_example o search_shapes): cualquier node/zone/edge acepta "style"
(string draw.io); los nodes aceptan además "w" y "h". En un style de receta, "image=<icono>" se
reemplaza por el icono de "product".
Reglas: ids únicos; 'product' debe ser un nombre devuelto por search_icons; los edges sin
'layer' van a la capa Base; las capas con visible=false quedan ocultas y se activan desde la
leyenda clicable; 'notes' crea la capa Anotaciones. Máx. ~25 nodos por diagrama."""

mcp = MCPServer(
    "advancedrawio",
    instructions=("Genera diagramas draw.io de arquitectura avanzados. Flujo: 1) search_icons para cada "
                  "producto, 2) build_diagram con el spec, 3) mira el PNG devuelto y corrige el spec si hay "
                  "cruces o nodos mal agrupados. Nunca escribas XML ni coordenadas.\n\n" + SPEC_DOC),
)

AGENT = (Path(__file__).parent / "agent.md").read_text(encoding="utf-8")


@mcp.prompt(name="arquitecto_drawio", title="Arquitecto de diagramas draw.io",
            description="Agente que diseña, construye y corrige el diagrama hasta que pase la revisión.")
def arquitecto_drawio(sistema: str) -> str:
    return f"{AGENT}\n\n## Sistema a diagramar\n\n{sistema}"


OUT = os.environ.get("ADVANCEDRAWIO_OUT", str(Path.cwd() / "diagramas"))


@mcp.tool()
def search_icons(query: str, limit: int = 10) -> list[str]:
    """Busca iconos (GCP, AWS, Azure, marcas...). Usa el título exacto devuelto como 'product'."""
    return icons.search(query, limit)


@mcp.tool()
def spec_reference() -> str:
    """Formato del spec JSON de build_diagram."""
    return SPEC_DOC


@mcp.tool()
def build_diagram(spec: dict, name: str = "diagrama", out_dir: str | None = None,
                  formats: list[str] | None = None) -> list:
    """Construye el diagrama (layout ELK, capas, leyenda) y devuelve rutas + PNG para revisarlo."""
    fmts = tuple(formats or ["png"])
    if "png" not in fmts:
        fmts = fmts + ("png",)
    try:
        res = builder.build(spec, out_dir or OUT, name, fmts)
    except (ValueError, RuntimeError) as e:
        raise ToolError(str(e)) from e
    res["revision"] = lint(res["drawio"])
    return [json.dumps(res, ensure_ascii=False, indent=1), Image(path=res["png"])]


def _deliver(res: dict) -> list:
    res["revision"] = lint(res["drawio"])
    return [json.dumps(res, ensure_ascii=False, indent=1), Image(path=res["png"])]


@mcp.tool()
def find_examples(tipo: str | None = None, query: str | None = None, patron: str | None = None,
                  libreria: str | None = None, limit: int = 8) -> dict:
    """Busca entre los 770 ejemplos oficiales de jgraph. Sin argumentos devuelve los tipos disponibles.
    patron: capas, capas-interactivas, contenedores, tablas, metadatos, links, iconos-imagen, multi-pagina, anidado."""
    if not any([tipo, query, patron, libreria]):
        return {"tipos": examples.types(), "modos": {"spec": "build_diagram", "mermaid": "build_from_mermaid",
                                                      "plantilla": "build_from_example"}}
    return {"ejemplos": examples.find(tipo, query, patron, libreria, limit)}


@mcp.tool()
def get_example(example_id: str) -> list:
    """Receta de un ejemplo: estilos por rol (zonas, nodos, iconos, edges, textos), capas, textos
    reemplazables y su imagen. Copia los styles al spec en vez de inventarlos."""
    try:
        data = examples.recipe(example_id)
        data["textos"] = examples.texts(example_id)
        png = examples.preview(example_id)
        if png is None:
            png = examples.download(example_id).with_suffix(".render.png")
            if not png.exists():
                drawio_cli.export(str(examples.download(example_id)), str(png), "png", scale=1)
    except (ValueError, RuntimeError, OSError) as e:
        raise ToolError(str(e)) from e
    return [json.dumps(data, ensure_ascii=False, indent=1), Image(path=str(png))]


@mcp.tool()
def search_shapes(query: str, limit: int = 8) -> list[dict]:
    """Stencils vectoriales (AWS, Azure, Cisco, BPMN, UML, redes, P&ID...) con su style y tamaño,
    para usar como node {"style":..., "w":..., "h":...}. Para iconos GCP usa search_icons."""
    return icons.search_shapes(query, limit)


@mcp.tool()
def build_from_mermaid(code: str, name: str = "diagrama", out_dir: str | None = None) -> list:
    """Construye desde Mermaid (ER, secuencia, clases, estados, gantt, mindmap, git). draw.io lo
    convierte en shapes nativos editables y los acomoda."""
    try:
        return _deliver(builder.build_mermaid(code, out_dir or OUT, name))
    except (ValueError, RuntimeError) as e:
        raise ToolError(str(e)) from e


@mcp.tool()
def build_from_example(example_id: str, replacements: dict[str, str], name: str = "diagrama",
                       out_dir: str | None = None) -> list:
    """Copia un ejemplo oficial y reemplaza sus textos ({"texto viejo": "texto nuevo"}). Para planos,
    infografías, wireframes, canvases de negocio: todo lo que depende del diseño y no del layout."""
    out = Path(out_dir or OUT).expanduser().resolve()
    try:
        drawio = examples.from_template(example_id, replacements, out / f"{name}.drawio")
        png = out / f"{name}.drawio.png"
        drawio_cli.export(str(drawio), str(png), "png")
    except (ValueError, RuntimeError, OSError) as e:
        raise ToolError(str(e)) from e
    return _deliver({"drawio": str(drawio), "png": str(png)})


@mcp.tool()
def lint_diagram(path: str) -> dict:
    """Revisión objetiva de un .drawio: solapes, edges que cruzan nodos, nodos aislados, proporción."""
    try:
        return lint(path)
    except (OSError, ValueError) as e:
        raise ToolError(f"No pude leer {path}: {e}") from e


@mcp.tool()
def render(path: str) -> Image:
    """Renderiza un .drawio existente a PNG para revisarlo visualmente."""
    out = str(Path(path).with_suffix(".preview.png"))
    try:
        drawio_cli.export(path, out, "png")
    except RuntimeError as e:
        raise ToolError(str(e)) from e
    return Image(path=out)


@mcp.tool()
def doctor() -> dict:
    """Verifica que draw.io Desktop y el índice de iconos estén disponibles."""
    exe = drawio_cli.find()
    try:
        n = len(icons._index())
    except Exception as e:  # noqa: BLE001
        n = f"error: {e}"
    return {"drawio": exe or "NO ENCONTRADO", "iconos_indexados": n, "salida": OUT}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

"""Servidor MCP de AdvanceDrawIO."""
from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from . import builder, drawio_cli, icons

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
Reglas: ids únicos; 'product' debe ser un nombre devuelto por search_icons; los edges sin
'layer' van a la capa Base; las capas con visible=false quedan ocultas y se activan desde la
leyenda clicable; 'notes' crea la capa Anotaciones. Máx. ~25 nodos por diagrama."""

mcp = MCPServer(
    "advancedrawio",
    instructions=("Genera diagramas draw.io de arquitectura avanzados. Flujo: 1) search_icons para cada "
                  "producto, 2) build_diagram con el spec, 3) mira el PNG devuelto y corrige el spec si hay "
                  "cruces o nodos mal agrupados. Nunca escribas XML ni coordenadas.\n\n" + SPEC_DOC),
)

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
    return [json.dumps(res, ensure_ascii=False), Image(path=res["png"])]


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

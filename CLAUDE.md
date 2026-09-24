# AdvanceDrawIO — contexto para Claude Code

MCP en Python (SDK `mcp` 2.x, `MCPServer`, no FastMCP) que genera diagramas draw.io de arquitectura.
El LLM escribe un spec JSON; el servidor pone iconos, layout ELK, capas, leyenda y revisión.
Dueño: Erick Sang. Preferencia: soluciones mínimas, sin sobreingeniería.

## Comandos

```bash
bash scripts/setup-cloud.sh && source .venv/bin/activate  # draw.io + xvfb + paquete en .venv (VM cloud)
ruff check src tests scripts && pytest -q       # los tests con draw.io real se saltan si no está
advancedrawio-build examples/plataforma-ia-gcp.json -o diagramas   # también .mmd y .plantilla.json
python scripts/galeria.py                        # todos los ejemplos -> docs/galeria (PNG, .drawio, puntajes)
advancedrawio-build --search "bigquery"          # nombres exactos de iconos
python -c "from advancedrawio.lint import lint; print(lint('diagramas/X.drawio'))"
```

## Mapa del código (`src/advancedrawio/`)

- `icons.py`: índice oficial de jgraph (descarga y cache en `~/.cache/advancedrawio`) más SVG en `icons/`.
  143 iconos GCP del índice traen el base64 como título; el nombre se recupera de los tags.
- `components.py`: estilos extraídos de la plantilla GCP oficial (tarjeta `shape=label` con icono,
  zonas, edges). Las zonas llevan `akind=<tipo>` en el style para que el linter las distinga.
- `builder.py`: spec → borrador → `drawio --layout elkLayered` (INCLUDE_CHILDREN) → `_finish`.
  `_finish` restaura el tamaño de los nodos (ELK los ensancha al ancho de la etiqueta), mueve cada edge
  a su capa convirtiendo sus waypoints a coordenadas absolutas, y añade notas, título y leyenda
  (toggles `data:action/json`).
- `lint.py`: revisión objetiva (solapes, edges que cruzan nodos, nodos aislados, zonas vacías,
  proporción) con puntaje 0–100. Se aprueba con ≥85.
- `server.py`: tools `search_icons`, `spec_reference`, `build_diagram` (devuelve rutas, `revision` y el
  PNG), `lint_diagram`, `render` y `doctor`, más el prompt MCP `arquitecto_drawio`.
- `examples.py` + `catalog.json`: los 770 ejemplos de jgraph (23 tipos, modos spec/mermaid/plantilla).
  `recipe()` extrae estilos por rol y `from_template()` reemplaza por **texto visible** conservando el HTML
  (las plantillas suelen duplicar el texto en una celda plana y otra HTML).
- `xmlio.py`: lectura de `.drawio` que descomprime páginas guardadas como deflate+base64.
- `agent.md`: prompt del agente (proceso + playbook). **Fuente única**: `.claude/agents/drawio-architect.md`
  debe tener el mismo cuerpo (hay un test que lo verifica).

## Lecciones aprendidas (no repetir)

- `--layout libavoid` se cuelga en headless. No usarlo.
- Si se borran los waypoints de ELK, draw.io re-rutea peor. Conservarlos siempre.
- Nunca `pkill -f drawio` dentro de un comando que contenga "drawio": se mata a sí mismo.
- Los errores de spec deben lanzarse como `ToolError`; si no, el modelo recibe un mensaje genérico
  y no puede autocorregirse.
- Las tablas (`childLayout=`) son un solo nodo para el linter; sus filas son partes.
- `search_shapes`: el ranking prefiere librerías oficiales vigentes (aws4, azure2, cisco19, kubernetes)
  y la coincidencia exacta del recurso en el style. Los iconos Azure son `image=img/lib/azure2/...`.
- Clasificación del catálogo: primero el nombre del archivo, luego la carpeta, luego las librerías.
  Coincidencia por inicio de palabra ("flowchart" no es "chart"; "floor_plan" no es "lan").
- Un puntaje de 100 no garantiza un buen diagrama. El linter no ve zonas que flotan porque sus edges
  están en capas ocultas, ni los huecos grandes. Por eso el agente también revisa el PNG.

## Estado y siguiente paso

Validación del agente con los ejemplos (resultados en `docs/galeria/revision.json`, que regenera el CI):
- `plataforma-recaudo`: iteración 1 → 92 (zona Control flotaba, bug de colores corregido); iteración 2 → 92
  (`proporcion_extrema` 4.2); **iteración 3, `direction: DOWN` → 100**.
- `DOWN` también dejó en 100 a `plataforma-ia-gcp` (antes 80, proporción 7.3), `multiagente-gcp` y
  `como-funciona`. En `aws-serverless` empeoró (9.6): la cadena es larga y lineal, se queda en `RIGHT`.
- El modo plantilla tenía un bug (reemplazaba "S" dentro de textos ya reemplazados). Corregido, con test.

Pendientes:
1. Revisión de notas: detectar cuando una nota pisa el borde de una zona (pasa en plataforma-ia-gcp con DOWN).
2. Detectar huecos grandes (plataforma-ia-gcp con DOWN deja mucho aire entre Canales y Google Cloud).
3. Validar el modo plantilla con más tipos (planos, wireframes, eléctricos).
4. Iconos de Vertex AI y Gemini: los aporta Erick en `icons/` (no están en el índice de draw.io).

## Reglas del repo

- El repo es **público**: los ejemplos, imágenes y docs no llevan nombres de clientes, empresas,
  proyectos ni datos internos. Usa escenarios genéricos.
- `docs/galeria/` la genera el workflow `galería` en cada push que toca `examples/` o el código. No
  se edita a mano; haz `git pull` antes de seguir trabajando para traer su commit.

## Sesiones cloud

- El paquete se instala en `.venv` (el pip del sistema choca con PyJWT de Debian).
- Si la red del entorno no permite las descargas de releases de github.com, draw.io no se instala:
  el setup avisa y sigue, y el test con draw.io real se salta. Para ver el resultado igual, haz push:
  el CI construye la galería con draw.io real y la commitea (ver docs/cloud.md).

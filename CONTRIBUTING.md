# Cómo contribuir

Gracias por el interés. AdvanceDrawIO prefiere soluciones mínimas: una función más antes que una
abstracción nueva, y un ejemplo que lo demuestre antes que una opción de configuración.

## Entorno

```bash
git clone https://github.com/Leonsang/AdvanceDrawIO.git && cd AdvanceDrawIO
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
ruff check src tests scripts && pytest -q
```

Los tests que necesitan draw.io Desktop se saltan si no lo encuentran. El CI los corre siempre en el
job `e2e`. En una sesión en la nube de Claude Code, usa `scripts/setup-cloud.sh` ([docs/cloud.md](docs/cloud.md)).

## Qué revisa el CI

| Job | Qué hace |
|---|---|
| `lint` | `ruff check` con la configuración de `pyproject.toml` |
| `test` | `pytest` en Linux, macOS y Windows, con Python 3.10 y 3.13 |
| `e2e` | Instala draw.io Desktop, corre todos los tests y construye cada ejemplo. Falla si alguno de modo spec queda por debajo de 85 |
| `galería` | Regenera `docs/galeria` y la commitea en la rama |

## Agregar un ejemplo

1. Crea `examples/<nombre>.json` (spec), `<nombre>.mmd` (Mermaid, con `%% title: ...` en la primera
   línea) o `<nombre>.plantilla.json` (`{"titulo", "ejemplo", "reemplazos"}`).
2. `pytest -q` valida el spec y comprueba que cada `product` tenga icono en el índice.
3. Haz push: la galería se regenera y te dice el puntaje. Si queda por debajo de 85, aplica el
   playbook de [`agent.md`](src/advancedrawio/agent.md) como lo haría el agente.

Los ejemplos son públicos: no uses nombres de clientes, proyectos ni datos internos.

## Cambiar el prompt del agente

`src/advancedrawio/agent.md` es la fuente única. `.claude/agents/drawio-architect.md` debe tener el
mismo cuerpo debajo de su frontmatter (un test lo verifica).

## Lecciones aprendidas

Antes de tocar el layout, lee la sección *Lecciones aprendidas* de [CLAUDE.md](CLAUDE.md): hay
opciones de draw.io que se cuelgan en headless y atajos que empeoran el ruteo.

## Publicar una versión

1. Sube la versión en `pyproject.toml` y `src/advancedrawio/__init__.py`.
2. Escribe `release-notes/vX.Y.Z.md`.
3. `git tag vX.Y.Z && git push --tags`. El workflow `release` construye el wheel y crea el release.

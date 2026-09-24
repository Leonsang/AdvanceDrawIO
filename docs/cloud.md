# Sesiones en la nube de Claude Code

AdvanceDrawIO funciona en una sesión en la nube de Claude Code (claude.ai/code, `claude --cloud`).
El repo trae lo necesario para prepararla.

```bash
bash scripts/setup-cloud.sh && source .venv/bin/activate
pytest -q
```

`scripts/setup-cloud.sh` instala draw.io Desktop (el `.deb` del último release) y `xvfb`, crea `.venv`
e instala el paquete con sus dependencias de desarrollo. Usa un venv porque el `pip` del sistema choca
con el PyJWT que trae Debian.

## Acceso a la red

El entorno en la nube necesita alcanzar:

| Host | Para qué |
|---|---|
| `github.com`, `release-assets.githubusercontent.com` | Descargar draw.io Desktop |
| `raw.githubusercontent.com` | Índice de iconos y ejemplos de jgraph |
| `pypi.org`, `files.pythonhosted.org` | Dependencias de Python |

Si la política de red no permite las descargas de releases de GitHub, el setup avisa y sigue sin
draw.io: los tests que lo necesitan se saltan y no hay layout ni PNG. Para habilitarlo, en la barra
de título de la sesión abre el menú del entorno, elige **Edit** y agrega esos hosts en **Network
access**, o sube el nivel de acceso. La guía oficial está en
[code.claude.com/docs/en/claude-code-on-the-web](https://code.claude.com/docs/en/claude-code-on-the-web).

## Sin draw.io en la sesión

Aunque la sesión no tenga draw.io, el CI sí lo tiene. Cada push que toca `examples/` o el código
dispara el workflow **galería**, que reconstruye todos los ejemplos con draw.io real y commitea el
resultado en `docs/galeria/` de la misma rama. Después de un `git pull` puedes ver los PNG y los
puntajes (`docs/galeria/revision.json`) sin haber instalado nada.

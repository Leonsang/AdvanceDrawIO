#!/usr/bin/env bash
# Setup para sesiones cloud de Claude Code (Ubuntu). Instala draw.io Desktop headless + el paquete.
set -euo pipefail
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
if ! command -v drawio >/dev/null 2>&1; then
  V=$(curl -fsI https://github.com/jgraph/drawio-desktop/releases/latest | grep -i '^location' | sed 's#.*/tag/v##' | tr -d '\r' || true)
  if [ -z "$V" ]; then
    echo "AVISO: no se pudo descargar draw.io Desktop (¿red de la sesión bloquea github.com releases?)." >&2
    echo "       Se sigue sin draw.io; los tests que lo necesitan se saltan." >&2
  else
    curl -fsSL -o /tmp/drawio.deb "https://github.com/jgraph/drawio-desktop/releases/download/v${V}/drawio-amd64-${V}.deb"
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq /tmp/drawio.deb xvfb >/dev/null
  fi
fi
# venv: evita choques con paquetes de Debian (p. ej. PyJWT sin RECORD).
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -e ".[dev]"
.venv/bin/python -c "from advancedrawio import drawio_cli; print('draw.io:', drawio_cli.find())"
echo "Listo. Usa .venv/bin/pytest -q  (o: source .venv/bin/activate)"

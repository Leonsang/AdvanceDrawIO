#!/usr/bin/env bash
# Setup para sesiones cloud de Claude Code (Ubuntu). Instala draw.io Desktop headless + el paquete.
set -euo pipefail
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
if ! command -v drawio >/dev/null 2>&1; then
  V=$(curl -fsI https://github.com/jgraph/drawio-desktop/releases/latest | grep -i '^location' | sed 's#.*/tag/v##' | tr -d '\r')
  curl -fsSL -o /tmp/drawio.deb "https://github.com/jgraph/drawio-desktop/releases/download/v${V}/drawio-amd64-${V}.deb"
  $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq /tmp/drawio.deb xvfb >/dev/null
fi
pip install -q -e ".[dev]" 2>/dev/null || pip install -q --break-system-packages -e ".[dev]"
python -c "from advancedrawio import drawio_cli; print('draw.io:', drawio_cli.find())"

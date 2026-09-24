"""Localiza y ejecuta el CLI de draw.io Desktop (layout ELK + export)."""
from __future__ import annotations

import glob
import json
import os
import platform
import shutil
import subprocess

CANDIDATES = [
    "/Applications/draw.io.app/Contents/MacOS/draw.io",
    r"C:\Program Files\draw.io\draw.io.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\draw.io\draw.io.exe"),
    "/mnt/c/Program Files/draw.io/draw.io.exe",
    "/opt/drawio/drawio",
]


def find() -> str | None:
    env = os.environ.get("DRAWIO_BIN")
    if env and os.path.exists(env):
        return env
    for name in ("drawio", "draw.io"):
        if shutil.which(name):
            return shutil.which(name)
    for c in CANDIDATES + glob.glob("/mnt/*/Program Files/draw.io/draw.io.exe"):
        if os.path.exists(c):
            return c
    return None


def _needs_no_sandbox() -> bool:
    """Chromium exige --no-sandbox solo como root (contenedores, CI). Fuera de eso el sandbox se queda:
    es lo que contiene un .drawio malicioso. ADVANCEDRAWIO_NO_SANDBOX=1 lo fuerza donde no hay sandbox."""
    return os.environ.get("ADVANCEDRAWIO_NO_SANDBOX") == "1" or (hasattr(os, "geteuid") and os.geteuid() == 0)


def _abs(path: str) -> str:
    """Las rutas van absolutas al CLI: una ruta que empiece con '-' sería una opción de Electron/Chromium,
    y algunas (--renderer-cmd-prefix, --gpu-launcher) ejecutan comandos."""
    return os.path.abspath(path)


def run(args: list[str], timeout: int = 120) -> None:
    exe = find()
    if not exe:
        raise RuntimeError("No encuentro draw.io Desktop. Instálalo (https://get.diagrams.net) "
                           "o define DRAWIO_BIN con la ruta del ejecutable.")
    cmd = [exe, *args, "--disable-gpu"]
    if platform.system() == "Linux":
        if _needs_no_sandbox():
            cmd.append("--no-sandbox")
        if not os.environ.get("DISPLAY") and shutil.which("xvfb-run"):
            cmd = ["xvfb-run", "-a", *cmd]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = args[args.index("-o") + 1] if "-o" in args else None
    if r.returncode != 0 or (out and not os.path.exists(out)):
        raise RuntimeError(f"draw.io falló ({r.returncode}): {r.stderr[-800:]}")


def layout(path: str, direction: str = "RIGHT", spacing: int = 40) -> None:
    cfg = json.dumps([{"layout": "elkLayered", "config": {
        "elk.direction": direction, "elk.spacing.nodeNode": str(spacing),
        "elk.layered.spacing.nodeNodeBetweenLayers": str(int(spacing * 1.8)),
        "elk.hierarchyHandling": "INCLUDE_CHILDREN"}}], separators=(",", ":"))
    path = _abs(path)
    run(["-x", "-f", "xml", "--layout", cfg, "-o", path, path])


def export(src: str, out: str, fmt: str = "png", scale: float = 1.5) -> None:
    src, out = _abs(src), _abs(out)
    args = ["-x", "-f", fmt, "-b", "20", "-o", out]
    if fmt in ("png", "svg", "pdf"):
        args.insert(3, "-e")
    if fmt == "png":
        args += ["-s", str(scale)]
    run(args + [src])

"""CLI: advancedrawio-build spec.json|diagrama.mmd|x.plantilla.json [-o salida] [-n nombre] [-f png svg pdf] [--min-score 85]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import builder, icons
from .lint import lint


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="advancedrawio-build")
    ap.add_argument("spec", nargs="?", help="spec .json, .mmd (Mermaid) o .plantilla.json ({ejemplo, reemplazos})")
    ap.add_argument("-o", "--out", default="diagramas")
    ap.add_argument("-n", "--name")
    ap.add_argument("-f", "--formats", nargs="*", default=["png"])
    ap.add_argument("--min-score", type=int, help="sale con código 1 si la revisión queda por debajo")
    ap.add_argument("--search", help="buscar iconos en vez de construir")
    a = ap.parse_args(argv)
    if a.search:
        sys.stdout.write("\n".join(icons.search(a.search, 20)) + "\n")
        return 0
    if not a.spec:
        ap.error("falta spec.json, diagrama.mmd o x.plantilla.json")
    src = Path(a.spec)
    text = src.read_text(encoding="utf-8")
    name, fmts = a.name or src.name.split(".")[0], tuple(a.formats)
    if src.suffix == ".mmd":
        res = builder.build_mermaid(text, a.out, name, fmts)
    elif src.name.endswith(".plantilla.json"):
        t = json.loads(text)
        res = builder.build_template(t["ejemplo"], t["reemplazos"], a.out, name, fmts)
    else:
        res = builder.build(json.loads(text), a.out, name, fmts)
    res["revision"] = lint(res["drawio"])
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if a.min_score is not None and res["revision"]["puntaje"] < a.min_score:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""CLI: advancedrawio-build spec.json [-o salida] [-n nombre] [-f png svg pdf]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import builder, icons


def main() -> None:
    ap = argparse.ArgumentParser(prog="advancedrawio-build")
    ap.add_argument("spec", nargs="?")
    ap.add_argument("-o", "--out", default="diagramas")
    ap.add_argument("-n", "--name")
    ap.add_argument("-f", "--formats", nargs="*", default=["png"])
    ap.add_argument("--search", help="buscar iconos en vez de construir")
    a = ap.parse_args()
    if a.search:
        sys.stdout.write("\n".join(icons.search(a.search, 20)) + "\n")
        return
    if not a.spec:
        ap.error("falta spec.json")
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    print(json.dumps(builder.build(spec, a.out, a.name or Path(a.spec).stem, tuple(a.formats)), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

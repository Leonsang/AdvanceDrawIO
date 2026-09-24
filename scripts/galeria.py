#!/usr/bin/env python3
"""Construye todos los ejemplos y regenera la galería: PNG, .drawio y tabla de revisión.

    python scripts/galeria.py                  # -> docs/galeria/
    python scripts/galeria.py -o /tmp/g --min-score 85

Necesita draw.io Desktop (el CI lo instala con scripts/setup-cloud.sh).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

from advancedrawio import builder
from advancedrawio.lint import lint

ROOT = Path(__file__).resolve().parents[1]
RAW = "https://raw.githubusercontent.com/Leonsang/AdvanceDrawIO/main/docs/galeria"


def build_one(src: Path, tmp: Path) -> dict:
    text = src.read_text(encoding="utf-8")
    if src.suffix == ".mmd":
        res = builder.build_mermaid(text, str(tmp), src.stem)
        title = next((ln.split(":", 1)[1].strip() for ln in text.splitlines() if ln.startswith("%% title:")), src.stem)
        mode = "mermaid"
    else:
        spec = json.loads(text)
        res = builder.build(spec, str(tmp), src.stem)
        title, mode = spec.get("title", src.stem), "spec"
    return {"nombre": src.stem, "titulo": title, "modo": mode, "fuente": src.name, **res, "revision": lint(res["drawio"])}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=str(ROOT / "docs" / "galeria"))
    ap.add_argument("--min-score", type=int, default=0)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sources = sorted((ROOT / "examples").glob("*.json")) + sorted((ROOT / "examples").glob("*.mmd"))
    rows, failed = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for src in sources:
            try:
                r = build_one(src, Path(tmp))
            except Exception as e:  # noqa: BLE001 - se reporta y sigue con el resto
                failed.append(f"{src.name}: {e}")
                print(f"FALLÓ {src.name}: {e}", file=sys.stderr)
                continue
            shutil.copy(r["drawio"], out / f"{r['nombre']}.drawio")
            shutil.copy(r["png"], out / f"{r['nombre']}.png")
            rev = r["revision"]
            print(f"{r['nombre']:<22} {rev['puntaje']:>3}  {', '.join(i['tipo'] for i in rev['problemas']) or '-'}")
            if r["modo"] == "spec" and rev["puntaje"] < a.min_score:
                failed.append(f"{src.name}: puntaje {rev['puntaje']} < {a.min_score}")
            rows.append(r)
    lines = ["# Galería", "",
             "Generada por `scripts/galeria.py` a partir de [`examples/`](../../examples). No la edites a mano:",
             "el workflow **galería** la regenera.", "",
             "| Ejemplo | Modo | Nodos | Revisión | Abrir |", "|---|---|---|---|---|"]
    for r in rows:
        rev = r["revision"]
        problems = ", ".join(sorted({i["tipo"] for i in rev["problemas"]})) or "sin problemas"
        lines.append(f"| [{r['titulo']}](../../examples/{r['fuente']}) | {r['modo']} | {rev['nodos']} | "
                     f"{rev['puntaje']} · {problems} | [draw.io](https://app.diagrams.net/#U{RAW}/{r['nombre']}.drawio) |")
    lines.append("")
    for r in rows:
        lines += [f"## {r['titulo']}", "", f"![{r['nombre']}]({r['nombre']}.png)", ""]
    (out / "README.md").write_text("\n".join(lines), encoding="utf-8")
    (out / "revision.json").write_text(json.dumps({r["nombre"]: r["revision"] for r in rows}, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    for f in failed:
        print("ERROR", f, file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

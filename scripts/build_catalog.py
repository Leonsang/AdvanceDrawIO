"""Genera src/advancedrawio/catalog.json a partir de clones locales de jgraph/drawio y jgraph/drawio-diagrams.

    git clone --depth 1 --filter=blob:none --sparse https://github.com/jgraph/drawio.git /tmp/drawio
    git -C /tmp/drawio sparse-checkout set src/main/webapp/templates
    git clone --depth 1 https://github.com/jgraph/drawio-diagrams.git /tmp/drawio-diagrams
    python scripts/build_catalog.py /tmp/drawio /tmp/drawio-diagrams
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

TYPES = [  # (tipo, prefijos de palabra en ruta/librerías) — el primero que coincide gana
    ("git", ["git"]),
    ("flowchart", ["flowchart", "flow_chart", "swimlane"]),
    ("arquitectura-software", ["c4", "component", "eip", "microservice", "architecture", "deployment"]),
    ("cloud-gcp", ["gcp"]), ("cloud-aws", ["aws"]), ("cloud-azure", ["azure", "mscae"]),
    ("cloud-otros", ["ibm", "cloud", "kubernetes", "citrix", "veeam"]),
    ("red", ["network", "cisco", "arista", "fortinet", "lan", "internet", "telecomm"]),
    ("bpmn", ["bpmn"]), ("uml-secuencia", ["sequence"]), ("uml", ["uml", "class", "activity", "sysml", "use_case"]),
    ("er-datos", ["entity", "database", "erd", "er"]),
    ("flujo-datos", ["data_flow", "dataflow", "pipeline", "etl", "sankey"]),
    ("git", ["git"]), ("organigrama", ["org", "orgchart"]), ("mapa-mental", ["mind"]),
    ("gantt-tablas", ["gantt", "table", "kanban", "timeline", "roadmap"]),
    ("wireframe", ["wireframe", "mockup", "ios", "android", "hero"]),
    ("plano", ["floor", "floorplan"]), ("electrico-ingenieria", ["electr", "pid", "engineering", "cabinet", "rack"]),
    ("infografia", ["infographic", "venn", "chart", "signs"]),
    ("negocio", ["business", "ishikawa", "swot", "canvas", "lean", "value", "5c", "marketing"]),
    ("conceptual", ["concept", "decision", "tree", "cycle", "site", "block", "map"]),
]
MODE = {  # cómo debe construirlo el agente
    "mermaid": {"uml-secuencia", "uml", "er-datos", "git", "mapa-mental", "gantt-tablas"},
    "plantilla": {"wireframe", "plano", "electrico-ingenieria", "infografia", "negocio"},
}
SOURCES = {
    "drawio": ("src/main/webapp/templates", "https://raw.githubusercontent.com/jgraph/drawio/dev/src/main/webapp/templates/"),
    "drawio-diagrams": ("", "https://raw.githubusercontent.com/jgraph/drawio-diagrams/dev/"),
}


def models(path: str) -> list[ET.Element]:
    root = ET.parse(path).getroot()
    if root.tag == "mxGraphModel":
        return [root]
    out = []
    for d in root.iter("diagram"):
        m = d.find("mxGraphModel")
        if m is None and d.text and d.text.strip():
            raw = zlib.decompress(base64.b64decode(d.text.strip()), -15)
            m = ET.fromstring(urllib.parse.unquote(raw.decode()))
        if m is not None:
            out.append(m)
    return out


def _match(text: str) -> str | None:
    joined = " ".join(re.split(r"[^a-z0-9]+", text.lower().replace("-", " ").replace("_", " ")))
    for t, words in TYPES:
        if any(re.search(r"(?<![a-z0-9])" + re.escape(w.replace("_", " ")), joined) for w in words):
            return t
    return None


def classify(rel: str, libs: list[str]) -> str:
    """Primero el nombre del archivo, luego la carpeta, luego las librerías de shapes."""
    p = Path(rel)
    return _match(p.stem) or _match(str(p.parent)) or _match(" ".join(libs)) or "otro"


def entry(src: str, rel: str, path: str) -> dict | None:
    try:
        ms = models(path)
    except Exception:  # noqa: BLE001
        return None
    cells = [c for m in ms for c in m.iter("mxCell")]
    raw = Path(path).read_text(encoding="utf-8", errors="ignore")
    st = " ".join(c.get("style") or "" for c in cells)
    libs = sorted(set(re.findall(r"shape=mxgraph\.([a-z0-9_]+)\.", st)))
    layers = sum(c.get("parent") == "0" for c in cells)
    tipo = classify(rel, libs)
    patterns = [p for p, cond in [
        ("capas", layers > len(ms)), ("capas-interactivas", "data:action/json" in raw),
        ("contenedores", "container=1" in st or "swimlane" in st),
        ("tablas", "shape=table" in st or "childLayout=stackLayout" in st),
        ("metadatos", "<UserObject" in raw or "<object" in raw), ("links", " link=" in raw),
        ("iconos-imagen", "shape=image" in st), ("multi-pagina", len(ms) > 1),
        ("anidado", sum(c.get("vertex") == "1" and c.get("parent") not in ("0", "1") for c in cells) > 10),
    ] if cond]
    base_url = SOURCES[src][1]
    png = Path(path).with_suffix(".png")
    return {
        "id": f"{src}:{rel}", "titulo": Path(rel).stem.replace("_", " ").replace("-", " "),
        "tipo": tipo, "modo": next((m for m, ts in MODE.items() if tipo in ts), "spec"),
        "librerias": libs, "patrones": patterns, "paginas": len(ms),
        "nodos": sum(c.get("vertex") == "1" for c in cells), "edges": sum(c.get("edge") == "1" for c in cells),
        "url": base_url + urllib.parse.quote(rel),
        "preview": base_url + urllib.parse.quote(str(Path(rel).with_suffix(".png"))) if png.exists() else None,
    }


def main(drawio_dir: str, diagrams_dir: str) -> None:
    out = []
    for src, base in (("drawio", Path(drawio_dir) / SOURCES["drawio"][0]), ("drawio-diagrams", Path(diagrams_dir))):
        for dp, _, fs in os.walk(base):
            if ".git" in dp:
                continue
            for f in sorted(fs):
                if f.endswith((".xml", ".drawio")) and f != "index.xml":
                    p = os.path.join(dp, f)
                    e = entry(src, os.path.relpath(p, base), p)
                    if e:
                        out.append(e)
    dest = Path(__file__).resolve().parents[1] / "src" / "advancedrawio" / "catalog.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(out)} ejemplos -> {dest} ({dest.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(*sys.argv[1:3])

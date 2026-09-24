"""Los 770 ejemplos oficiales de jgraph: buscar, extraer su receta de estilos y reutilizarlos."""
from __future__ import annotations

import collections
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

from .icons import CACHE_DIR
from .xmlio import first_model as _load
from .xmlio import load as _load_all

CATALOG = Path(__file__).parent / "catalog.json"


@lru_cache(maxsize=1)
def catalog() -> list[dict]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def types() -> dict[str, int]:
    return dict(collections.Counter(e["tipo"] for e in catalog()).most_common())


def find(tipo: str | None = None, query: str | None = None, patron: str | None = None,
         libreria: str | None = None, limit: int = 8) -> list[dict]:
    words = (query or "").lower().split()
    hits = []
    for e in catalog():
        if tipo and e["tipo"] != tipo:
            continue
        if patron and patron not in e["patrones"]:
            continue
        if libreria and libreria not in e["librerias"]:
            continue
        hay = (e["titulo"] + " " + e["id"] + " " + " ".join(e["librerias"])).lower()
        if words and not all(w in hay for w in words):
            continue
        hits.append(e)
    # plantillas oficiales antes que posts del blog; luego los más ricos en patrones y de tamaño moderado
    def origin(e):
        path = e["id"].split(":", 1)[1]
        return 0 if e["id"].startswith("drawio:") or path.startswith("templates/") else 1 if path.startswith("examples/") else 2
    hits.sort(key=lambda e: (origin(e) if not patron else 0, "legacy" in e["id"], -len(e["patrones"]),
                             abs(min(e["nodos"], 80) - 35)))
    seen, unique = set(), []
    for e in hits:  # jgraph/drawio y jgraph/drawio-diagrams repiten muchas plantillas
        key = Path(e["id"]).stem.lower()
        if key not in seen:
            seen.add(key)
            unique.append(e)
    hits = unique
    keys = ("id", "titulo", "tipo", "modo", "librerias", "patrones", "nodos", "edges")
    return [{k: e[k] for k in keys} for e in hits[:limit]]


def _get(eid: str) -> dict:
    e = next((x for x in catalog() if x["id"] == eid), None)
    if not e:
        raise ValueError(f"Ejemplo '{eid}' no existe; usa find_examples para ver ids válidos")
    return e


def download(eid: str) -> Path:
    e = _get(eid)
    dest = CACHE_DIR / "examples" / re.sub(r"[^A-Za-z0-9._-]+", "_", eid)
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(e["url"], timeout=60) as r:
            dest.write_bytes(r.read())
    return dest


def preview(eid: str) -> Path | None:
    e = _get(eid)
    if not e.get("preview"):
        return None
    dest = download(eid).with_suffix(".png")
    if not dest.exists():
        with urllib.request.urlopen(e["preview"], timeout=60) as r:
            dest.write_bytes(r.read())
    return dest


def _clean(style: str) -> str:
    s = re.sub(r"image=data:[^;]+;?", "image=<icono>;", style or "")
    return re.sub(r"(points|editableCssRules)=[^;]*;", "", s)


def recipe(eid: str, top: int = 4) -> dict:
    """Estilos más usados por rol, listos para copiar al campo 'style' del spec."""
    model = _load(str(download(eid)))
    cells = list(model.iter("mxCell"))
    roles: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for c in cells:
        st = c.get("style") or ""
        if c.get("parent") == "0" or not st:
            continue
        if c.get("edge") == "1":
            role = "edges"
        elif ("container=1" in st or "swimlane" in st or "group" in st.split(";")[0]
              or ("dashed=1" in st and "fillColor=none" in st)):
            role = "zonas"
        elif st.startswith("text;") or "text;" in st[:10]:
            role = "textos"
        elif re.search(r"shape=(image|mxgraph\.)", st):
            role = "iconos"
        else:
            role = "nodos"
        roles[role][_clean(st)] += 1
    layers = [{"nombre": c.get("value") or "(base)", "oculta": c.get("visible") == "0"}
              for c in cells if c.get("parent") == "0"]
    e = _get(eid)
    return {"id": eid, "tipo": e["tipo"], "modo": e["modo"], "librerias": e["librerias"],
            "patrones": e["patrones"], "capas": layers,
            "estilos": {r: [{"usos": n, "style": s} for s, n in cnt.most_common(top)] for r, cnt in roles.items()}}


def _visible(v: str) -> str:
    """Texto que se ve en pantalla: sin HTML, entidades resueltas, espacios normalizados."""
    v = re.sub(r"<br\s*/?>|</div>|</p>|</li>", "\n", v or "", flags=re.I)
    v = html.unescape(re.sub(r"<[^>]+>", "", v)).replace("\xa0", " ")
    return "\n".join(" ".join(line.split()) for line in v.splitlines() if line.strip())


def _rewrite_html(raw: str, new: str) -> str:
    """Pone el texto nuevo en el primer fragmento de texto, conservando las etiquetas de formato."""
    parts = re.split(r"(<[^>]+>)", raw)
    done = False
    for i, part in enumerate(parts):
        if part.startswith("<") or not html.unescape(part).strip():
            continue
        parts[i] = "" if done else html.escape(new, quote=False).replace("\n", "<br>")
        done = True
    return "".join(parts)


def from_template(eid: str, replacements: dict[str, str], out: Path) -> Path:
    """Copia un ejemplo y reemplaza textos visibles. Para planos, infografías, wireframes, canvases."""
    root = _load_all(str(download(eid)))
    wanted = {_visible(k): v for k, v in replacements.items()}
    missing = set(wanted)
    for el in root.iter():
        for attr in ("value", "label"):
            raw = el.get(attr)
            if not raw:
                continue
            seen = _visible(raw)
            if seen in wanted:  # la celda entera es ese texto: se reescribe (conserva html=1) y no se toca más
                el.set(attr, _rewrite_html(raw, wanted[seen]) if "<" in raw else wanted[seen])
                missing.discard(seen)
                continue
            # fragmentos literales dentro de un texto mayor: palabras completas, en una sola pasada sobre
            # el original, para no reemplazar dentro de lo ya reemplazado ("S" dentro de "PAGOS")
            frags = sorted((o for o in wanted if o in seen and o in raw), key=len, reverse=True)
            if frags:
                pattern = re.compile(r"(?<!\w)(" + "|".join(map(re.escape, frags)) + r")(?!\w)")
                found = pattern.findall(raw)
                if found:
                    el.set(attr, pattern.sub(lambda m: wanted[m.group(1)], raw))
                    missing.difference_update(found)
    if missing:
        raise ValueError(f"Textos no encontrados en la plantilla: {sorted(missing)}. "
                         "Usa get_example y copia los textos exactos de 'textos'.")
    out.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(out, encoding="unicode")
    return out


def texts(eid: str, limit: int = 60) -> list[str]:
    """Textos visibles de la plantilla (las claves válidas para build_from_example)."""
    model = _load(str(download(eid)))
    seen = []
    for el in model.iter():
        v = _visible(el.get("value") or el.get("label") or "")
        if v and v not in seen:
            seen.append(v)
    return seen[:limit]

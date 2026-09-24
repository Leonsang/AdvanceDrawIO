"""Resolución de iconos: índice oficial de draw.io (cacheado) + SVGs propios."""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.request
from functools import lru_cache
from pathlib import Path

INDEX_URL = "https://raw.githubusercontent.com/jgraph/drawio-mcp/main/shape-search/search-index.json"
CACHE_DIR = Path(os.environ.get("ADVANCEDRAWIO_CACHE", Path.home() / ".cache" / "advancedrawio"))
USER_ICONS = [Path(__file__).resolve().parents[2] / "icons"]
if os.environ.get("ADVANCEDRAWIO_ICONS"):
    USER_ICONS.insert(0, Path(os.environ["ADVANCEDRAWIO_ICONS"]))


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


@lru_cache(maxsize=1)
def _index() -> list[dict]:
    path = CACHE_DIR / "search-index.json"
    if not path.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(INDEX_URL, timeout=60) as r:
            path.write_bytes(r.read())
    items = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for i in items:
        m = re.search(r"image=data:image/svg\+xml,([A-Za-z0-9+/=]+)", i.get("style", ""))
        if not m:
            continue
        title, tags = i["title"], i.get("tags", "")
        if title.startswith("Svg+Xml"):  # el índice guarda estos GCP con el base64 como título
            t = re.search(r"\bicon \w+ (.+)$", tags)
            if not t:
                continue
            title = t.group(1).strip().title()
        out.append({"title": title, "tags": tags, "b64": m.group(1)})
    return out


@lru_cache(maxsize=1)
def _user_icons() -> dict[str, str]:
    icons = {}
    for d in USER_ICONS:
        if d.is_dir():
            for f in d.glob("*.svg"):
                icons[_norm(f.stem)] = base64.b64encode(f.read_bytes()).decode()
    return icons


def search(query: str, limit: int = 10) -> list[str]:
    """Devuelve títulos de iconos que coinciden (los propios primero)."""
    q = _norm(query)
    words = q.split()
    res = [k + " (propio)" for k in _user_icons() if all(w in k for w in words)]
    scored = []
    for i in _index():
        t, hay = _norm(i["title"]), _norm(i["title"] + " " + i["tags"])
        if all(w in hay for w in words):
            scored.append((0 if t == q else 1 if t.startswith(q) else 2, len(t), i["title"]))
    seen = set()
    for _, _, t in sorted(scored):
        if t not in seen:
            seen.add(t)
            res.append(t)
    return res[:limit]


def resolve(name: str) -> str | None:
    """Base64 del SVG para un producto/icono, o None si no existe."""
    q = _norm(name.replace("(propio)", ""))
    if q in _user_icons():
        return _user_icons()[q]
    exact = [i for i in _index() if _norm(i["title"]) == q]
    if exact:
        return exact[0]["b64"]
    hits = search(name, 1)
    if hits and not hits[0].endswith("(propio)"):
        return next(i["b64"] for i in _index() if i["title"] == hits[0])
    return None

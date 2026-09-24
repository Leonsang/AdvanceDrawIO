"""Revisión objetiva de un .drawio: el agente la usa para decidir qué corregir en el spec."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from .xmlio import first_model

ROOT, BASE = "0", "1"
MAX_NODES = 25
MAX_ASPECT = 3.5


def _load(path: str) -> ET.Element:
    return first_model(path)


def _geometry(model: ET.Element):
    cells = {}
    for el in model.iter():
        if el.tag == "mxCell" and el.get("id"):
            cells[el.get("id")] = el
        elif el.tag in ("UserObject", "object"):
            inner = el.find("mxCell")
            if inner is not None:
                inner.set("id", el.get("id"))
                cells[el.get("id")] = inner
    layers = {cid for cid, c in cells.items() if c.get("parent") == ROOT}

    def abs_rect(cid):
        c = cells[cid]
        g = c.find("mxGeometry")
        x, y = float(g.get("x", 0)), float(g.get("y", 0))
        p = c.get("parent")
        while p and p not in layers and p in cells:
            pg = cells[p].find("mxGeometry")
            x += float(pg.get("x", 0))
            y += float(pg.get("y", 0))
            p = cells[p].get("parent")
        return x, y, float(g.get("width", 0)), float(g.get("height", 0))

    return cells, layers, abs_rect


def _hits(seg, rect, pad=4.0) -> bool:
    (x1, y1), (x2, y2) = seg
    rx, ry, rw, rh = rect[0] + pad, rect[1] + pad, rect[2] - 2 * pad, rect[3] - 2 * pad
    if rw <= 0 or rh <= 0:
        return False
    # Liang-Barsky
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - rx), (dx, rx + rw - x1), (-dy, y1 - ry), (dy, ry + rh - y1)):
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True


def lint(path: str) -> dict:
    model = _load(path)
    cells, layers, abs_rect = _geometry(model)
    layer_name = {cid: cells[cid].get("value") or "Base" for cid in layers}
    compound = {cid for cid, c in cells.items() if c.get("vertex") == "1" and "childLayout=" in (c.get("style") or "")}

    def owner(cid):
        """El nodo atómico que contiene a cid (una tabla contiene sus filas y celdas)."""
        found, p = cid, cells.get(cid, {}).get("parent") if cid in cells else None
        while p and p in cells and p not in layers:
            if p in compound:
                found = p
            p = cells[p].get("parent")
        return found

    parts = {cid for cid in cells if cells[cid].get("vertex") == "1" and owner(cid) != cid}
    containers = {cid for cid, c in cells.items()
                  if "container=1" in (c.get("style") or "") and cid not in compound and cid not in parts}
    decor = {cid for cid, c in cells.items()
             if cid in ("title", "legend_t") or cid.startswith(("legend_", "note")) or "text;" in (c.get("style") or "")}
    nodes = {cid for cid, c in cells.items()
             if c.get("vertex") == "1" and cid not in containers and cid not in decor and cid not in parts}
    rects = {cid: abs_rect(cid) for cid in nodes | containers}
    edges = [c for c in cells.values() if c.get("edge") == "1"]
    issues = []

    for a in sorted(nodes):
        for b in sorted(nodes):
            if a < b:
                ax, ay, aw, ah = rects[a]
                bx, by, bw, bh = rects[b]
                if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                    issues.append({"tipo": "solape", "nodos": [a, b],
                                   "arreglo": "Reporta el bug o separa los nodos en zonas distintas."})

    linked = set()
    for e in edges:
        s, t = owner(e.get("source")), owner(e.get("target"))
        linked |= {s, t}
        if s not in rects or t not in rects:
            continue
        sx, sy, sw, sh = rects[s]
        tx, ty, tw, th = rects[t]
        pts = [(sx + sw / 2, sy + sh / 2)]
        arr = e.find("mxGeometry/Array")
        if arr is not None:
            origin = (0.0, 0.0)
            if e.get("parent") not in layers:
                ox, oy, _, _ = abs_rect(e.get("parent"))
                origin = (ox, oy)
            pts += [(float(p.get("x", 0)) + origin[0], float(p.get("y", 0)) + origin[1]) for p in arr.iter("mxPoint")]
        pts.append((tx + tw / 2, ty + th / 2))
        segs = list(zip(pts, pts[1:]))
        crossed = sorted(n for n in nodes - {s, t} if any(_hits(sg, rects[n]) for sg in segs))
        if crossed:
            issues.append({"tipo": "edge_cruza_nodo", "edge": f"{s}->{t}",
                           "capa": layer_name.get(e.get("parent"), "Base"), "cruza": crossed,
                           "arreglo": "Mueve el nodo cruzado a otra zona, cambia 'direction', o pasa este edge "
                                      "a una capa propia (visible:false) si es secundario."})

    isolated = sorted(n for n in nodes if n not in linked)
    if isolated:
        issues.append({"tipo": "nodo_aislado", "nodos": isolated,
                       "arreglo": "Conéctalo con un edge o elimínalo; los nodos sueltos confunden."})

    for z in sorted(containers):
        if "akind=external" in (cells[z].get("style") or ""):
            continue
        kids = [n for n in nodes if cells[n].get("parent") == z]
        subzones = [c for c in containers if cells[c].get("parent") == z]
        if len(kids) + len(subzones) <= 1:
            issues.append({"tipo": "zona_casi_vacia", "zona": z,
                           "arreglo": "Fusiona la zona con su vecina o quítala; una zona con 1 elemento es ruido."})

    if len(nodes) > MAX_NODES:
        issues.append({"tipo": "demasiados_nodos", "n": len(nodes),
                       "arreglo": f"Divide en {-(-len(nodes) // MAX_NODES)} diagramas: vista general + detalle por zona."})

    base_rects = [rects[c] for c in nodes | containers if cells[c].get("parent") in layers]
    if base_rects:
        w = max(x + ww for x, _, ww, _ in base_rects) - min(x for x, _, _, _ in base_rects)
        h = max(y + hh for _, y, _, hh in base_rects) - min(y for _, y, _, _ in base_rects)
        ratio = round(max(w, h) / max(min(w, h), 1), 1)
        if ratio > MAX_ASPECT and len(nodes) > 6:
            issues.append({"tipo": "proporcion_extrema", "ratio": ratio,
                           "arreglo": "Cambia 'direction' (RIGHT<->DOWN) o agrupa etapas en zonas para "
                                      "que el diagrama sea más compacto."})

    def penalty(i):
        t = i["tipo"]
        if t == "edge_cruza_nodo":
            return 8 * len(i["cruza"])
        if t == "proporcion_extrema":
            return 8 if i["ratio"] <= 5 else 20
        return {"solape": 30, "demasiados_nodos": 15, "nodo_aislado": 5, "zona_casi_vacia": 5}[t]
    score = max(0, 100 - sum(penalty(i) for i in issues))
    return {"archivo": str(Path(path).name), "nodos": len(nodes), "edges": len(edges),
            "puntaje": score, "aprobado": score >= 85 and not any(i["tipo"] == "solape" for i in issues),
            "problemas": issues}

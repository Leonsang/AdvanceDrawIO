"""Spec JSON -> .drawio con zonas anidadas, layout ELK, capas y leyenda interactiva."""
from __future__ import annotations

import json
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from . import components as C
from . import drawio_cli

ROOT, BASE = "0", "1"


def _validate(spec: dict) -> None:
    errs = []
    zones = {z["id"]: z for z in spec.get("zones", [])}
    nodes = {n["id"]: n for n in spec.get("nodes", [])}
    layers = {l["id"] for l in spec.get("layers", [])}
    ids = [z["id"] for z in spec.get("zones", [])] + [n["id"] for n in spec.get("nodes", [])]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        errs.append(f"ids duplicados: {sorted(dup)}")
    for z in zones.values():
        if z.get("parent") and z["parent"] not in zones:
            errs.append(f"zona '{z['id']}': parent '{z['parent']}' no existe")
    for n in spec.get("nodes", []):
        if n.get("zone") and n["zone"] not in zones:
            errs.append(f"nodo '{n['id']}': zone '{n['zone']}' no existe")
        if n.get("kind", "card") not in C.NODE_SIZE:
            errs.append(f"nodo '{n['id']}': kind debe ser uno de {list(C.NODE_SIZE)}")
    for e in spec.get("edges", []):
        for k in ("from", "to"):
            if e.get(k) not in nodes and e.get(k) not in zones:
                errs.append(f"edge {e.get('from')}->{e.get('to')}: '{e.get(k)}' no existe")
        if e.get("layer") and e["layer"] not in layers:
            errs.append(f"edge {e['from']}->{e['to']}: capa '{e['layer']}' no declarada en layers")
    for nt in spec.get("notes", []):
        if nt.get("near") not in nodes and nt.get("near") not in zones:
            errs.append(f"nota: near '{nt.get('near')}' no existe")
    if not nodes:
        errs.append("el spec no tiene nodes")
    if errs:
        raise ValueError("Spec inválido:\n- " + "\n- ".join(errs))


def _cell(parent_el, **attrs):
    geom = attrs.pop("geom", None)
    c = ET.SubElement(parent_el, "mxCell", {k: str(v) for k, v in attrs.items()})
    if geom is not None:
        ET.SubElement(c, "mxGeometry", {**{k: str(v) for k, v in geom.items()}, "as": "geometry"})
    return c


def _chain(cid: str, parent_of: dict) -> list[str]:
    out = []
    while cid in parent_of:
        cid = parent_of[cid]
        out.append(cid)
    return out


def _draft(spec: dict) -> tuple[ET.Element, dict]:
    """Modelo pre-layout: todo en la capa base, edges en su contenedor común."""
    model = ET.Element("mxGraphModel", {"adaptiveColors": "auto"})
    root = ET.SubElement(model, "root")
    _cell(root, id=ROOT)
    _cell(root, id=BASE, parent=ROOT, value="Base")
    parent_of, sizes = {}, {}
    ext = 0
    zones = spec.get("zones", [])
    ordered, placed = [], set()
    while len(ordered) < len(zones):
        for z in zones:
            if z["id"] not in placed and (not z.get("parent") or z["parent"] in placed):
                ordered.append(z)
                placed.add(z["id"])
    for z in ordered:
        kind = z.get("kind", "zone")
        p = z.get("parent") or BASE
        parent_of[z["id"]] = p
        _cell(root, id=z["id"], parent=p, vertex=1, value=z.get("label", ""),
              style=C.zone_style(kind, ext), geom={"width": 200, "height": 120})
        ext += kind == "external"
    for n in spec["nodes"]:
        kind = n.get("kind", "card")
        w, h = C.NODE_SIZE[kind]
        p = n.get("zone") or BASE
        parent_of[n["id"]] = p
        sizes[n["id"]] = (w, h)
        _cell(root, id=n["id"], parent=p, vertex=1, value=C.node_label(kind, n.get("label", n["id"]), n.get("product")),
              style=C.node_style(kind, n.get("product")), geom={"width": w, "height": h})
    colors = {l["id"]: l.get("color") or C.LAYER_COLORS[i % len(C.LAYER_COLORS)]
              for i, l in enumerate(spec.get("layers", []))}
    edge_layer = {}
    for i, e in enumerate(spec.get("edges", [])):
        a, b = _chain(e["from"], parent_of), _chain(e["to"], parent_of)
        common = next((x for x in a if x in b), BASE)
        if common == ROOT:
            common = BASE
        eid = f"e{i + 1}"
        edge_layer[eid] = e.get("layer")
        label = str(e.get("label", ""))
        if e.get("step") is not None:
            label = f"&nbsp;{e['step']}&nbsp;" + (f"· {label}&nbsp;" if label else "")
        color = colors.get(e.get("layer"), C.BASE_EDGE)
        _cell(root, id=eid, parent=common, edge=1, source=e["from"], target=e["to"], value=label,
              style=C.edge_style(color, e.get("dashed", False), e.get("bidirectional", False), e.get("step") is not None),
              geom={"relative": 1})
    return model, {"sizes": sizes, "edge_layer": edge_layer, "colors": colors}


def _abs_origin(cid: str, cells: dict) -> tuple[float, float]:
    x = y = 0.0
    c = cells.get(cid)
    while c is not None and c.get("parent") not in (None, ROOT):
        g = c.find("mxGeometry")
        if c.get("vertex") == "1" and g is not None:
            x += float(g.get("x", 0))
            y += float(g.get("y", 0))
        c = cells.get(c.get("parent"))
    return x, y


def _finish(model: ET.Element, spec: dict, meta: dict) -> ET.Element:
    root = model.find("root")
    cells = {c.get("id"): c for c in root.iter("mxCell")}
    # 1) ELK ensancha los nodos al ancho de la etiqueta: restaurar tamaño, centrado en su hueco
    for cid, (w, h) in meta["sizes"].items():
        g = cells[cid].find("mxGeometry")
        cw, ch = float(g.get("width", w)), float(g.get("height", h))
        g.set("x", str(round(float(g.get("x", 0)) + (cw - w) / 2)))
        g.set("y", str(round(float(g.get("y", 0)) + (ch - h) / 2)))
        g.set("width", str(w))
        g.set("height", str(h))
    # 2) capas: crear celdas de capa y mover edges (coordenadas -> absolutas)
    layer_ids = {}
    for l in spec.get("layers", []):
        lid = "L_" + l["id"]
        layer_ids[l["id"]] = lid
        attrs = {"id": lid, "parent": ROOT, "value": l.get("name", l["id"])}
        if l.get("visible") is False:
            attrs["visible"] = "0"
        ET.SubElement(root, "mxCell", attrs)
    for eid, layer in meta["edge_layer"].items():
        if not layer:
            continue
        e = cells[eid]
        ox, oy = _abs_origin(e.get("parent"), cells)
        for pt in e.find("mxGeometry").iter("mxPoint"):
            if pt.get("as") != "offset":
                pt.set("x", str(float(pt.get("x", 0)) + ox))
                pt.set("y", str(float(pt.get("y", 0)) + oy))
        root.remove(e)
        e.set("parent", layer_ids[layer])
        root.append(e)
    # 3) bbox de lo dibujado en la base
    xs, ys, xe, ye = [], [], [], []
    for c in root.iter("mxCell"):
        if c.get("parent") == BASE and c.get("vertex") == "1":
            g = c.find("mxGeometry")
            x, y = float(g.get("x", 0)), float(g.get("y", 0))
            xs.append(x); ys.append(y)
            xe.append(x + float(g.get("width", 0))); ye.append(y + float(g.get("height", 0)))
    minx, miny, maxx = min(xs), min(ys), max(xe)
    # 4) notas en su propia capa
    if spec.get("notes"):
        lid = "L__notes"
        ET.SubElement(root, "mxCell", {"id": lid, "parent": ROOT, "value": "Anotaciones"})
        for i, nt in enumerate(spec["notes"]):
            t = cells[nt["near"]]
            ax, ay = _abs_origin(nt["near"], cells)
            g = t.find("mxGeometry")
            _cell(root, id=f"note{i}", parent=lid, vertex=1, value=nt["text"], style=C.NOTE_STYLE,
                  geom={"x": round(ax + float(g.get("width", 0)) - 20), "y": round(ay - 38), "width": 150, "height": 34})
    # 5) título y leyenda clicable
    if spec.get("title"):
        _cell(root, id="title", parent=BASE, vertex=1, value=spec["title"], style=C.TITLE_STYLE,
              geom={"x": minx, "y": miny - 60, "width": 700, "height": 36})
    toggles = [(l, layer_ids[l["id"]]) for l in spec.get("layers", [])]
    if spec.get("notes"):
        toggles.append(({"id": "_notes", "name": "Anotaciones"}, "L__notes"))
    if toggles and spec.get("legend", True):
        lx = maxx + 40
        _cell(root, id="legend_t", parent=BASE, vertex=1, value="<b>Capas</b><br><font style=\"font-size:9px\" color=\"#80868B\">clic para mostrar / ocultar</font>",
              style="text;html=1;align=left;verticalAlign=top;fontSize=12;", geom={"x": lx, "y": miny, "width": 170, "height": 34})
        for i, (l, lid) in enumerate(toggles):
            color = meta["colors"].get(l["id"], "#F9AB00")
            link = "data:action/json," + json.dumps({"actions": [{"toggle": {"cells": [lid]}}]}, separators=(",", ":"))
            uo = ET.SubElement(root, "UserObject", {"id": f"legend_{i}", "label": l.get("name", l["id"]), "link": link})
            _cell(uo, parent=BASE, vertex=1, style=C.LEGEND_ITEM + f"strokeColor={color};",
                  geom={"x": lx, "y": miny + 44 + i * 42, "width": 170, "height": 32})
    return model


def build(spec: dict | str, out_dir: str, name: str = "diagrama", formats: tuple[str, ...] = ("png",)) -> dict:
    """Construye el diagrama. Devuelve rutas generadas."""
    if isinstance(spec, str):
        spec = json.loads(spec)
    _validate(spec)
    out = Path(out_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    model, meta = _draft(spec)
    with tempfile.TemporaryDirectory() as tmp:
        draft = os.path.join(tmp, "draft.drawio")
        ET.ElementTree(model).write(draft, encoding="unicode")
        drawio_cli.layout(draft, spec.get("direction", "RIGHT"), int(spec.get("spacing", 40)))
        laid = ET.parse(draft).getroot()
    laid_model = laid if laid.tag == "mxGraphModel" else laid.find(".//mxGraphModel")
    final = _finish(laid_model, spec, meta)
    mxfile = ET.Element("mxfile", {"host": "advancedrawio"})
    diagram = ET.SubElement(mxfile, "diagram", {"id": "p1", "name": spec.get("title", name)[:40]})
    diagram.append(final)
    drawio_path = out / f"{name}.drawio"
    ET.ElementTree(mxfile).write(drawio_path, encoding="unicode")
    result = {"drawio": str(drawio_path)}
    for fmt in formats:
        p = out / f"{name}.drawio.{fmt}"
        drawio_cli.export(str(drawio_path), str(p), fmt)
        result[fmt] = str(p)
    return result

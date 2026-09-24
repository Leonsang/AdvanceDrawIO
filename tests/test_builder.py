import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from advancedrawio import builder, drawio_cli

SPEC = json.loads((Path(__file__).parents[1] / "examples" / "plataforma-ia-gcp.json").read_text(encoding="utf-8"))


def test_validacion_reporta_todos_los_errores():
    bad = {"nodes": [{"id": "a", "zone": "nope"}, {"id": "a"}],
           "edges": [{"from": "a", "to": "x", "layer": "fantasma"}]}
    with pytest.raises(ValueError) as e:
        builder._validate(bad)
    msg = str(e.value)
    assert "duplicados" in msg and "'nope' no existe" in msg and "'x' no existe" in msg and "fantasma" in msg


def test_edge_va_al_contenedor_comun_mas_interno():
    model, _ = builder._draft(SPEC)
    edges = {c.get("source") + ">" + c.get("target"): c.get("parent") for c in model.iter("mxCell") if c.get("edge")}
    assert edges["lb>armor"] == "borde"
    assert edges["apigee>orq"] == "gcp"
    assert edges["orq>sap"] == "1"


def test_capas_edges_a_coordenadas_absolutas():
    spec = {"layers": [{"id": "x", "visible": False}],
            "zones": [{"id": "z", "label": "Z"}],
            "nodes": [{"id": "a", "zone": "z", "kind": "box"}, {"id": "b", "zone": "z", "kind": "box"}],
            "edges": [{"from": "a", "to": "b", "layer": "x"}]}
    model, meta = builder._draft(spec)
    cells = {c.get("id"): c for c in model.iter("mxCell")}
    cells["z"].find("mxGeometry").attrib.update(x="100", y="50")
    geo = cells["e1"].find("mxGeometry")
    arr = ET.SubElement(geo, "Array", {"as": "points"})
    ET.SubElement(arr, "mxPoint", {"x": "10", "y": "20"})
    out = builder._finish(model, spec, meta)
    e = next(c for c in out.iter("mxCell") if c.get("id") == "e1")
    assert e.get("parent") == "L_x"
    pt = e.find(".//mxPoint")
    assert (float(pt.get("x")), float(pt.get("y"))) == (110, 70)
    layer = next(c for c in out.iter("mxCell") if c.get("id") == "L_x")
    assert layer.get("visible") == "0"
    links = [u.get("link") for u in out.iter("UserObject")]
    assert any('"toggle":{"cells":["L_x"]}' in l for l in links)


@pytest.mark.skipif(drawio_cli.find() is None, reason="draw.io Desktop no instalado")
def test_build_completo(tmp_path):
    res = builder.build(SPEC, str(tmp_path), "t", ("png",))
    assert Path(res["png"]).stat().st_size > 10_000
    root = ET.parse(res["drawio"]).getroot()
    layers = [c.get("value") for c in root.iter("mxCell") if c.get("parent") == "0"]
    assert layers == ["Base", "Flujo conversacional", "Datos y analítica", "Seguridad", "Anotaciones"]

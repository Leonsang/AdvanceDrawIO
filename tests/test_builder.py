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


def test_lint_detecta_edge_que_cruza_nodo(tmp_path):
    from advancedrawio.lint import lint
    xml = """<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>
    <mxCell id="a" vertex="1" parent="1" style="rounded=1;"><mxGeometry x="0" y="0" width="100" height="40" as="geometry"/></mxCell>
    <mxCell id="b" vertex="1" parent="1" style="rounded=1;"><mxGeometry x="400" y="0" width="100" height="40" as="geometry"/></mxCell>
    <mxCell id="c" vertex="1" parent="1" style="rounded=1;"><mxGeometry x="200" y="0" width="100" height="40" as="geometry"/></mxCell>
    <mxCell id="e1" edge="1" parent="1" source="a" target="b"><mxGeometry relative="1" as="geometry"/></mxCell>
    <mxCell id="e2" edge="1" parent="1" source="a" target="c"><mxGeometry relative="1" as="geometry"/></mxCell>
    </root></mxGraphModel>"""
    p = tmp_path / "x.drawio"
    p.write_text(xml)
    r = lint(str(p))
    cruces = [i for i in r["problemas"] if i["tipo"] == "edge_cruza_nodo"]
    assert cruces and cruces[0]["edge"] == "a->b" and cruces[0]["cruza"] == ["c"]
    assert not r["aprobado"] or r["puntaje"] < 100


def test_subagente_sincronizado_con_prompt():
    root = Path(__file__).parents[1]
    agent = (root / "src" / "advancedrawio" / "agent.md").read_text(encoding="utf-8")
    sub = (root / ".claude" / "agents" / "drawio-architect.md").read_text(encoding="utf-8")
    assert sub.split("---", 2)[2].strip() == agent.strip(), "regenera .claude/agents/drawio-architect.md"


def test_ejemplo_del_prompt_es_valido():
    import re
    agent = (Path(__file__).parents[1] / "src" / "advancedrawio" / "agent.md").read_text(encoding="utf-8")
    spec = json.loads(re.search(r"```json\n(.+?)```", agent, re.S).group(1))
    builder._validate(spec)

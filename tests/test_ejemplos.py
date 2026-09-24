import json
from pathlib import Path

import pytest

from advancedrawio import builder, cli, drawio_cli

EXAMPLES = Path(__file__).parents[1] / "examples"
SPECS = sorted(EXAMPLES.glob("*.json"))


@pytest.mark.parametrize("path", SPECS, ids=[p.stem for p in SPECS])
def test_ejemplo_es_valido(path):
    spec = json.loads(path.read_text(encoding="utf-8"))
    builder._validate(spec)
    model, meta = builder._draft(spec)
    assert len(meta["sizes"]) == len(spec["nodes"])
    cards = [n for n in spec["nodes"] if n.get("product")]
    styles = {c.get("id"): c.get("style") for c in model.iter("mxCell")}
    sin_icono = [n["id"] for n in cards if "image=data:image/svg+xml," not in styles[n["id"]]]
    assert not sin_icono, f"product sin icono en el índice: {sin_icono}"


@pytest.fixture
def fake_build(monkeypatch, tmp_path):
    calls = []

    def fake(kind):
        def run(src, out, name, fmts):
            calls.append((kind, name, fmts))
            return {"drawio": str(tmp_path / f"{name}.drawio")}
        return run

    monkeypatch.setattr(builder, "build", fake("spec"))
    monkeypatch.setattr(builder, "build_mermaid", fake("mermaid"))
    monkeypatch.setattr(cli, "lint", lambda p: {"puntaje": 80})
    return calls


def test_cli_elige_modo_por_extension(fake_build, capsys):
    assert cli.main([str(EXAMPLES / "modelo-recaudo.mmd"), "-f", "png", "svg"]) == 0
    assert cli.main([str(EXAMPLES / "pipeline-datos.json")]) == 0
    assert fake_build == [("mermaid", "modelo-recaudo", ("png", "svg")), ("spec", "pipeline-datos", ("png",))]
    assert '"puntaje": 80' in capsys.readouterr().out


def test_cli_min_score_falla_bajo_el_umbral(fake_build):
    assert cli.main([str(EXAMPLES / "pipeline-datos.json"), "--min-score", "85"]) == 1
    assert cli.main([str(EXAMPLES / "pipeline-datos.json"), "--min-score", "80"]) == 0


@pytest.mark.skipif(drawio_cli.find() is None, reason="draw.io Desktop no instalado")
def test_mermaid_completo(tmp_path):
    res = builder.build_mermaid((EXAMPLES / "modelo-recaudo.mmd").read_text(encoding="utf-8"), str(tmp_path), "er")
    assert Path(res["png"]).stat().st_size > 5_000

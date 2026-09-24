"""Regresiones de seguridad: los argumentos de las tools vienen de un LLM y se tratan como no confiables."""
import base64
import os
import subprocess
import zlib

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from advancedrawio import builder, drawio_cli, server, xmlio
from advancedrawio.lint import lint

MIN_SPEC = {"nodes": [{"id": "n", "kind": "box"}]}


@pytest.fixture
def argv(monkeypatch):
    """Captura el comando que se le pasaría a draw.io, sin ejecutarlo."""
    calls = []
    monkeypatch.setattr(drawio_cli, "find", lambda: "/opt/drawio/drawio")
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: calls.append(cmd) or subprocess.CompletedProcess(cmd, 1, "", ""))
    monkeypatch.setenv("DISPLAY", ":0")
    return calls


def test_ruta_con_guion_no_llega_como_opcion(argv):
    with pytest.raises(RuntimeError):
        drawio_cli.export("--renderer-cmd-prefix=touch x", "--gpu-launcher=y.png")
    cmd = argv[0]
    assert cmd[cmd.index("-o") + 1] == os.path.abspath("--gpu-launcher=y.png")
    assert not any(a.startswith(("--renderer-cmd-prefix", "--gpu-launcher")) for a in cmd)


def test_render_exige_un_archivo_existente(argv):
    with pytest.raises(ToolError):
        server.render("--renderer-cmd-prefix=touch x")
    assert argv == []


@pytest.mark.parametrize("zones", [
    [{"id": "a", "parent": "b"}, {"id": "b", "parent": "a"}],
    [{"id": "a", "parent": "a"}],
])
def test_ciclo_en_zonas_es_error_y_no_cuelga(zones):
    with pytest.raises(ValueError, match="ciclo en parent"):
        builder._validate({"zones": zones, "nodes": [{"id": "n", "zone": "a", "kind": "box"}]})


@pytest.mark.parametrize("uid, sandbox", [(0, False), (1000, True)])
def test_no_sandbox_solo_como_root(argv, monkeypatch, uid, sandbox):
    monkeypatch.setattr(drawio_cli.platform, "system", lambda: "Linux")
    monkeypatch.setattr(drawio_cli.os, "geteuid", lambda: uid, raising=False)
    monkeypatch.delenv("ADVANCEDRAWIO_NO_SANDBOX", raising=False)
    with pytest.raises(RuntimeError):
        drawio_cli.run(["-x"])
    assert ("--no-sandbox" not in argv[0]) is sandbox


@pytest.mark.parametrize("name", ["../fuera", "a/b", "a\\b", "..", ""])
def test_nombre_de_salida_no_puede_ser_una_ruta(name, tmp_path, argv):
    for build in (lambda: builder.build(MIN_SPEC, str(tmp_path), name),
                  lambda: builder.build_mermaid("graph TD; a-->b", str(tmp_path), name)):
        with pytest.raises(ValueError, match="name inválido"):
            build()
    assert argv == [] and list(tmp_path.iterdir()) == []


def test_bomba_de_descompresion_se_corta(tmp_path, monkeypatch):
    monkeypatch.setattr(xmlio, "MAX_PAGE", 1024)
    deflate = zlib.compressobj(9, zlib.DEFLATED, -15)
    page = deflate.compress(b"<mxGraphModel>" + b" " * 100_000 + b"</mxGraphModel>") + deflate.flush()
    p = tmp_path / "bomba.drawio"
    p.write_text(f'<mxfile><diagram id="d">{base64.b64encode(page).decode()}</diagram></mxfile>')
    with pytest.raises(ValueError, match="página comprimida"):
        lint(str(p))
    with pytest.raises(ToolError):
        server.lint_diagram(str(p))

#!/usr/bin/env python3
"""Dibuja el banner de AdvanceDrawIO — "Lámina de montaje" (ver design-philosophy.md).

    pip install fonttools && python media/banner.py

Escribe media/banner.svg (esquinas redondeadas, para el README) y media/social-preview.svg
(para la vista previa social de GitHub). Las fuentes se reducen a los glifos usados y se
embeben, así el SVG se ve igual en cualquier parte y sin peticiones externas.
Para el PNG de la vista previa: ver la nota al final de design-philosophy.md.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

HERE = Path(__file__).parent
FONTS = HERE / "fonts"
W, H = 1280, 640
M = 64  # margen exterior: todo queda dentro del recorte de la vista previa social

INK = "#0E1116"
PANEL = "#151B23"
BONE = "#EDE6D8"
ORANGE = "#F08705"  # el naranja de draw.io: la señal, usada con mesura
TEAL = "#3E9C94"
RULE = "#222A33"
RAIL = "#3A444F"
LABEL = "#7C8591"

WORDMARK = "AdvanceDrawIO"
TAGLINE = ["Tú describes la estructura;", "el servidor dibuja el plano."]
KICKER = "LÁMINA 01 — MONTAJE"
POINTS = ["layout ELK con zonas anidadas", "iconos oficiales, sin base64",
          "capas con leyenda clicable", "revisión objetiva de 0 a 100"]
FOOT = "servidor mcp · python · draw.io desktop"
FIG = "fig. 1 — de la estructura al plano"
SPEC = ['{', '  "zones": [', '    {"id": "gcp"}', '  ],', '  "nodes": [', '    {"id": "api"},',
        '    {"id": "orq"},', '    {"id": "bq"},', '    {"id": "sap"}', '  ],', '  "edges": [',
        '    {"from": "api",', '     "to": "orq",', '     "step": 1}', '  ]', '}']
LEGEND = [("base", ORANGE, True), ("datos", TEAL, True), ("seguridad", TEAL, False)]


def embed(font: str, text: str, family: str, style: str = "normal") -> str:
    """Reduce la fuente a `text` y devuelve un @font-face con ella en línea."""
    f = TTFont(FONTS / font)
    opts = subset.Options()
    opts.layout_features = ["kern", "liga"]
    opts.name_IDs = ["*"]
    sub = subset.Subsetter(opts)
    sub.populate(text=text + " ")
    sub.subset(f)
    buf = io.BytesIO()
    f.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return (f"@font-face{{font-family:'{family}';font-style:{style};"
            f"src:url(data:font/ttf;base64,{data}) format('truetype');}}")


def text_width(font: str, text: str, size: float) -> float:
    f = TTFont(FONTS / font)
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    return sum(hmtx[cmap[ord(c)]][0] for c in text) * size / upm


def n(x: float) -> str:
    return f"{x:.1f}".rstrip("0").rstrip(".")


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def card(x: float, y: float, label: str, accent: str) -> list[str]:
    return [f'<rect x="{x}" y="{y}" width="76" height="34" rx="3" fill="{PANEL}" stroke="{RAIL}" stroke-width="0.75"/>',
            f'<rect x="{x + 8}" y="{y + 11}" width="12" height="12" rx="2" fill="{accent}"/>',
            f'<text x="{x + 28}" y="{y + 21}" class="mono node">{label}</text>']


def badge(x: float, y: float, k: int) -> list[str]:
    return [f'<circle cx="{x}" cy="{y}" r="8" fill="{ORANGE}"/>',
            f'<text x="{x}" y="{y + 3.5}" class="mono badge" text-anchor="middle">{k}</text>']


def draw(rounded: bool, css: str, word_size: float) -> str:
    el: list[str] = []
    add = el.append
    add(f'<rect width="{W}" height="{H}" rx="{24 if rounded else 0}" fill="{INK}"/>')
    for cx, cy in [(40, 40), (W - 40, 40), (40, H - 40), (W - 40, H - 40)]:
        add(f'<path d="M{cx - 6} {cy}H{cx + 6}M{cx} {cy - 6}V{cy + 6}" stroke="{RAIL}" stroke-width="0.75"/>')

    # ---- columna izquierda: rótulo, nombre, lema, puntos, pie --------------
    add(f'<text x="{M}" y="128" class="mono kicker">{KICKER}</text>')
    add(f'<text x="{M - 4}" y="236" class="serif word">{WORDMARK}</text>')
    for i, line in enumerate(TAGLINE):
        add(f'<text x="{M}" y="{292 + i * 36}" class="serif-i tag">{line}</text>')
    add(f'<rect x="{M}" y="362" width="24" height="1.5" fill="{ORANGE}"/>')
    for i, p in enumerate(POINTS):
        y = 402 + i * 26
        add(f'<path d="M{M} {y - 4}H{M + 12}" stroke="{TEAL}" stroke-width="1.25"/>')
        add(f'<text x="{M + 22}" y="{y}" class="mono point">{p}</text>')

    # ---- el spec: la estructura, sin coordenadas ---------------------------
    sx, sy = 640, 150
    add(f'<text x="{sx}" y="{sy - 22}" class="mono num">SPEC.JSON</text>')
    for i, line in enumerate(SPEC):
        add(f'<text x="{sx}" y="{sy + i * 18}" class="mono code" xml:space="preserve">{esc(line)}</text>')
    # el tronco: del spec al plano
    add(f'<path d="M800 300H846" stroke="{BONE}" stroke-width="1.25"/>')
    add(f'<path d="M840 295L847 300L840 305" stroke="{BONE}" stroke-width="1.25" fill="none"/>')

    # ---- el plano: zona, tarjetas en columnas ELK, edges ortogonales -------
    zx, zy, zw, zh = 860, 128, 356, 332
    for gx in range(zx + 12, zx + zw, 16):  # retícula de puntos, el papel del plano
        for gy in range(zy + 12, zy + zh, 16):
            add(f'<circle cx="{gx}" cy="{gy}" r="0.6" fill="{RULE}"/>')
    add(f'<rect x="{zx}" y="{zy}" width="{zw}" height="{zh}" rx="8" fill="none" stroke="{RAIL}" '
        f'stroke-width="1" stroke-dasharray="2 3"/>')
    add(f'<text x="{zx + 12}" y="{zy + 20}" class="mono num">ZONA · GOOGLE CLOUD</text>')
    c1, c2, c3 = 876, 998, 1124
    add(f'<path d="M{c1 + 76} 247H{c2}" stroke="{ORANGE}" stroke-width="1.5"/>')
    add(f'<path d="M{c2 + 76} 247H1100V197H{c3}" stroke="{ORANGE}" stroke-width="1.5" fill="none"/>')
    add(f'<path d="M1100 247V307H{c3}" stroke="{ORANGE}" stroke-width="1.5" fill="none"/>')
    add(f'<path d="M{c2 + 38} 264V330" stroke="{TEAL}" stroke-width="1.25"/>')
    add(f'<path d="M{c2 + 76} 347H1100V407H{c3}" stroke="{TEAL}" stroke-width="1.25" fill="none" '
        f'stroke-dasharray="4 3" opacity="0.7"/>')
    el += card(c1, 230, "api", ORANGE) + card(c2, 230, "orq", ORANGE) + card(c2, 330, "mem", TEAL)
    el += card(c3, 180, "bq", TEAL) + card(c3, 290, "sap", TEAL) + card(c3, 390, "kms", RAIL)
    el += badge((c1 + 76 + c2) / 2, 247, 1) + badge(1100, 222, 2) + badge(1100, 277, 3)

    # ---- leyenda: capas que se muestran y se ocultan -----------------------
    ly = 490
    add(f'<text x="{zx}" y="{ly + 15}" class="mono num">CAPAS</text>')
    x = zx + 56
    for name, color, on in LEGEND:
        w = 26 + len(name) * 7.2
        dash = "" if on else ' stroke-dasharray="3 2"'
        add(f'<rect x="{n(x)}" y="{ly}" width="{n(w)}" height="22" rx="11" fill="none" stroke="{color}" '
            f'stroke-width="1"{dash}/>')
        dot = f'fill="{color}"' if on else f'fill="none" stroke="{color}" stroke-width="1"'
        add(f'<circle cx="{n(x + 11)}" cy="{ly + 11}" r="3.5" {dot}/>')
        add(f'<text x="{n(x + 20)}" y="{ly + 15}" class="mono legend">{name}</text>')
        x += w + 8

    # ---- regla de agrimensor al pie ---------------------------------------
    ry = H - 72
    add(f'<path d="M{M} {ry}H{W - M}" stroke="{RULE}" stroke-width="0.75"/>')
    for tx in range(M, W - M + 1, 8):
        major = (tx - M) % 128 == 0
        add(f'<path d="M{tx} {ry}V{ry + (7 if major else 3)}" stroke="{RAIL if major else RULE}" stroke-width="0.75"/>')
        if major:
            add(f'<text x="{tx + 3}" y="{ry + 18}" class="mono scale">{tx - M}</text>')
    add(f'<text x="{M}" y="{ry - 12}" class="mono fig">{FOOT}</text>')
    add(f'<text x="{W - M}" y="{ry - 12}" class="mono fig" text-anchor="end">{FIG}</text>')

    style = (css
             + f".serif{{font-family:'Instrument Serif';fill:{BONE}}}"
             + f".serif-i{{font-family:'Instrument Serif Italic';font-style:italic;fill:{BONE}}}"
             + f".mono{{font-family:'Geist Mono';fill:{LABEL}}}"
             + f".word{{font-size:{n(word_size)}px;letter-spacing:-1.5px}}"
             + ".tag{font-size:27px;opacity:.8}"
             + ".kicker{font-size:11px;letter-spacing:2.6px}"
             + f".point{{font-size:12px;fill:{BONE};opacity:.85;letter-spacing:.3px}}"
             + ".code{font-size:11px;letter-spacing:.2px;white-space:pre}"
             + f".node{{font-size:11px;fill:{BONE}}}"
             + f".badge{{font-size:10px;fill:{INK};font-weight:700}}"
             + f".legend{{font-size:10px;fill:{BONE};letter-spacing:.3px}}"
             + ".num{font-size:9px;letter-spacing:1.4px}"
             + ".scale{font-size:8px;letter-spacing:.5px}"
             + ".fig{font-size:10px;letter-spacing:.8px}")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'role="img" aria-label="AdvanceDrawIO — tú describes la estructura, el servidor dibuja el plano">'
            f"<title>AdvanceDrawIO</title><style>{style}</style>" + "".join(el) + "</svg>\n")


def main() -> None:
    # el nombre ocupa la columna izquierda sin invadir el spec (x=640), con 40 px de aire
    word_size = min(112.0, 112.0 * (640 - 40 - M) / text_width("InstrumentSerif-Regular.ttf", WORDMARK, 112))
    mono = KICKER + FOOT + FIG + "".join(POINTS) + "".join(SPEC) + "".join(x[0] for x in LEGEND)
    mono += "SPEC.JSONZONA·GOOGLECLOUDCAPASapiorqmembqsapkms0123456789"
    css = (embed("InstrumentSerif-Regular.ttf", WORDMARK, "Instrument Serif")
           + embed("InstrumentSerif-Italic.ttf", "".join(TAGLINE), "Instrument Serif Italic", "italic")
           + embed("GeistMono-Regular.ttf", mono, "Geist Mono"))
    for name, rounded in (("banner.svg", True), ("social-preview.svg", False)):
        (HERE / name).write_text(draw(rounded, css, word_size), encoding="utf-8")
        print(f"{name}: {(HERE / name).stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()

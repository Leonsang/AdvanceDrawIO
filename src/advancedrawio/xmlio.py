"""Lectura de .drawio: descomprime páginas guardadas como deflate+base64."""
from __future__ import annotations

import base64
import urllib.parse
import xml.etree.ElementTree as ET
import zlib


def load(path: str) -> ET.Element:
    """Devuelve un <mxfile> con todas las páginas descomprimidas (o el <mxGraphModel> suelto)."""
    root = ET.parse(path).getroot()
    for d in root.iter("diagram"):
        if d.find("mxGraphModel") is None and d.text and d.text.strip():
            raw = zlib.decompress(base64.b64decode(d.text.strip()), -15)
            d.text = None
            d.append(ET.fromstring(urllib.parse.unquote(raw.decode("utf-8"))))
    return root


def first_model(path: str) -> ET.Element:
    root = load(path)
    return root if root.tag == "mxGraphModel" else root.find(".//mxGraphModel")

"""Librería de componentes extraída de la plantilla GCP oficial de draw.io."""
from __future__ import annotations

from . import icons

LAYER_COLORS = ["#4284F3", "#EA4335", "#34A853", "#F9AB00", "#A142F4", "#12B5CB"]
EXTERNAL_FILLS = ["#EFEBE9", "#E6F4EA", "#F3E8FD", "#E8F0FE", "#FEF7E0"]

NODE_SIZE = {"card": (190, 56), "box": (150, 48), "actor": (40, 60), "database": (110, 70)}


def node_style(kind: str, product: str | None) -> str:
    if kind == "card":
        b64 = icons.resolve(product) if product else None
        base = ("rounded=1;arcSize=4;absoluteArcSize=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;"
                "strokeColor=#DADCE0;shadow=1;fontSize=12;fontColor=#202124;align=left;verticalAlign=middle;")
        if b64:
            return ("shape=label;" + base + "spacingLeft=46;imageWidth=28;imageHeight=28;imageAlign=left;"
                    "imageVerticalAlign=middle;image=data:image/svg+xml," + b64 + ";")
        return base + "spacingLeft=12;"
    if kind == "actor":
        return ("shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;"
                "fillColor=#E8F0FE;strokeColor=#5F6368;fontSize=11;")
    if kind == "database":
        return ("shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;size=10;fillColor=#FFFFFF;"
                "strokeColor=#5F6368;fontSize=11;")
    return "rounded=1;arcSize=8;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#9AA0A6;fontSize=11;"


def node_label(kind: str, label: str, product: str | None) -> str:
    if kind == "card" and product:
        return f"<b>{label}</b><br><font color=\"#80868B\">{product}</font>"
    return label


def zone_style(kind: str, index: int = 0) -> str:
    common = ("container=1;collapsible=0;html=1;whiteSpace=wrap;rounded=1;absoluteArcSize=1;arcSize=6;"
              "align=left;verticalAlign=top;spacingLeft=10;spacingTop=4;fontSize=12;")
    if kind == "cloud":
        return common + "fillColor=#F1F3F4;strokeColor=none;fontStyle=1;fontColor=#5F6368;fontSize=14;"
    if kind == "external":
        return common + f"fillColor={EXTERNAL_FILLS[index % len(EXTERNAL_FILLS)]};strokeColor=none;fontColor=#5F6368;"
    if kind == "plain":
        return common + "fillColor=#FFFFFF;strokeColor=#DADCE0;fontColor=#3C4043;fontStyle=1;"
    return common + "fillColor=none;strokeColor=#4284F3;dashed=1;dashPattern=1 2;strokeWidth=2;fontColor=#80868B;"


def edge_style(color: str, dashed: bool = False, both: bool = False, step: bool = False) -> str:
    s = (f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=blockThin;endFill=1;endSize=4;"
         f"strokeWidth=2;strokeColor={color};fontSize=11;fontColor=#3C4043;labelBackgroundColor=#FFFFFF;")
    if dashed:
        s += "dashed=1;"
    if both:
        s += "startArrow=blockThin;startFill=1;startSize=4;"
    if step:
        s = s.replace("labelBackgroundColor=#FFFFFF;fontColor=#3C4043;", "")
        s += f"labelBackgroundColor={color};fontColor=#FFFFFF;fontStyle=1;fontSize=13;"
    return s


NOTE_STYLE = ("shape=note;size=10;whiteSpace=wrap;html=1;fillColor=#FEF7E0;strokeColor=#F9AB00;"
              "fontSize=10;align=left;spacingLeft=6;verticalAlign=top;")
TITLE_STYLE = "text;html=1;align=left;verticalAlign=middle;fontSize=20;fontStyle=1;fontColor=#202124;"
LEGEND_ITEM = ("rounded=1;arcSize=20;html=1;whiteSpace=wrap;fillColor=#FFFFFF;strokeWidth=2;"
               "fontSize=11;fontColor=#202124;align=left;spacingLeft=10;")

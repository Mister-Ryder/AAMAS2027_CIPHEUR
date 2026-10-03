"""Build native draw.io scientific schematics and editable PDF/PNG exports.

Run from the repository root with .venv/Scripts/python.exe.
The figures use explicit coordinates because graph topology, equality joins,
and residual update order carry scientific meaning. Exporting uses draw.io
Desktop, never a generic raster renderer.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import struct
from urllib.parse import quote, unquote
import xml.etree.ElementTree as ET
import zlib


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "figures"
DRAWIO = Path(r"C:\Program Files\draw.io\draw.io.exe")
BLUE = "#176B9B"
ORANGE = "#D36B32"
GRAY = "#687782"
INK = "#243640"
LIGHT = "#EAF3F8"
PALE = "#FCF0E8"
LINE = "#C8D2D9"


class Figure:
    def __init__(self, name, width, height):
        self.name, self.width, self.height = name, width, height
        self.model = ET.Element("mxGraphModel", {
            "dx": str(width), "dy": str(height), "grid": "0", "gridSize": "10",
            "page": "0", "pageScale": "1", "pageWidth": str(width),
            "pageHeight": str(height), "background": "#FFFFFF",
            "math": "0", "shadow": "0", "adaptiveColors": "auto"})
        self.root = ET.SubElement(self.model, "root")
        ET.SubElement(self.root, "mxCell", {"id": "0"})
        ET.SubElement(self.root, "mxCell", {"id": "1", "parent": "0"})
        self.serial = 1
        # Fixed white canvas gives all exports the same intended dimensions.
        self.rect(0, 0, width, height, fill="#FFFFFF", stroke="none")

    def cell(self, value, style, x, y, w, h):
        self.serial += 1
        cell = ET.SubElement(self.root, "mxCell", {
            "id": str(self.serial), "value": value, "style": style,
            "vertex": "1", "parent": "1"})
        ET.SubElement(cell, "mxGeometry", {
            "x": str(x), "y": str(y), "width": str(w), "height": str(h),
            "as": "geometry"})
        return str(self.serial)

    def text(self, value, x, y, w, h=24, size=13, color=INK, bold=False,
             align="left"):
        size = max(size, 12.5)
        return self.cell(value,
                         "text;html=1;whiteSpace=wrap;overflow=hidden;"
                         f"fontFamily=Arial;fontSize={size};fontColor={color};"
                         f"fontStyle={1 if bold else 0};align={align};"
                         "verticalAlign=middle;spacing=0;strokeColor=none;fillColor=none;",
                         x, y, w, h)

    def rect(self, x, y, w, h, fill="none", stroke=LINE, label="", size=13,
             color=INK, bold=False, dashed=False, sw=1, align="center"):
        size = max(size, 12.5)
        return self.cell(label,
                         f"rounded=0;html=1;whiteSpace=wrap;fontFamily=Arial;fontSize={size};"
                         f"fontColor={color};fontStyle={1 if bold else 0};align={align};"
                         f"verticalAlign=middle;fillColor={fill};strokeColor={stroke};"
                         f"strokeWidth={sw};dashed={1 if dashed else 0};spacing=6;",
                         x, y, w, h)

    def node(self, label, x, y, d=30, fill="#FFFFFF", stroke=GRAY, color=INK,
             size=13, sw=1.3):
        size = max(size, 12.5)
        return self.cell(label,
                         f"ellipse;html=1;whiteSpace=wrap;fontFamily=Arial;fontSize={size};"
                         f"fontColor={color};fontStyle=1;fillColor={fill};strokeColor={stroke};"
                         f"strokeWidth={sw};align=center;verticalAlign=middle;spacing=0;",
                         x-d/2, y-d/2, d, d)

    def line(self, x1, y1, x2, y2, color=GRAY, sw=1.3, arrow=False,
             dashed=False, via=()):
        self.serial += 1
        cell = ET.SubElement(self.root, "mxCell", {
            "id": str(self.serial), "edge": "1", "parent": "1",
            "style": f"html=1;strokeColor={color};strokeWidth={sw};"
                     f"endArrow={'block' if arrow else 'none'};endFill=1;"
                     f"dashed={1 if dashed else 0};rounded=0;"})
        geom = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        ET.SubElement(geom, "mxPoint", {"x": str(x1), "y": str(y1), "as": "sourcePoint"})
        ET.SubElement(geom, "mxPoint", {"x": str(x2), "y": str(y2), "as": "targetPoint"})
        if via:
            points = ET.SubElement(geom, "Array", {"as": "points"})
            for x, y in via:
                ET.SubElement(points, "mxPoint", {"x": str(x), "y": str(y)})

    def save(self):
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / f"{self.name}.drawio"
        mxfile = ET.Element("mxfile", {"host": "app.diagrams.net", "type": "device"})
        diagram = ET.SubElement(mxfile, "diagram", {"name": self.name, "id": self.name})
        diagram.append(self.model)
        ET.ElementTree(mxfile).write(path, encoding="utf-8", xml_declaration=True)
        ET.parse(path)
        return path


def motivation():
    f = Figure("motivation", 680, 348)
    f.text("(a) Ground gap = 0", 12, 5, 318, 26, bold=True)
    f.text("(b) Ground gap = 4", 352, 5, 318, 26, bold=True)
    f.line(340, 6, 340, 224, color=LINE, sw=1)
    for off, after in ((0, False), (340, True)):
        pos = {"a": (off+119, 107), "b": (off+220, 107),
               "X1": (off+45, 67), "X2": (off+20, 107), "X3": (off+45, 147),
               "Y1": (off+295, 67), "Y2": (off+305, 107), "Y3": (off+295, 147)}
        f.text("X: one station", off+8, 31, 126, 23, size=12, color=GRAY)
        f.text("Y: distinct stations", off+179, 31, 150, 23, size=12, color=GRAY,
               align="right")
        for u, v in [("a", "b")] + [("a", f"X{i}") for i in range(1, 4)] + [
                ("b", f"Y{i}") for i in range(1, 4)] + [("Y1", "Y2")]:
            f.line(*pos[u], *pos[v], color=GRAY, sw=1.15)
        if after:
            for u, v in (("X1", "X2"), ("X2", "X3"), ("X1", "X3")):
                f.line(*pos[u], *pos[v], color=ORANGE, sw=2.3)
        for name, (x, y) in pos.items():
            preferred = name == ("a" if after else "b")
            root = name in ("a", "b")
            f.node(name, x, y, d=36 if root else 29,
                   fill=LIGHT if preferred else "#FFFFFF",
                   stroke=BLUE if preferred else GRAY, color=BLUE if preferred else INK,
                   sw=2 if preferred else 1.2)
        f.text("Root rewards: 8; peripheral rewards: 6", off+21, 168, 300, 20,
               size=12, color=GRAY, align="center")
        pref = "a" if after else "b"
        vb = 14 if after else 26
        f.rect(off+17, 193, 145, 31, fill=LIGHT if after else "#FFFFFF", stroke=BLUE if after else LINE,
               label="Commit a: <b>20</b>", color=BLUE if after else INK, sw=1.4 if after else 1)
        f.rect(off+176, 193, 145, 31, fill=LIGHT if not after else "#FFFFFF", stroke=BLUE if not after else LINE,
               label=f"Commit b: <b>{vb}</b>", color=BLUE if not after else INK, sw=1.4 if not after else 1)
        f.text(f"Certified preference: <b>{pref}</b>", off+17, 229, 304, 21,
               color=BLUE, align="center")
    f.text("Conditional increments V(d | B) − w(F); F contains independent z", 14, 254, 651,
           18, size=12, color=GRAY, align="center")
    f.line(12, 277, 668, 277, color=LINE, sw=1)
    f.text("Nine base inputs alias", 12, 284, 219, 22, bold=True)
    f.text("φ₀(a) = φ₀(b) on each side<br>Including resource-gap scalars", 12, 310, 221, 31,
           size=12, color=ORANGE)
    for x, label in ((265, "C₀"), (315, "C₁")):
        f.line(x-9, 309, x+9, 309, color=ORANGE, sw=1.5, arrow=True,
               via=((x-17, 293), (x+17, 293)))
        f.node(label, x, 318, d=28, fill=PALE, stroke=ORANGE, color=ORANGE, size=12)
    f.text("Missing statistic: edges inside N(v)", 354, 284, 310, 22, bold=True, color=BLUE)
    f.text("Before: a = 0, b = 1  |  After: a = 3, b = 1", 354, 310, 310, 30, size=12)
    return f


def problem_setting_wide():
    f = Figure("problem_setting-wide", 680, 250)
    f.text("(a) Fixed contact opportunities", 10, 4, 245, 27, bold=True)
    f.text("(b) Conflict graph Gθ", 272, 4, 184, 27, bold=True)
    f.text("(c) Feasible schedule", 482, 4, 188, 27, bold=True)
    # Timeline lanes make the shared ground resource visible.
    f.text("G1", 10, 63, 27, 22, bold=True)
    f.text("G2", 10, 164, 27, 22, bold=True)
    scale, origin = 16, 42
    contacts = [("a", 0, 4, 4, 55), ("b", 3, 6, 3, 85),
                ("c", 6.5, 8.5, 2, 115), ("d", 8, 11, 3, 145),
                ("e", 1, 4, 3, 170)]
    for name, start, end, w, y in contacts:
        f.rect(origin+scale*start, y, scale*(end-start), 22, fill="#F2F5F7", stroke=GRAY,
               label=f"{name}: {w}", size=12)
    f.line(origin, 206, origin+176, 206, color=GRAY, arrow=True, sw=1)
    for time in (0, 4, 8):
        x = origin+scale*time
        f.line(x, 202, x, 210, sw=1)
        f.text(str(time), x-10, 211, 20, 19, size=12, color=GRAY, align="center")
    f.text("time", 222, 198, 29, 21, size=12, color=GRAY)
    f.line(238, 115, 266, 115, color=BLUE, arrow=True, sw=2)
    f.text("Ground gap = 1", 265, 37, 190, 22, size=12, color=GRAY, align="center")
    pos = {"a": (288, 91), "b": (343, 91), "c": (398, 91),
           "d": (398, 151), "e": (301, 170)}
    for u, v in (("a", "b"), ("b", "c"), ("c", "d")):
        f.line(*pos[u], *pos[v], sw=1.4)
    for name, (x, y) in pos.items():
        choose = name in {"a", "d", "e"}
        f.node(name, x, y, d=30, fill=LIGHT if choose else "#FFFFFF",
               stroke=BLUE if choose else GRAY, color=BLUE if choose else INK,
               sw=1.7 if choose else 1.2)
    f.text("Edge = joint infeasibility", 270, 207, 191, 23, size=12, color=GRAY, align="center")
    f.line(445, 115, 475, 115, color=BLUE, arrow=True, sw=2)
    f.text("I = {a, d, e}; reward = 10", 482, 39, 190, 25, color=BLUE, bold=True)
    f.text("G1", 481, 94, 27, 22, bold=True)
    f.text("G2", 481, 143, 27, 22, bold=True)
    for name, start, end, y in (("a", 0, 4, 94), ("d", 8, 11, 94), ("e", 1, 4, 143)):
        f.rect(512+13*start, y, 13*(end-start), 23, fill=LIGHT, stroke=BLUE,
               label=name, color=BLUE, bold=True)
    f.line(512, 194, 660, 194, color=GRAY, arrow=True, sw=1)
    f.text("a and d satisfy the gap", 481, 207, 189, 23, size=12, color=GRAY, align="center")
    return f


def problem_setting():
    """Column-width version: preserve labels instead of shrinking a wide strip."""
    f = Figure("problem_setting", 330, 400)
    f.text("(a) Contacts: ground gap = 1", 8, 3, 314, 22, bold=True)
    origin, scale = 43, 22
    for name, start, end, w, y in (("a", 0, 4, 4, 33), ("b", 3, 6, 3, 56),
                                  ("c", 6.5, 8.5, 2, 79), ("d", 8, 11, 3, 102),
                                  ("e", 1, 4, 3, 125)):
        f.rect(origin+scale*start, y, scale*(end-start), 21, fill="#F2F5F7", stroke=GRAY,
               label=f"{name}: {w}", size=12)
    f.text("G1", 8, 69, 30, 20, bold=True)
    f.text("G2", 8, 125, 30, 21, bold=True)
    f.line(origin, 156, 301, 156, arrow=True, sw=1)
    for time in (0, 4, 8):
        x = origin+scale*time
        f.line(x, 152, x, 159, sw=1)
        f.text(str(time), x-9, 161, 18, 18, size=12, color=GRAY, align="center")
    f.text("time", 302, 147, 27, 21, size=12, color=GRAY)
    f.line(165, 181, 165, 192, color=BLUE, sw=1.7, arrow=True)
    f.text("(b) Pairwise conflict graph", 8, 195, 314, 22, bold=True)
    pos = {"a": (44, 239), "b": (101, 239), "c": (158, 239),
           "d": (215, 239), "e": (289, 239)}
    for u, v in (("a", "b"), ("b", "c"), ("c", "d")):
        f.line(*pos[u], *pos[v], sw=1.4)
    for name, (x, y) in pos.items():
        selected = name in {"a", "d", "e"}
        f.node(name, x, y, d=30, fill=LIGHT if selected else "#FFFFFF",
               stroke=BLUE if selected else GRAY, color=BLUE if selected else INK,
               sw=1.7 if selected else 1.2)
    f.line(165, 260, 165, 270, color=BLUE, sw=1.7, arrow=True)
    f.text("(c) I = {a, d, e}; reward = 10", 8, 274, 314, 22, bold=True, color=BLUE)
    f.text("G1", 8, 310, 30, 21, bold=True)
    f.text("G2", 8, 345, 30, 21, bold=True)
    for name, start, end, y in (("a", 0, 4, 310), ("d", 8, 11, 310), ("e", 1, 4, 345)):
        f.rect(origin+scale*start, y, scale*(end-start), 22, fill=LIGHT, stroke=BLUE,
               label=name, color=BLUE, bold=True)
    f.line(origin, 377, 301, 377, arrow=True, sw=1)
    for time in (0, 4, 8):
        x = origin+scale*time
        f.line(x, 373, x, 380, sw=1)
        f.text(str(time), x-9, 381, 18, 18, size=12, color=GRAY, align="center")
    f.text("time", 302, 368, 27, 21, size=12, color=GRAY)
    return f


def method_overview():
    f = Figure("method_overview", 680, 290)
    f.rect(8, 1, 664, 19, fill="#F2F5F7", stroke="none")
    f.text("OFFLINE SYNTHESIS  ·  training interventions + validation schedules", 18, 1, 644,
           19, bold=True)
    # Aligned interventions, certified intervals, accumulated requirements.
    f.rect(8, 25, 202, 73, stroke=LINE)
    f.text("Aligned static problems", 18, 28, 182, 19, bold=True)
    f.text("Contacts and rewards fixed<br>Same boundary B = (F, X)<br>Common feasible conflict: a, b",
           18, 49, 182, 46, size=12)
    f.rect(239, 25, 202, 73, fill=LIGHT, stroke=BLUE, sw=1.5)
    f.text("Full-residual certificates", 249, 28, 182, 19, bold=True, color=BLUE)
    f.text("θ₀: L(b) &gt; U(a) + ε<br>θ₁: L(a) &gt; U(b) + ε<br>Overlap / tie / budget: unknown",
           249, 49, 182, 46, size=12)
    f.rect(470, 25, 202, 73, stroke=LINE)
    f.text("Strict requirements", 480, 28, 182, 19, bold=True)
    f.text("h(φ(x⁺)) &gt; h(φ(x⁻))<br>Reversal + preservation<br>Replay all earlier requirements",
           480, 49, 182, 46, size=12)
    f.line(210, 62, 237, 62, color=BLUE, sw=1.8, arrow=True)
    f.line(441, 62, 468, 62, color=BLUE, sw=1.8, arrow=True)
    # Diagnosis and repair are the actual center, not a generic workflow.
    f.rect(8, 112, 202, 84, fill=PALE, stroke=ORANGE, sw=1.6)
    f.text("Exact quotient diagnosis", 18, 115, 182, 19, bold=True, color=ORANGE)
    f.text("Cycle → no scalar score of φ", 18, 136, 182, 18, size=12)
    f.text("x₁⁺ → x₁⁻ ≡φ x₂⁺<br>x₂⁺ → x₂⁻ ≡φ x₁⁺", 31, 157, 168, 34, size=13,
           color=ORANGE)
    f.text("Concrete arcs + equality joins", 9, 199, 211, 18, size=12, color=GRAY)
    f.rect(239, 112, 202, 84, fill=LIGHT, stroke=BLUE, sw=1.5)
    f.text("LLM: typed catalogue", 249, 115, 182, 19, bold=True, color=BLUE)
    f.text("NodeSet → EdgeSet → Number", 249, 136, 182, 18, size=12)
    f.text("Minimum-cost master", 249, 156, 182, 19, bold=True)
    f.text("min Σ c<sub>f</sub> z<sub>f</sub>;  Σ d<sub>Wf</sub> z<sub>f</sub> ≥ 1", 249, 176, 182, 18, size=12)
    f.rect(470, 112, 202, 84, stroke=BLUE, sw=1.5)
    f.text("Full quotient separation", 480, 115, 182, 19, bold=True, color=BLUE)
    f.text("Surviving cycle: add witness<br>DAG: observed repair passes<br>Budget / no feature: unresolved",
           480, 138, 182, 52, size=12)
    f.line(571, 99, 109, 110, color=GRAY, sw=1.25, arrow=True,
           via=((571, 104), (109, 104)))
    f.line(210, 154, 237, 154, color=BLUE, sw=1.8, arrow=True)
    f.line(441, 154, 468, 154, color=BLUE, sw=1.8, arrow=True)
    f.line(570, 197, 339, 197, color=ORANGE, sw=1.8, arrow=True,
           via=((570, 201), (339, 201)))
    f.text("cycle: add cut; resolve master", 355, 203, 224, 17, size=12, color=ORANGE)
    f.rect(239, 223, 433, 39, stroke=LINE)
    f.text("LLM rule proposals + joint selection", 249, 225, 413, 18, bold=True)
    f.text("Replay s(P); assess schedule quality q(P) and compiled work c(P)",
           249, 245, 413, 16, size=12)
    f.line(640, 197, 640, 221, color=BLUE, sw=1.5, arrow=True)
    f.text("DAG", 585, 199, 47, 19, size=12, color=BLUE, align="right")
    f.rect(8, 223, 202, 39, fill=LIGHT, stroke=BLUE, sw=1.5)
    f.text("Freeze (φ, h, kernel)", 18, 225, 181, 18, bold=True, color=BLUE)
    f.text("Eligible quality–work tradeoff", 18, 245, 181, 16, size=12)
    f.line(237, 242, 212, 242, color=BLUE, sw=1.8, arrow=True)
    f.line(8, 267, 672, 267, color=GRAY, sw=1.4, dashed=True)
    f.text("ONLINE", 10, 271, 60, 17, bold=True, color=BLUE)
    f.text("Current graph → compiled φ → frozen h → commit argmax → delete closed neighborhood",
           80, 270, 590, 19, size=12, color=BLUE)
    f.line(109, 263, 109, 269, color=BLUE, arrow=True, sw=1.4)
    return f


def repair_cycle():
    f = Figure("repair_cycle", 680, 260)
    f.text("(a) Coarse quotient", 8, 4, 192, 26, bold=True)
    f.text("(b) Cheap feature: cost 1", 221, 4, 216, 26, bold=True, color=ORANGE)
    f.text("(c) Separating feature: cost 2", 454, 4, 218, 26, bold=True, color=BLUE)
    f.line(211, 8, 211, 212, color=LINE, sw=1)
    f.line(446, 8, 446, 212, color=LINE, sw=1)
    # Coarse two-cycle; the displayed concrete witness uses requirements 1,2.
    f.line(55, 62, 166, 62, color=ORANGE, arrow=True, sw=1.8,
           via=((55, 51), (166, 51)))
    f.line(166, 104, 55, 104, color=ORANGE, arrow=True, sw=1.8,
           via=((166, 117), (55, 117)))
    f.node("A", 55, 83, d=40, fill=PALE, stroke=ORANGE, color=ORANGE)
    f.node("B", 166, 83, d=40, fill=PALE, stroke=ORANGE, color=ORANGE)
    f.text("r₁, r₃", 86, 31, 56, 19, size=12, color=ORANGE, align="center")
    f.text("r₂, r₄", 86, 119, 56, 20, size=12, color=ORANGE, align="center")
    f.text("Concrete witness W₁", 8, 144, 193, 21, bold=True)
    f.text("a₁ → b₁ ≡ b₂ → a₂ ≡ a₁", 8, 166, 193, 23, size=12)
    f.text("cheap breaks a₂ ≡ a₁", 8, 190, 193, 21, size=12, color=ORANGE)
    # The complete refined quotient, not merely the displayed old witness.
    p = {"A0": (268, 83), "B0": (390, 83), "A1": (390, 146), "B1": (268, 146)}
    for u, v, r, tx, ty in (("A0", "B0", "r₁", 322, 55), ("B0", "A1", "r₂", 405, 104),
                            ("A1", "B1", "r₃", 322, 158), ("B1", "A0", "r₄", 232, 104)):
        x1, y1 = p[u]; x2, y2 = p[v]
        if x1 == x2:
            y1 += 21 if y2 > y1 else -21
            y2 += -21 if y2 > y1 else 21
        else:
            x1 += 21 if x2 > x1 else -21
            x2 += -21 if x2 > x1 else 21
        f.line(x1, y1, x2, y2, color=ORANGE, arrow=True, sw=1.9)
        f.text(r, tx, ty, 25, 22, size=12, color=ORANGE, align="center")
    for name, (x, y) in p.items():
        f.node(name, x, y, d=42, fill=PALE, stroke=ORANGE, color=ORANGE)
    f.text("a₁, a₄", 241, 34, 60, 22, size=12, color=GRAY, align="center")
    f.text("b₁, b₂", 360, 34, 60, 22, size=12, color=GRAY, align="center")
    f.text("a₂, a₃", 359, 179, 60, 22, size=12, color=GRAY, align="center")
    f.text("b₃, b₄", 239, 179, 60, 22, size=12, color=GRAY, align="center")
    # Unique occurrence values turn all requirements into disjoint DAG arcs.
    for i, (a, b) in enumerate((("a₁", "b₁"), ("b₂", "a₂"), ("a₃", "b₃"), ("b₄", "a₄"))):
        y = 57 + i*40
        f.line(517, y, 605, y, color=BLUE, arrow=True, sw=1.6)
        f.node(a, 499, y, d=30, fill=LIGHT, stroke=BLUE, color=BLUE, sw=1.2)
        f.node(b, 625, y, d=30, fill=LIGHT, stroke=BLUE, color=BLUE, sw=1.2)
        f.text(f"r{('₁', '₂', '₃', '₄')[i]}", 554, y-24, 27, 20, size=12, color=BLUE, align="center")
    f.text("Every occurrence has a distinct value", 454, 194, 218, 20, size=12, color=BLUE,
           align="center")
    f.line(8, 217, 672, 217, color=LINE, sw=1)
    f.text("Round 1: cover W₁ → cheap (cost 1), but the full quotient still cycles", 10, 221, 660,
           17, size=12, color=ORANGE)
    f.text("Round 2: add W₂ → replace cheap with repair (cost 2); full quotient is a DAG", 10, 241, 660,
           17, size=12, color=BLUE)
    return f


def compiled_updates_wide():
    f = Figure("compiled_updates-wide", 680, 337)
    f.text("(a) Shared typed expression DAG", 8, 4, 324, 27, bold=True)
    f.text("(b) Sequential residual deletion", 347, 4, 325, 27, bold=True)
    f.line(335, 8, 335, 280, color=LINE, sw=1)
    # Typed DAG with real common subexpression sharing.
    f.rect(15, 46, 91, 31, fill=LIGHT, stroke=BLUE, label="root: Node", size=12)
    f.rect(15, 99, 166, 34, fill=LIGHT, stroke=BLUE, label="neighbors: NodeSet", size=12)
    f.rect(15, 157, 166, 34, fill=LIGHT, stroke=BLUE, label="induced_edges: EdgeSet", size=12)
    f.rect(217, 99, 105, 38, stroke=BLUE, label="count → Number", size=12)
    f.rect(217, 157, 105, 48, stroke=BLUE, label="min-weight sum<br>→ Number", size=12)
    f.line(59, 77, 59, 97, color=BLUE, arrow=True, sw=1.4)
    f.line(99, 133, 99, 155, color=BLUE, arrow=True, sw=1.4)
    f.line(181, 174, 215, 118, color=BLUE, arrow=True, sw=1.4,
           via=((198, 174), (198, 118)))
    f.line(181, 181, 215, 181, color=BLUE, arrow=True, sw=1.4)
    f.text("Share repeated subexpressions.<br>Cache only within the valid residual state.<br>Unrecognized expressions use the interpreter.",
           15, 222, 306, 57, size=12, color=GRAY)
    # Two triangles share the edge (1,2), matching the deletion regression.
    pos = {"0": (384, 72), "1": (429, 117), "2": (383, 163), "3": (481, 164), "4": (532, 164)}
    for u, v in (("0", "1"), ("0", "2"), ("1", "2"), ("1", "3"), ("2", "3"), ("3", "4")):
        f.line(*pos[u], *pos[v], sw=1.25)
    for name, (x, y) in pos.items():
        deleted = name in {"0", "1"}
        tracked = name == "2"
        f.node(name, x, y, d=29, fill=PALE if deleted else LIGHT if tracked else "#FFFFFF",
               stroke=ORANGE if deleted else BLUE if tracked else GRAY,
               color=ORANGE if deleted else BLUE if tracked else INK)
    f.text("w₀ = 2, w₁ = 3, w₂ = 5,<br>w₃ = 7, w₄ = 11", 466, 48, 194, 44, size=12, color=GRAY)
    f.text("Track surviving root v = 2", 352, 194, 309, 22, bold=True, color=BLUE)
    f.text("T₂: 5 ── delete 0 → 3 ── delete 1 → 0", 352, 221, 315, 26, size=13, color=BLUE)
    f.text("Each step reads the updated residual neighborhood.", 352, 253, 314, 26,
           size=12, color=GRAY)
    f.rect(557, 107, 111, 73, fill=PALE, stroke=ORANGE, label="Snapshot batch<br>subtracts {0,1}<br>twice: T₂ = −2", size=12, color=ORANGE)
    f.line(8, 289, 672, 289, color=LINE, sw=1)
    f.text("T(v) ← T(v) − Σ min(wₓ, wᵧ),   y ∈ N<sub>R</sub>(v) ∩ N<sub>R</sub>(x),   before deleting x", 11,
           296, 659, 24, size=13, color=BLUE)
    f.text("Preserve the interpreter’s numeric interface; charge initialization, intersections, updates, caches and scoring.",
           11, 319, 659, 18, size=12, color=GRAY)
    return f


def compiled_updates():
    """Column-width version with unchanged feature types and deletion example."""
    f = Figure("compiled_updates", 330, 427)
    f.text("(a) Share a typed expression DAG", 8, 3, 314, 22, bold=True)
    f.rect(8, 33, 120, 28, fill=LIGHT, stroke=BLUE, label="root: Node", size=12)
    f.rect(8, 78, 150, 31, fill=LIGHT, stroke=BLUE, label="neighbors: NodeSet", size=12)
    f.rect(8, 124, 150, 32, fill=LIGHT, stroke=BLUE, label="induced_edges: EdgeSet", size=12)
    f.rect(188, 78, 134, 31, stroke=BLUE, label="count: Number", size=12)
    f.rect(188, 124, 134, 32, stroke=BLUE, label="min-weight sum: Number", size=12)
    f.line(68, 62, 68, 76, color=BLUE, arrow=True, sw=1.4)
    f.line(83, 110, 83, 122, color=BLUE, arrow=True, sw=1.4)
    f.line(159, 138, 186, 93, color=BLUE, arrow=True, sw=1.4,
           via=((173, 138), (173, 93)))
    f.line(159, 147, 186, 147, color=BLUE, arrow=True, sw=1.4)
    f.text("Shared nodes; cache per residual state.", 8, 166, 314, 20, size=12, color=GRAY)
    f.line(8, 190, 322, 190, color=LINE, sw=1)
    f.text("(b) Sequential deletion preserves T(2)", 8, 195, 314, 22, bold=True)
    pos = {"0": (31, 245), "1": (86, 231), "2": (86, 287),
           "3": (145, 259), "4": (195, 259)}
    for u, v in (("0", "1"), ("0", "2"), ("1", "2"), ("1", "3"), ("2", "3"), ("3", "4")):
        f.line(*pos[u], *pos[v], sw=1.2)
    for name, (x, y) in pos.items():
        deleted, tracked = name in {"0", "1"}, name == "2"
        f.node(name, x, y, d=28, fill=PALE if deleted else LIGHT if tracked else "#FFFFFF",
               stroke=ORANGE if deleted else BLUE if tracked else GRAY,
               color=ORANGE if deleted else BLUE if tracked else INK)
    f.text("w₀ = 2<br>w₁ = 3<br>w₃ = 7", 222, 224, 95, 48, size=12, color=GRAY)
    f.rect(218, 279, 104, 39, fill=PALE, stroke=ORANGE,
           label="Batch: T₂ = −2<br>{0,1} twice", size=12, color=ORANGE)
    f.text("T₂: 5 → delete 0: 3 → delete 1: 0", 8, 328, 314, 23,
           size=13, color=BLUE, bold=True)
    f.text("T(v) ← T(v) − Σ min(wₓ, wᵧ)<br>y ∈ N<sub>R</sub>(v) ∩ N<sub>R</sub>(x), before deleting x",
           8, 355, 314, 38, size=12, color=BLUE)
    f.text("Charge initialization, queries and updates.<br>Unrecognized expressions: interpreter.",
           8, 398, 314, 29, size=12, color=GRAY)
    return f


def verify_semantics():
    """Check scientific numbers and fixture topology, independent of drawing."""
    import sys
    sys.path.insert(0, str(ROOT))
    from cipheur.experiment_data import diagnostic_pair
    from cipheur.graph_features import FeatureRuleProgram
    from cipheur.oracle import solve
    from cipheur.refinement import diagnose_occurrences, minimum_cost_vector_refinement
    from cipheur.compiled import CompiledEvaluator
    from cipheur.model import Contact, Graph, temporal_graph
    from tests.test_innovation_v03 import vector_cycle

    pair = diagnostic_pair("train", 0, "reversal")
    ids, scale = pair["source"]["semantic_roles"], pair["source"]["weight_scale"]
    base = FeatureRuleProgram("figure_audit", [], "weight")
    actual = []
    for g in (pair["left"], pair["right"]):
        active = g.available(pair["fixed"], pair["excluded"])
        assert base.evaluate_features(g, ids["a"], active) == base.evaluate_features(g, ids["b"], active)
        for role in ("a", "b"):
            result = solve(g, fixed=tuple(pair["fixed"]) + (ids[role],))
            actual.append((result.lower-g.value(pair["fixed"]))/scale)
    assert actual == [20, 26, 20, 14], actual
    additions = pair["right"].edges-pair["left"].edges
    expected = {tuple(sorted((ids[u], ids[v]))) for u, v in (("x1", "x2"), ("x2", "x3"), ("x1", "x3"))}
    assert additions == expected
    assert pair["left"].constraints["station_gap"] == 0
    assert pair["right"].constraints["station_gap"] == 4
    assert pair["left"].constraints["satellite_gap"] == pair["right"].constraints["satellite_gap"] == 0
    counts = []
    for g in (pair["left"], pair["right"]):
        for role in ("a", "b"):
            n = g.adj[ids[role]]
            counts.append(sum(u in n and v in n for u, v in g.edges))
    assert counts == [0, 1, 3, 1], counts
    occurrences, requirements, features, costs = vector_cycle()
    assert diagnose_occurrences(occurrences, requirements, features, ("cheap",))["contradictory"]
    result = minimum_cost_vector_refinement(occurrences, requirements, features, costs)
    assert result["selected_names"] == ["repair"] and result["cost_exact"] == "2"
    assert len(result["rounds"]) == 2
    edges = frozenset((str(a), str(b)) for a, b in [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (3, 4)])
    contacts = tuple(Contact(str(i), w, f"S{i}", f"G{i}", i, i+1) for i, w in enumerate([2, 3, 5, 7, 11]))
    g = Graph("figure_deletion", contacts, edges)
    expression = {"op": "edge_min_weight_sum", "args": [{"op": "induced_edges", "args": [
        {"op": "neighbors", "args": [{"op": "root", "args": []}]}]}]}
    p = FeatureRuleProgram("figure_updates", [{"name": "T", "expression": expression}], "T")
    evaluator = CompiledEvaluator(g, p, g.nodes)
    values = [evaluator.feature_values("2")["T"]]
    for removed in ("0", "1"):
        evaluator.remove([removed])
        values.append(evaluator.feature_values("2")["T"])
        assert evaluator.feature_values("2") == p.evaluate_features(g, "2", evaluator.active)
    assert values == [5, 3, 0], values
    # The small scheduling illustration uses distinct satellites and one shared station.
    c = tuple(Contact(n, w, f"S{n}", "G2" if n == "e" else "G1", start, end)
              for n, start, end, w in (("a", 0, 4, 4), ("b", 3, 6, 3), ("c", 6.5, 8.5, 2),
                                       ("d", 8, 11, 3), ("e", 1, 4, 3)))
    g = temporal_graph("figure_problem", c, station_gap=1, satellite_gap=0)
    assert g.edges == frozenset({("a", "b"), ("b", "c"), ("c", "d")})
    assert g.feasible(("a", "d", "e")) and g.value(("a", "d", "e")) == 10
    print("Scientific semantics verified: 4 conditional values, equal base interfaces, 3 added X edges, 4-cycle repair, sequential updates, schedule feasibility.")


def psquote(value):
    return "'" + str(value).replace("'", "''") + "'"


def export(source, fmt):
    destination = source.with_suffix(f".drawio.{fmt}")
    # Input must precede --disable-gpu in this Desktop CLI build: otherwise
    # the unlisted Electron flag is mistakenly treated as the input argument.
    arguments = [f'"{source}"', "--disable-gpu", "-x", "-f", fmt, "-e", "-b", "0", "-o",
                 f'"{destination}"']
    if fmt == "png":
        arguments.extend(["-s", "3"])
    command = (f"$figureArgs = @({','.join(psquote(a) for a in arguments)}); "
               f"$figureProcess = Start-Process -FilePath {psquote(DRAWIO)} "
               "-ArgumentList $figureArgs -WindowStyle Hidden -Wait -PassThru; "
               "exit $figureProcess.ExitCode")
    subprocess.run(["powershell.exe", "-NoProfile", "-Command", command], check=True)
    if not destination.exists() or destination.stat().st_size < 1000:
        raise RuntimeError(f"Export failed: {destination}")
    if fmt == "png":
        normalize_png_metadata(destination, source.read_text(encoding="utf-8"))
    print(f"Exported {destination.name}: {destination.stat().st_size:,} bytes")
    return destination


def normalize_png_metadata(path, native_xml):
    """Repair Desktop's malformed embedded PNG metadata, without pixel edits.

    This installed export build writes a raw-deflate zTXt payload, incorrect
    ancillary CRC, and no IEND. Keep IHDR/color/IDAT bytes unchanged and write
    the same URL-encoded native XML as a standards-compliant tEXt chunk under
    draw.io's recognized mxGraphModel key. All original pixel bytes survive.
    """
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    result = bytearray(data[:8])
    def chunk(kind, payload):
        return (struct.pack(">I", len(payload)) + kind + payload
                + struct.pack(">I", zlib.crc32(kind+payload)))
    payload = b"mxGraphModel\x00" + quote(native_xml, safe="").encode("ascii")
    metadata = chunk(b"tEXt", payload)
    position = 8
    inserted = False
    while position+12 <= len(data):
        length = struct.unpack(">I", data[position:position+4])[0]
        kind = data[position+4:position+8]
        payload = data[position+8:position+8+length]
        if position+12+length > len(data):
            raise ValueError(f"Truncated PNG pixel stream: {path}")
        # draw.io's native PNG reader stops at the first IDAT chunk.
        if kind == b"IDAT" and not inserted:
            result.extend(metadata)
            inserted = True
        if kind not in (b"zTXt", b"tEXt", b"iTXt", b"IEND"):
            result.extend(data[position:position+12+length])
        position += 12+length
    assert inserted, f"PNG has no compressed pixel stream: {path}"
    result.extend(chunk(b"IEND", b""))
    path.write_bytes(result)


def verify_exports(paths):
    from PIL import Image
    from pypdf import PdfReader
    for name in paths:
        pdf, png = OUT / f"{name}.drawio.pdf", OUT / f"{name}.drawio.png"
        reader = PdfReader(pdf)
        assert len(reader.pages) == 1
        native_xml = unquote(reader.metadata.get("/Subject", ""))
        assert ET.fromstring(native_xml).tag == "mxfile", f"No editable XML in {pdf.name}"
        with Image.open(png) as image:
            image.load()
            assert image.size[0] >= 950
            assert ET.fromstring(unquote(image.info.get("mxGraphModel", ""))).tag == "mxfile", f"No editable XML in {png.name}"
        page = reader.pages[0]
        print(f"Verified {name}: PDF {float(page.mediabox.width):.2f} × {float(page.mediabox.height):.2f} pt; editable XML in both exports")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-source", action="store_true", help="Retain native editable .drawio sources")
    parser.add_argument("--only", nargs="*", help="Rebuild named figures only")
    args = parser.parse_args()
    verify_semantics()
    if not DRAWIO.exists():
        raise FileNotFoundError(f"draw.io Desktop CLI not found: {DRAWIO}")
    builders = [motivation, problem_setting, method_overview, repair_cycle, compiled_updates,
                problem_setting_wide, compiled_updates_wide]
    built = []
    for builder in builders:
        if args.only and builder.__name__ not in args.only:
            continue
        figure = builder()
        source = figure.save()
        for fmt in ("pdf", "png"):
            export(source, fmt)
        built.append(figure.name)
        if not args.keep_source:
            source.unlink()
    verify_exports(built)


if __name__ == "__main__":
    main()

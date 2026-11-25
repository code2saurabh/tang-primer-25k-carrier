"""Build kicad/carrier_v2.kicad_pcb: outline, placement and DF40 fan-out (PLAN step 8).

Run with KiCad's Python:  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" gen_pcb.py
Inputs : kicad/carrier_v2.net.xml (from the verified schematic), sources/sipeed_official/dock_layout.json
Output : kicad/carrier_v2.kicad_pcb (+ design rules in carrier_v2.kicad_pro / carrier_v2.kicad_dru)

Mechanical layout copies Sipeed's 25K Dock (same coordinates): board outline, module sockets J1/J2,
40-pin J3, PMOD J4/J5/J6, JTAG J7, USB-C, mounting holes. Each copied part is placed by matching its
pad set to the Dock's pads (pin 1 + every pad within 0.03 mm), so orientation cannot be wrong.
Fan-out (decision D12 in PLAN.md): each socket pad gets a 0.1 mm stub straight away from the
socket body to a 0.46/0.2 mm via; vias alternate between two staggered rows. No vias between pads.
"""
import json, math, xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
K = ROOT / "kicad"
PCB = K / "carrier_v2.kicad_pcb"
FPDIR = Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")
DOCK = json.loads((ROOT / "sources" / "sipeed_official" / "dock_layout.json").read_text(encoding="utf-8"))

mm = pcbnew.FromMM
def V(x, y): return pcbnew.VECTOR2I(mm(x), mm(y))
def P(v): return (round(pcbnew.ToMM(v.x), 4), round(pcbnew.ToMM(v.y), 4))

# fan-out geometry (mm) - see PLAN.md D12
FAN_TRACK = 0.10
VIA_D, VIA_DRILL = 0.46, 0.20
VIA_ROW_A = 0.10 + VIA_D / 2           # from pad end to row-A via centre
VIA_ROW_STEP = 0.60                    # row A -> row B
MODULE_RECT = (120.85, 75.28, 143.75, 93.08)   # core board 22.9 x 17.8 centred on the Dock sockets

# ------------------------------------------------------------------ netlist
xml = ET.parse(K / "carrier_v2.net.xml").getroot()
COMPS = {c.get("ref"): (c.findtext("value"), c.findtext("footprint")) for c in xml.iter("comp")}
FIELDS = {c.get("ref"): {f.get("name"): f.text for f in c.iter("field") if f.get("name") == "MPN" and f.text}
          for c in xml.iter("comp")}
PIN_NET = {}
for n in xml.iter("net"):
    for nd in n.iter("node"):
        PIN_NET[(nd.get("ref"), nd.get("pin"))] = n.get("name")

board = pcbnew.NewBoard(str(PCB))
board.SetCopperLayerCount(4)
board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)    # In1 = solid GND plane: no signal routing on it
NETS = {}
for name in sorted(set(PIN_NET.values())):
    ni = pcbnew.NETINFO_ITEM(board, name)
    board.Add(ni)
    NETS[name] = ni


def load(fpid):
    lib, name = fpid.split(":")
    path = K / "carrier_v2.pretty" if lib == "carrier_v2" else FPDIR / f"{lib}.pretty"
    fp = pcbnew.FootprintLoad(str(path), name)
    assert fp, fpid
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


PLACED = {}


def put(ref, x, y, rot):
    value, fpid = COMPS[ref]
    fp = load(fpid)
    fp.SetReference(ref)
    fp.SetValue(value)
    board.Add(fp)
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(V(x, y))
    for pad in fp.Pads():
        net = PIN_NET.get((ref, pad.GetNumber()))
        if net:
            pad.SetNet(NETS[net])
    for name, val in FIELDS.get(ref, {}).items():          # keep schematic fields (MPN) in sync
        f = pcbnew.PCB_FIELD(fp, fp.GetNextFieldOrdinal() if hasattr(fp, "GetNextFieldOrdinal") else len(fp.GetFields()), name)
        f.SetText(val); f.SetVisible(False); f.SetLayer(pcbnew.F_Fab)
        fp.Add(f)
    if ref[:2] in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "C1", "C2", "C3", "C4", "C5", "C6", "C7",
                   "C8", "C9", "FB", "F1", "D1", "D2", "D3", "D4"):
        fp.Reference().SetLayer(pcbnew.F_Fab)              # tiny parts: designator on assembly layer only
    PLACED[ref] = fp
    return fp


def match_dock(ref, dock_ref, pad_type=None, pin1_names=("1",)):
    """Place `ref` so its pads coincide with the Dock footprint's pads. Returns (x, y, rot).

    Our pin-1 pad (one of `pin1_names`) must land on the Dock's pin-1 pad. Without that, a
    symmetric footprint (DF40!) also 'matches' rotated 180 deg with every pin number reversed."""
    d = DOCK["footprints"][dock_ref]
    dpads = [p for p in d["pads"] if pad_type is None or p["type"] == pad_type]
    pin1 = next(p for p in d["pads"] if p.get("pin1"))
    fp = load(COMPS[ref][1])
    ours = [p for p in fp.Pads() if pad_type is None or
            (p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD) == (pad_type == "smd")]
    for rot in (0, 90, 180, 270):
        for anchor in ours:
            if anchor.GetNumber() not in pin1_names:
                continue
            fp.SetOrientationDegrees(rot)
            fp.SetPosition(V(0, 0))
            a = P(anchor.GetPosition())
            x, y = pin1["pos"][0] - a[0], pin1["pos"][1] - a[1]
            fp.SetPosition(V(x, y))
            pos = [P(p.GetPosition()) for p in ours]
            if len(pos) == len(dpads) and all(
                    any(abs(px - q["pos"][0]) < 0.03 and abs(py - q["pos"][1]) < 0.03 for q in dpads) for px, py in pos):
                return round(x, 4), round(y, 4), rot, anchor.GetNumber()
    raise SystemExit(f"{ref}: no orientation matches Dock {dock_ref}")


# ------------------------------------------------------------------ outline (Dock's)
def edge(shape):
    s = pcbnew.PCB_SHAPE(board)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(mm(0.1))
    if shape["type"] == "segment":
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(*shape["start"]))
        s.SetEnd(V(*shape["end"]))
    else:
        (cx, cy), r = shape["start"], shape["radius"]
        a0, a1 = math.radians(shape["startangle"]), math.radians(shape["endangle"])
        pt = lambda a: V(cx + r * math.cos(a), cy + r * math.sin(a))
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetArcGeometry(pt(a0), pt((a0 + a1) / 2), pt(a1))
    board.Add(s)


for e in DOCK["edges"]:
    edge(e)

# ------------------------------------------------------------------ placement
report = []
for ref, dref in (("J1", "J1"), ("J2", "J2")):
    x, y, rot, anc = match_dock(ref, dref)
    put(ref, x, y, rot); report.append(f"{ref}: Dock {dref} match at ({x}, {y}) rot {rot}")
for ref, dref in (("J3", "J3"), ("J4", "J4"), ("J5", "J5"), ("J6", "J6"), ("J7", "J7")):
    x, y, rot, anc = match_dock(ref, dref)
    note = ""
    if ref == "J7":      # Dock's JTAG courtyard overlaps its 40-pin; ours sits 0.5 mm lower (not a mating part)
        y, note = round(y + 0.5, 4), " then moved 0.5 mm down"
    put(ref, x, y, rot); report.append(f"{ref}: Dock {dref} match at ({x}, {y}) rot {rot}{note}")
# USB-C: the Dock uses a different USB-C part (no pad match), so place ours by its body:
# mouth (footprint +y) faces the right edge, shell front 0.3 mm past the edge (x = 164.27),
# centred 0.4 mm above the Dock's connector so its courtyard clears PMOD J4.
USB_FRONT = 3.65                     # F.Fab body front, footprint +y
x, y = round(164.27 + 0.3 - USB_FRONT, 3), 88.1
put("J10", x, y, 90); report.append(f"J10: USB-C at ({x}, {y}) rot 90, shell 0.3 mm past the right edge")
for ref, dref in (("H1", "J9"), ("H2", "J11"), ("H3", "J10"), ("H4", "J12")):
    cx, cy = DOCK["footprints"][dref]["center"]
    put(ref, cx, cy, 0); report.append(f"{ref}: Dock hole {dref} at ({cx}, {cy})")

# --- our own parts (Dock frame).  Left: config LEDs, buttons, UART/AUX.  Right: power.  Bottom gap: VCCIO beads.
OWN = {
    # LEDs at the Dock's LED positions (POWER / READY / DONE), series resistors left, pull-ups right
    "D2": (113.6, 75.6, 0), "D3": (113.6, 77.4, 0), "D4": (113.6, 79.2, 0),
    "R7": (110.6, 75.6, 0), "R4": (110.6, 77.4, 0), "R6": (110.6, 79.2, 0),
    "R9": (116.8, 75.6, 0), "R3": (116.8, 77.4, 0), "R5": (116.8, 79.2, 0), "C8": (119.4, 75.6, 0),
    "SW1": (104.6, 77.3, 0),                     # RECONFIG (Dock boot-button corner)
    "SW2": (104.6, 84.6, 0), "SW3": (104.6, 90.6, 0),
    "R10": (110.0, 83.0, 0), "C9": (110.0, 84.8, 0), "R11": (110.0, 89.0, 0), "C10": (110.0, 90.8, 0),
    "J8": (113.5, 82.6, 0), "J9": (118.0, 82.6, 0),
    # right: USB-C power path and bulk capacitors (Dock's debugger area)
    "F1": (153.6, 84.0, 90), "D1": (153.6, 89.2, 270), "R1": (151.0, 86.6, 90), "R2": (151.0, 89.2, 90),
    "C1": (148.0, 82.0, 0), "C2": (147.6, 84.6, 0), "C3": (147.6, 86.9, 0), "C4": (147.6, 89.2, 0),
    "R8": (156.5, 78.3, 0),                      # TCK pull-down next to J7
    # bottom gap between PMOD J5 and J4: VCCIO ferrite beads + caps
    "FB1": (141.6, 95.3, 90), "FB2": (143.5, 95.3, 90), "FB3": (145.4, 95.3, 90),
    "C5": (141.6, 98.6, 90), "C6": (143.5, 98.6, 90), "C7": (145.4, 98.6, 90),
}
for ref, (x, y, rot) in OWN.items():
    put(ref, x, y, rot)
# silkscreen tidy-up: designators of switches/headers go to Fab; the silk shows what the user needs:
# button function (Dock names), one label per header pin (pin 1 = top), LED meaning.
for ref in ("SW1", "SW2", "SW3", "J10", "J8", "J9"):
    PLACED[ref].Reference().SetLayer(pcbnew.F_Fab)


def silk(text, x, y, angle=0, size=0.8):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text); t.SetLayer(pcbnew.F_SilkS); t.SetPosition(V(x, y))
    t.SetTextSize(V(size, size)); t.SetTextThickness(mm(0.12)); t.SetTextAngleDegrees(angle)
    board.Add(t)


for ref, label in (("SW1", "RCFG"), ("SW2", "S1"), ("SW3", "S2")):    # inside the switch outline
    px, py = P(PLACED[ref].GetPosition())
    silk(label, px, py)
for ref, labels, lx in (("J8", ("G", "RX", "TX"), 115.75), ("J9", ("G", "B", "A", "3V3"), 120.3)):
    pads = sorted((P(p.GetPosition()) for p in PLACED[ref].Pads()), key=lambda q: q[1])
    for (px, py), lab in zip(pads, labels):
        silk(lab, lx, py, 270 if len(lab) > 1 else 0)
silk("UART", 113.5, 90.3)
silk("AUX", 118.0, 92.8)
silk("RDY", 119.2, 77.4)
silk("DONE", 119.3, 79.2)
missing = set(COMPS) - set(PLACED)
assert not missing, f"unplaced: {missing}"


# ------------------------------------------------------------------ fan-out
def fanout(ref):
    fp = PLACED[ref]
    cy = pcbnew.ToMM(fp.GetPosition().y)
    rows = {}
    for pad in fp.Pads():
        net = pad.GetNetname()
        if not net or net.startswith("unconnected-"):
            continue
        x, y = P(pad.GetPosition())
        rows.setdefault(y > cy, []).append((x, y, pad))
    n = 0
    for below, pads in rows.items():
        xmin = min(p[0] for p in pads)
        sgn = 1 if below else -1
        for x, y, pad in pads:
            half = pcbnew.ToMM(pad.GetSize(pcbnew.F_Cu).y if hasattr(pad, "GetSize") else pad.GetSize().y) / 2
            k = round((x - xmin) / 0.4)
            vy = y + sgn * (half + VIA_ROW_A + (VIA_ROW_STEP if k % 2 else 0))
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(V(x, y)); t.SetEnd(V(x, vy))
            t.SetWidth(mm(FAN_TRACK)); t.SetLayer(pcbnew.F_Cu); t.SetNet(pad.GetNet()); t.SetLocked(True)
            board.Add(t)
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(V(x, vy)); v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_DRILL)); v.SetNet(pad.GetNet()); v.SetLocked(True)
            board.Add(v)
            n += 1
    return n


fan_counts = {ref: fanout(ref) for ref in ("J1", "J2")}


# ------------------------------------------------------------------ GND stitch vias for SMD ground pads
# Every SMD pad on GND (outside the sockets/USB-C) gets its own via to the In1 plane, so no ground pad
# depends on the outer-layer pours (which routed traces can cut into islands). PLAN.md D16.
def stitch_gnd():
    vias = [(P(t.GetPosition()), VIA_D) for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    pads = [(p, fp) for fp in board.GetFootprints() for p in fp.Pads()]
    edge = board.GetBoardEdgesBoundingBox()
    ex0, ey0, ex1, ey1 = (pcbnew.ToMM(v) for v in (edge.GetLeft(), edge.GetTop(), edge.GetRight(), edge.GetBottom()))
    made, failed = 0, []
    for pad, fp in pads:
        if pad.GetNetname() != "GND" or fp.GetReference() in ("J1", "J2", "J10")                 or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
            continue
        px, py = P(pad.GetPosition())
        bb = pad.GetBoundingBox()
        hw, hh = pcbnew.ToMM(bb.GetWidth()) / 2, pcbnew.ToMM(bb.GetHeight()) / 2
        cx, cy = P(fp.GetPosition())
        dirs = sorted(((1, 0), (-1, 0), (0, 1), (0, -1)),
                      key=lambda d: -((px - cx) * d[0] + (py - cy) * d[1]))     # prefer away from the part
        for dx, dy in dirs:
            reach = (hw if dx else hh) + VIA_D / 2 + 0.15
            vx, vy = round(px + dx * reach, 3), round(py + dy * reach, 3)
            ok = ex0 + 0.6 < vx < ex1 - 0.6 and ey0 + 0.6 < vy < ey1 - 0.6
            for q, qfp in pads:
                if not ok:
                    break
                if q.GetNetname() == "GND" and qfp is fp and q.GetNumber() == pad.GetNumber():
                    continue
                qb = q.GetBoundingBox()
                qx0, qy0, qx1, qy1 = (pcbnew.ToMM(v) for v in (qb.GetLeft(), qb.GetTop(), qb.GetRight(), qb.GetBottom()))
                gap = 0.15 if q.GetNetname() != "GND" else 0.05
                if qx0 - gap - VIA_D / 2 < vx < qx1 + gap + VIA_D / 2 and qy0 - gap - VIA_D / 2 < vy < qy1 + gap + VIA_D / 2:
                    ok = False
                if q.GetDrillSize().x > 0:          # keep JLC hole-to-hole distance to plated holes
                    qx, qy = P(q.GetPosition())
                    if math.hypot(vx - qx, vy - qy) < pcbnew.ToMM(q.GetDrillSize().x) / 2 + VIA_DRILL / 2 + 0.55:
                        ok = False
            ok = ok and all(math.hypot(vx - a[0], vy - a[1]) >= 0.75 for a, _ in vias)
            if ok:
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(V(px, py)); t.SetEnd(V(vx, vy)); t.SetWidth(mm(0.3)); t.SetLayer(pcbnew.F_Cu)
                t.SetNet(pad.GetNet()); t.SetLocked(True); board.Add(t)
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(V(vx, vy)); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetWidth(mm(VIA_D))
                v.SetDrill(mm(VIA_DRILL)); v.SetNet(pad.GetNet()); v.SetLocked(True); board.Add(v)
                vias.append(((vx, vy), VIA_D))
                made += 1
                break
        else:
            failed.append(f"{fp.GetReference()}.{pad.GetNumber()}")
    return made, failed


stitch_made, stitch_failed = stitch_gnd()


# USB-C shell (4 x "SH", GND) tied to the connector's own GND pins on F.Cu, so the shell never
# depends on how the pours happen to fill around it (PLAN.md D19)
def tie_usb_shell():
    fp = PLACED["J10"]
    gnd = [p for p in fp.Pads() if p.GetNetname() == "GND" and p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD]
    n = 0
    for sh in [p for p in fp.Pads() if p.GetNumber() == "SH"]:
        a = sh.GetPosition()
        b = min(gnd, key=lambda q: (q.GetPosition() - a).EuclideanNorm()).GetPosition()
        if pcbnew.ToMM((b - a).EuclideanNorm()) > 2.0:   # front shell pads: a tie would cross CC and the
            continue                                     # NPTH pegs; the back ties are enough (D19)
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(a); t.SetEnd(b); t.SetWidth(mm(0.3)); t.SetLayer(pcbnew.F_Cu)
        t.SetNet(sh.GetNet()); t.SetLocked(True); board.Add(t)
        n += 1
    return n


shell_ties = tie_usb_shell()


# ------------------------------------------------------------------ rule areas + GND plane
def area(name, x0, y0, x1, y1, layers=None, rule=True, net=None, layer=None, priority=0):
    z = pcbnew.ZONE(board)
    if rule:
        z.SetIsRuleArea(True)
        for f in ("SetDoNotAllowTracks", "SetDoNotAllowVias", "SetDoNotAllowPads",
                  "SetDoNotAllowFootprints", "SetDoNotAllowZoneFills"):
            getattr(z, f)(False)
        z.SetLayerSet(pcbnew.LSET.AllCuMask())
        z.SetZoneName(name)
    else:
        z.SetLayer(layer)
        z.SetNet(NETS[net])
        z.SetAssignedPriority(priority)
        z.SetZoneName(name)
        z.SetMinThickness(mm(0.2))
        z.SetLocalClearance(mm(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    ol = z.Outline()
    ol.NewOutline()
    for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        ol.Append(mm(px), mm(py))
    board.Add(z)
    return z


# (no rule areas: kicad-cli ignores custom rules, and Freerouting treats rule areas as keep-outs)
bb = DOCK["edges_bbox"]
area("GND_In1", bb["minx"], bb["miny"], bb["maxx"], bb["maxy"], rule=False, net="GND", layer=pcbnew.In1_Cu)

# module body outline on User.Drawings (visual check: nothing but the sockets may sit under it)
r = pcbnew.PCB_SHAPE(board)
r.SetShape(pcbnew.SHAPE_T_RECT); r.SetLayer(pcbnew.Dwgs_User); r.SetWidth(mm(0.1))
r.SetStart(V(MODULE_RECT[0], MODULE_RECT[1])); r.SetEnd(V(MODULE_RECT[2], MODULE_RECT[3]))
board.Add(r)
txt = pcbnew.PCB_TEXT(board)
txt.SetText("TANG PRIMER 25K MODULE"); txt.SetLayer(pcbnew.Dwgs_User); txt.SetPosition(V(132.3, 84.2))
txt.SetTextSize(V(1.0, 1.0)); board.Add(txt)

# ------------------------------------------------------------------ placement self-checks
problems = []
for ref, fp in PLACED.items():
    if ref in ("J1", "J2"):
        continue
    bbx = fp.GetCourtyard(pcbnew.F_CrtYd).BBox() if fp.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else fp.GetBoundingBox()
    x0, y0, x1, y1 = (pcbnew.ToMM(v) for v in (bbx.GetLeft(), bbx.GetTop(), bbx.GetRight(), bbx.GetBottom()))
    mx0, my0, mx1, my1 = MODULE_RECT
    if x0 < mx1 - 0.15 and x1 > mx0 + 0.15 and y0 < my1 - 0.15 and y1 > my0 + 0.15:
        problems.append(f"{ref} courtyard under the module body")
pcbnew.SaveBoard(str(PCB), board)
print("\n".join(report))
print(f"fan-out: J1 {fan_counts['J1']} pads, J2 {fan_counts['J2']} pads -> stubs + vias")
print(f"GND stitch vias: {stitch_made} placed; no room for: {stitch_failed or 'none'}")
print("placement problems:", problems or "none")


# ------------------------------------------------------------------ design rules (JLCPCB 4-layer, with margin)
# JLCPCB published minimums (Nov 2026): 0.09 mm trace/space, 0.2 mm via drill, 0.45 mm via pad,
# 0.13 mm annular ring, 0.5 mm hole-to-hole (different nets). See PLAN.md D13.
pro_path = K / "carrier_v2.kicad_pro"
pro = json.loads(pro_path.read_text(encoding="utf-8"))
ds = pro["board"]["design_settings"]
ds["rules"].update({
    "min_clearance": 0.1, "min_track_width": 0.1, "min_copper_edge_clearance": 0.3,
    "min_hole_clearance": 0.2, "min_hole_to_hole": 0.5, "min_through_hole_diameter": 0.2,
    "min_via_diameter": 0.46, "min_via_annular_width": 0.13,
    "min_resolved_spokes": 1,      # a few GND pins (USB-C shell, header GND) only fit one thermal spoke
})
ds["track_widths"] = [0.0, 0.1, 0.15, 0.25, 0.4, 0.6]
ds["via_dimensions"] = [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.46, "drill": 0.2},
                        {"diameter": 0.6, "drill": 0.3}]
ns = pro["net_settings"]
default = next(c for c in ns["classes"] if c["name"] == "Default")
# 0.10 mm signal clearance (JLC min 0.09): kicad-cli 10.0.8 ignores .kicad_dru (tested), so the
# fan-out's 0.12 mm gaps must pass under the net-class rule. Routing uses 0.15 (set in the router).
# Signals: 0.12 mm track / 0.46-0.2 via. A trace leaving a row-A fan-out via must pass between two
# row-B vias 0.34 mm apart: 0.12 + 2 x 0.1 = 0.32 fits (PLAN.md D15). Power nets: 0.3 mm.
default.update({"clearance": 0.1, "track_width": 0.12, "via_diameter": 0.46, "via_drill": 0.2})
# Power (PLAN.md D18): +5V/VBUS 0.6 mm (~1.6 A on 1 oz outer copper, IPC-2221, 10 C rise), +3V3 0.4 mm.
# route_pcb.py restricts both classes to the outer (1 oz) layers. Local-label nets carry a leading "/".
# VCCIO stays in Default: bank supplies draw little and must escape between 0.4 mm-pitch fan-out vias.
p5 = dict(default, name="Power5V", clearance=0.1, track_width=0.6, via_diameter=0.6, via_drill=0.3, priority=0)
p33 = dict(default, name="Power3V3", clearance=0.1, track_width=0.4, via_diameter=0.6, via_drill=0.3, priority=1)
ns["classes"] = [default, p5, p33]
ns["netclass_patterns"] = [{"netclass": "Power5V", "pattern": "+5V"}, {"netclass": "Power5V", "pattern": "/VBUS"},
                           {"netclass": "Power3V3", "pattern": "+3V3"}]
pro_path.write_text(json.dumps(pro, indent=2) + "\n", encoding="utf-8")
dru = K / "carrier_v2.kicad_dru"
if dru.exists():
    dru.unlink()                                   # custom rules are not used (see note above)
print("design rules: min 0.1/0.1; Default 0.12/0.1 via 0.46/0.2; Power5V 0.6 mm; Power3V3 0.4 mm")

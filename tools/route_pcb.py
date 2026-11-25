"""Route kicad/carrier_v2.kicad_pcb with Freerouting and add copper pours (PLAN step 9).

Run with KiCad's Python after gen_pcb.py:
  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" route_pcb.py [passes]
Steps: export Specctra DSN -> freerouting-cli (headless) -> import SES -> GND pours on F.Cu/B.Cu,
+3V3 pour on In2.Cu (In1.Cu is the solid GND plane from gen_pcb.py) -> fill -> save.
The fan-out from gen_pcb.py is locked and exported as 'fixed', so the router keeps it.
Freerouting: D:\\Claude\\_tools\\freerouting\\freerouting-1.9.0.jar run on the installed Java 21.
(The v2.5.0 native CLI crashes on its first pass and then hangs; v2.2+ jars need Java 25.)
Every run has a hard time limit and fails loudly on a crash, so it can never hang silently.
"""
import os, subprocess, sys, time
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
K = HERE.parent / "kicad"
PCB = K / "carrier_v2.kicad_pcb"
WORK = K / "routing"
# set FREEROUTING_JAR to your freerouting-1.9.0.jar (github.com/freerouting/freerouting/releases/tag/v1.9.0)
FREEROUTING = Path(os.environ.get("FREEROUTING_JAR", r"D:\Claude\_tools\freerouting\freerouting-1.9.0.jar"))
TIMEOUT_S = 20 * 60
PASSES = int(sys.argv[1]) if len(sys.argv) > 1 else 100
mm = pcbnew.FromMM

WORK.mkdir(exist_ok=True)
dsn, ses, log = WORK / "carrier_v2.dsn", WORK / "carrier_v2.ses", WORK / "freerouting.log"

# Always start from a freshly generated, unrouted board. (After an SES import the fan-out is no
# longer marked locked, so 're-routing' a routed board would strip it.)
subprocess.run([sys.executable, str(HERE / "gen_pcb.py")], check=True, capture_output=True)
board = pcbnew.LoadBoard(str(PCB))
assert all(t.IsLocked() for t in board.GetTracks()), "expected only the locked fan-out before routing"
assert pcbnew.ExportSpecctraDSN(board, str(dsn)), "DSN export failed"
# keep router vias >= 0.7 mm apart centre-to-centre (JLC hole-to-hole 0.5 mm with 0.2 mm drills):
# Specctra via-to-via clearance class, 0.25 mm copper gap
d = dsn.read_text(encoding="utf-8")
d = d.replace("(clearance 25 (type smd_smd))", "(clearance 25 (type smd_smd))\n      (clearance 250 (type via_via))", 1)
assert "(type via_via)" in d, "could not add via_via clearance"
# power classes on the outer 1 oz layers only (inner layers are 0.5 oz at JLCPCB)
for cls in ("Power5V", "Power3V3"):
    i = d.index("(class " + cls)
    j = d.index("(circuit", i) + len("(circuit")
    d = d[:j] + "\n        (use_layer F.Cu B.Cu)" + d[j:]
assert d.count("(use_layer F.Cu B.Cu)") == 2, "power layer restriction not applied"
dsn.write_text(d, encoding="utf-8")

t0 = time.time()
with open(log, "w", encoding="utf-8") as lf:
    try:
        r = subprocess.run(["java", "-jar", str(FREEROUTING), "-de", str(dsn), "-do", str(ses), "-mp", str(PASSES)],
                           stdout=lf, stderr=subprocess.STDOUT, timeout=TIMEOUT_S)
        code = r.returncode
    except subprocess.TimeoutExpired:
        code = "TIMEOUT"
text = log.read_text(encoding="utf-8", errors="replace")
print(f"freerouting exit {code} in {time.time() - t0:.0f} s; log {log}")
if code == "TIMEOUT" or "Exception" in text:
    print("\n".join(text.splitlines()[-25:]))
    raise SystemExit("Freerouting failed (timeout or exception) - see log")
assert ses.exists(), "no session file produced"
assert pcbnew.ImportSpecctraSES(board, str(ses)), "SES import failed"


def P(v):
    return (round(pcbnew.ToMM(v.x), 3), round(pcbnew.ToMM(v.y), 3))


def add_track(net, a, b, width, layer=pcbnew.F_Cu):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(a); t.SetEnd(b); t.SetWidth(mm(width)); t.SetLayer(layer); t.SetNet(net); t.SetLocked(True)
    board.Add(t)


# 1. bridge neighbouring module pins of the same power net on F.Cu (5 V group, 3V3 group, VCCIO pairs).
#    Pads are 0.2 x 0.7 at 0.4 pitch; a 0.2 mm bridge between two same-net neighbours keeps 0.2 mm to others.
POWER = {"+5V", "+3V3", "VCCIO01", "VCCIO23", "VCCIO67"}
bridges = 0
for ref in ("J1", "J2"):
    fp = next(f for f in board.GetFootprints() if f.GetReference() == ref)
    rows = {}
    for pad in fp.Pads():
        if pad.GetNetname().lstrip("/") in POWER:
            rows.setdefault(P(pad.GetPosition())[1], []).append(pad)
    for pads in rows.values():
        pads.sort(key=lambda q: q.GetPosition().x)
        for a, b in zip(pads, pads[1:]):
            if a.GetNetname() == b.GetNetname() and abs(pcbnew.ToMM(b.GetPosition().x - a.GetPosition().x) - 0.4) < 0.01:
                add_track(a.GetNet(), a.GetPosition(), b.GetPosition(), 0.2)
                bridges += 1

# 2. drop zero-length scraps the router leaves at via centres
scraps = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and pcbnew.ToMM(t.GetLength()) < 0.001]
for t in scraps:
    board.Remove(t)

# (unused fan-out vias/stubs are removed afterwards by cleanup_dangling.py, driven by KiCad's DRC)
removed = 0
print(f"cleanup: {bridges} power-pin bridges, {len(scraps)} zero-length scraps removed")


def pour(name, net, layer, priority):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(board.FindNet(net))
    z.SetZoneName(name)
    z.SetAssignedPriority(priority)
    z.SetMinThickness(mm(0.2))
    z.SetLocalClearance(mm(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.25))
    z.SetThermalReliefSpokeWidth(mm(0.3))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    bb = board.GetBoardEdgesBoundingBox()
    ol = z.Outline()
    ol.NewOutline()
    for x, y in ((bb.GetLeft(), bb.GetTop()), (bb.GetRight(), bb.GetTop()),
                 (bb.GetRight(), bb.GetBottom()), (bb.GetLeft(), bb.GetBottom())):
        ol.Append(x, y)
    board.Add(z)


pour("GND_F", "GND", pcbnew.F_Cu, 1)
pour("GND_B", "GND", pcbnew.B_Cu, 1)
pour("3V3_In2", "+3V3", pcbnew.In2_Cu, 0)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(PCB), board)

tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
print(f"imported: {len(tracks)} track segments, {len(vias)} vias (incl. fan-out); "
      f"total length {sum(pcbnew.ToMM(t.GetLength()) for t in tracks):.0f} mm")

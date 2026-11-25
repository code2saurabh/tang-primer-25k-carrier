"""Fabrication outputs for JLCPCB (PLAN step 10).

Run with system Python after the board is routed and clean:   python make_fab.py
Writes ../fab/:
  gerbers/                         Gerbers (4 copper, mask, paste, silk, outline) + Excellon drill
  carrier_v2_jlcpcb_gerbers.zip    upload this to jlcpcb.com
  carrier_v2_jlcpcb_bom.csv        assembly BOM  (Comment, Designator, Footprint, LCSC Part #)
  carrier_v2_jlcpcb_cpl.csv        pick-and-place (Designator, Mid X, Mid Y, Layer, Rotation)
  carrier_v2_bom_mpn.csv           vendor-neutral BOM with manufacturer + MPN + polarity notes (PCB Power etc.)
  hand_solder.csv                  through-hole parts left out of assembly (2.54 mm headers etc.)
Gerber settings follow JLCPCB's KiCad guide: Protel extensions, no X2, no netlist attributes,
mask subtracted from silk, Excellon in mm with decimal format, PTH+NPTH in one file.
"""
import csv, subprocess, xml.etree.ElementTree as ET, zipfile
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
K = ROOT / "kicad"
PCB = K / "carrier_v2.kicad_pcb"
FAB = ROOT / "fab"
GER = FAB / "gerbers"
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"

# LCSC numbers checked on lcsc.com / jlcpcb.com (Nov 2026). The generic R/C lines are the parts JLCPCB's
# BOM tool matched on 24 Nov 2026 (checked value + package by hand), pinned so every order gets the same parts.
LCSC = {
    "J1": "C597938", "J2": "C597938",          # Hirose DF40C-60DS-0.4V(51)
    "J10": "C165948",                           # HRO TYPE-C-31-M-12
    "SW1": "C318884", "SW2": "C318884", "SW3": "C318884",   # XKB TS-1187A-B-A-B (Basic)
    "D1": "C169426",                            # SMF5.0A, SOD-123F (Jingdao)
    "F1": "C354895",                            # 1206 2 A 63 V fuse (Walter 1206T2A63V)
    "FB1": "C24821", "FB2": "C24821", "FB3": "C24821",      # Sunlord GZ1608D300TF
    "D2": "C12624", "D3": "C12624", "D4": "C12624",         # Kento KT-0603G green
    "C1": "C96123",                                         # Samsung 47 uF 10 V 1206
    "C2": "C45783", "C3": "C45783", "C4": "C45783",         # Samsung 22 uF 25 V 0805 (Basic)
    **{c: "C1525" for c in ("C5", "C6", "C7", "C8", "C9", "C10")},   # Samsung 100 nF 16 V 0402
    "R1": "C25905", "R2": "C25905", "R8": "C25905",         # UNI-ROYAL 5.1k 0402
    **{r: "C25897" for r in ("R3", "R4", "R5", "R6")},      # UNI-ROYAL 49.9k 0402
    "R7": "C25900", "R9": "C25744",                         # UNI-ROYAL 4.7k, 10k 0402
    "R10": "C25076", "R11": "C25076",                       # UNI-ROYAL 100R 0402
}
# LCSC number -> (manufacturer, MPN), for vendors that source parts themselves (PCB Power asked for MPNs)
MPN = {
    "C597938": ("Hirose", "DF40C-60DS-0.4V(51)"),
    "C165948": ("Korean Hroparts Elec", "TYPE-C-31-M-12"),
    "C318884": ("XKB Connection", "TS-1187A-B-A-B"),
    "C169426": ("Jingdao Microelectronics", "SMF5.0A"),
    "C354895": ("Walter Electronic", "1206T2A63V"),
    "C24821": ("Sunlord", "GZ1608D300TF"),
    "C12624": ("Hubei KENTO Elec", "KT-0603G"),
    "C96123": ("Samsung Electro-Mechanics", "CL31A476MPHNNNE"),
    "C45783": ("Samsung Electro-Mechanics", "CL21A226MAQNNNE"),
    "C1525": ("Samsung Electro-Mechanics", "CL05B104KO5NNNC"),
    "C25905": ("UNI-ROYAL", "0402WGF5101TCE"),
    "C25897": ("UNI-ROYAL", "0402WGF4992TCE"),
    "C25900": ("UNI-ROYAL", "0402WGF4701TCE"),
    "C25744": ("UNI-ROYAL", "0402WGF1002TCE"),
    "C25076": ("UNI-ROYAL", "0402WGF1000TCE"),
}
POLARITY = {"D1": "Unidirectional TVS: cathode band on pad 1 = VBUS side (silkscreen mark)",
            "D2": "LED: cathode on pad 1 = GND", "D3": "LED: cathode on pad 1 = GND", "D4": "LED: cathode on pad 1 = GND",
            "J1": "Pin 1 at silkscreen '1'", "J2": "Pin 1 at silkscreen '1'", "J10": "Mouth faces the board edge"}
HAND = {"J3", "J4", "J5", "J6", "J7", "J8", "J9"}      # 2.54 mm headers / PMOD sockets: hand-solder
MECH = {"H1", "H2", "H3", "H4"}                        # holes, nothing to place
PKG = {"R_0402_1005Metric": "0402", "C_0402_1005Metric": "0402", "C_0805_2012Metric": "0805",
       "C_1206_3216Metric": "1206", "LED_0603_1608Metric": "0603", "L_0603_1608Metric": "0603",
       "Fuse_1206_3216Metric": "1206", "D_SOD-123F": "SOD-123F", "SW_Push_1P1T_XKB_TS-1187A": "SMD-4P 5.1x5.1",
       "USB_C_Receptacle_HRO_TYPE-C-31-M-12": "USB-C-SMD_TYPE-C-31-M-12",
       "DF40C-60DS-0.4V_51_Sipeed": "SMD,P=0.4mm (DF40C-60DS)"}


def run(*args):
    r = subprocess.run([CLI, *args], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"kicad-cli {' '.join(args[:3])} failed:\n{r.stdout}\n{r.stderr}")
    return r.stdout


GER.mkdir(parents=True, exist_ok=True)
for old in GER.iterdir():
    old.unlink()
layers = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
run("pcb", "export", "gerbers", "--layers", layers, "--no-x2", "--no-netlist", "--subtract-soldermask",
    "--check-zones", "-o", str(GER) + "\\", str(PCB))
run("pcb", "export", "drill", "--format", "excellon", "--excellon-units", "mm", "--excellon-zeros-format",
    "decimal", "--excellon-oval-format", "route", "--generate-map", "--map-format", "gerberx2",
    "-o", str(GER) + "\\", str(PCB))
zpath = FAB / "carrier_v2_jlcpcb_gerbers.zip"
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(GER.iterdir()):
        z.write(f, f.name)

# ---- BOM from the verified netlist
xml = ET.parse(K / "carrier_v2.net.xml").getroot()
groups = defaultdict(list)
hand = []
for c in xml.iter("comp"):
    ref, val, fp = c.get("ref"), c.findtext("value"), c.findtext("footprint")
    if ref in MECH:
        continue
    if ref in HAND:
        hand.append((ref, val, fp))
        continue
    pkg = PKG.get(fp.split(":")[1], fp.split(":")[1])
    groups[(val, pkg, LCSC.get(ref, ""))].append(ref)


def natural(r):
    import re
    m = re.match(r"([A-Z]+)(\d+)", r)
    return (m.group(1), int(m.group(2)))


with open(FAB / "carrier_v2_jlcpcb_bom.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for (val, pkg, lcsc), refs in sorted(groups.items(), key=lambda kv: natural(sorted(kv[1], key=natural)[0])):
        w.writerow([val, ",".join(sorted(refs, key=natural)), pkg, lcsc])
with open(FAB / "carrier_v2_bom_mpn.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Item", "Designator", "Qty per board", "Value", "Package", "Manufacturer", "MPN", "LCSC Part #",
                "Polarity / orientation"])
    for i, ((val, pkg, lcsc), refs) in enumerate(sorted(groups.items(),
                                                       key=lambda kv: natural(sorted(kv[1], key=natural)[0])), 1):
        refs = sorted(refs, key=natural)
        man, mpn = MPN.get(lcsc, ("", ""))
        pol = "; ".join(sorted({POLARITY[r] for r in refs if r in POLARITY}))
        w.writerow([i, ",".join(refs), len(refs), val, pkg, man, mpn, lcsc, pol])
with open(FAB / "hand_solder.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Value", "Footprint", "Note"])
    for ref, val, fp in sorted(hand, key=lambda h: natural(h[0])):
        w.writerow([ref, val, fp, "through-hole, solder by hand (or add JLCPCB THT assembly)"])

# ---- CPL (placement) for the assembled parts
pos = FAB / "positions_kicad.csv"
run("pcb", "export", "pos", "--side", "front", "--format", "csv", "--units", "mm", "-o", str(pos), str(PCB))
assembled = {r for refs in groups.values() for r in refs}
rows = list(csv.DictReader(open(pos, encoding="utf-8")))
with open(FAB / "carrier_v2_jlcpcb_cpl.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for r in sorted(rows, key=lambda r: natural(r["Ref"])):
        if r["Ref"] in assembled:
            w.writerow([r["Ref"], f'{float(r["PosX"]):.4f}mm', f'{float(r["PosY"]):.4f}mm',
                        "Top" if r["Side"].lower() == "top" else "Bottom", f'{float(r["Rot"]):.0f}'])
pos.unlink()
missing = assembled - {r["Ref"] for r in rows}
print(f"gerbers: {len(list(GER.iterdir()))} files -> {zpath.name} ({zpath.stat().st_size // 1024} KB)")
print(f"BOM: {sum(len(v) for v in groups.values())} parts in {len(groups)} lines, "
      f"{sum(1 for k in groups if not k[2])} lines for JLCPCB auto-match; hand-solder: {len(hand)} parts")
print("CPL: all assembled parts placed" if not missing else f"CPL MISSING: {missing}")
nompn = [refs for (v, p, l), refs in groups.items() if l not in MPN]
print("MPN BOM: every line has an MPN" if not nompn else f"MPN BOM: NO MPN for {nompn}")

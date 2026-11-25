"""Make the project DF40 footprint from Sipeed's official carrier footprint, and use the
net names Sipeed left on its pads as a 4th independent check of pinout_v2.csv.

  python make_df40_footprint.py
  "C:\\Program Files\\KiCad\\10.0\\bin\\kicad-cli.exe" fp upgrade ..\\kicad\\carrier_v2.pretty   (done by this script)

Input : ../sources/sipeed_official/Tang_Primer_25K_Footprint.kicad_pcb (J1, J2 = BTB-DF40C-60DS-0.4V(51))
Output: ../kicad/carrier_v2.pretty/DF40C-60DS-0.4V_51_Sipeed.kicad_mod
Pad geometry is copied verbatim; only placement/net data is stripped and the 180 deg
instance rotation removed (pad angles 180 -> 0, positions are already footprint-local).
"""
import csv, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "sources" / "sipeed_official" / "Tang_Primer_25K_Footprint.kicad_pcb"
LIB = HERE.parent / "kicad" / "carrier_v2.pretty"
NAME = "DF40C-60DS-0.4V_51_Sipeed"
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"


def block(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError("unbalanced")


def footprints(text):
    out = {}
    for m in re.finditer(r'\(footprint "Connector_mine:BTB-DF40C-60DS-0\.4V\(51\)#"', text):
        b = block(text, m.start())
        ref = re.search(r'\(fp_text reference "([^"]+)"', b).group(1)
        out[ref] = b
    return out


def to_kicad_mod(b):
    b = re.sub(r'^\(footprint "[^"]+" \(layer "F.Cu"\)',
               f'(footprint "{NAME}" (version 20211014) (generator pcbnew) (layer "F.Cu")\n'
               '    (descr "Hirose DF40C-60DS-0.4V(51) receptacle, 1.5 mm stack height. Pads copied from '
               'Sipeed Tang Primer 25K carrier footprint: 0.20x0.70 mm, 0.4 mm pitch, rows 3.08 mm apart '
               '(matches Hirose catalog recommended layout).")\n'
               '    (tags "Hirose DF40 board-to-board 0.4mm Tang Primer 25K")', b)
    b = re.sub(r'\n\s*\(tedit [^)]*\) \(tstamp [^)]*\)', "", b)
    b = re.sub(r'\n\s*\(at [-\d.]+ [-\d.]+ 180\)', "", b, count=1)           # instance placement
    b = re.sub(r'\n\s*\(property "Sheet(file|name)" "[^"]*"\)', "", b)
    b = re.sub(r'\n\s*\(path "[^"]*"\)', "", b)
    b = re.sub(r'\s*\(tstamp [0-9a-f-]+\)', "", b)
    b = re.sub(r'\s*\(net \d+ "[^"]*"\)', "", b)
    b = re.sub(r'\s*\(pinfunction "[^"]*"\)', "", b)
    b = re.sub(r'\s*\(pintype "[^"]*"\)', "", b)
    b = re.sub(r'(\(at [-\d.]+ [-\d.]+) 180( unlocked)?\)', r'\1\2)', b)      # angles back to footprint frame
    b = b.replace('(fp_text reference "J1"', '(fp_text reference "REF**"')
    b = b.replace("(size 0.762 0.762)", "(size 0.8 0.8)")                     # JLC silk text >= 0.8 mm
    return b + "\n"


def pad_nets(b):
    return {m.group(1): m.group(2).lstrip("/") for m in
            re.finditer(r'\(pad "(\d+)" smd[^\n]*\n?\s*\(net \d+ "([^"]*)"\)', b)}


def main():
    text = SRC.read_text(encoding="utf-8")
    fps = footprints(text)
    LIB.mkdir(parents=True, exist_ok=True)
    out = LIB / f"{NAME}.kicad_mod"
    out.write_text(to_kicad_mod(fps["J1"]), encoding="utf-8")
    r = subprocess.run([CLI, "fp", "upgrade", str(LIB)], capture_output=True, text=True)
    print("kicad-cli fp upgrade:", r.returncode, (r.stdout + r.stderr).strip()[-300:])

    # ---- 4th check: Sipeed's own pad net names vs pinout_v2.csv
    pin = {(r["connector"], int(r["pin"])): r for r in csv.DictReader(open(HERE.parent / "pinout_v2.csv", encoding="utf-8"))}
    bad = 0
    checked = 0
    for ref, b in fps.items():
        for p, net in pad_nets(b).items():
            row = pin[(ref, int(p))]
            sig, ball = row["signal"], row["fpga_ball"]
            n = net.upper()
            ok = (ball and n.startswith(ball + "_")) or (sig == "GND" and n == "GND") \
                or ("VCC_5V" in n or "+5V" in n) and "5V0" in sig \
                or ("VCCIO" in n and "VCCIO" in sig) or ("VDD" in n and sig.startswith("VDD")) \
                or ("M0_" in n and sig.startswith("MIPI")) or (sig in n)
            checked += 1
            if not ok:
                bad += 1
                print(f"  MISMATCH {ref}.{p}: Sipeed net '{net}' vs pinout_v2 '{sig}' ball {ball}")
    print(f"Sipeed pad-net check: {checked} pads with nets, {bad} mismatches")


if __name__ == "__main__":
    main()

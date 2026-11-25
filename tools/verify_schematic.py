"""Independent verification of kicad/carrier_v2.kicad_sch.

1. Runs KiCad ERC (must be 0 violations) and exports the netlist with kicad-cli.
2. Netlist == generator intent (kicad/expected_nets.json): proves the drawing connects what was meant.
3. Independent of the generator's tables:
   a. J1/J2 pin nets vs pinout_v2.csv (official Sipeed pinout, 4-way checked)
   b. all 68 GPIOs reach exactly one module pin and at least one off-module pin
   c. Dock header signal sets vs the labels printed in the Dock schematic PDF
   d. circuit rules: pull-ups/downs, VCCIO feed, power pins, JTAG/UART/USB-C wiring
4. Every symbol pin has a pad of the same number in its footprint (and vice versa).
Run: python verify_schematic.py   -> exits 1 on any failure.
"""
import csv, json, re, subprocess, sys, xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
K = ROOT / "kicad"
SCH = K / "carrier_v2.kicad_sch"
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
FPDIR = Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
    return cond


# ---------------------------------------------------------------- 1. ERC + netlist
r = subprocess.run([CLI, "sch", "erc", "--severity-all", "--format", "json", "-o", str(K / "erc.json"), str(SCH)],
                   capture_output=True, text=True)
erc = json.loads((K / "erc.json").read_text(encoding="utf-8"))
viol = [v for s in erc["sheets"] for v in s["violations"]]
check(not viol, f"ERC: {len(viol)} violations, e.g. {[v['description'] for v in viol[:3]]}")
subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", str(K / "carrier_v2.net.xml"), str(SCH)],
               capture_output=True, text=True, check=True)
xml = ET.parse(K / "carrier_v2.net.xml").getroot()
net_nodes, pin_net = {}, {}
for n in xml.iter("net"):
    name = n.get("name").lstrip("/")
    nodes = {f'{x.get("ref")}.{x.get("pin")}' for x in n.iter("node")}
    if name.startswith("unconnected-"):
        for nd in nodes:
            pin_net[nd] = "NC"
        continue
    net_nodes[name] = nodes
    for nd in nodes:
        pin_net[nd] = name
comps = {c.get("ref"): c for c in xml.iter("comp")}
print(f"netlist: {len(comps)} components, {len(net_nodes)} nets, {len(pin_net)} pins")

# ---------------------------------------------------------------- 2. vs generator intent
exp = json.loads((K / "expected_nets.json").read_text(encoding="utf-8"))
for net, nodes in exp["nets"].items():
    check(net_nodes.get(net) == set(nodes),
          f"net {net}: netlist {sorted(net_nodes.get(net, []))} != intended {nodes}")
check(set(net_nodes) == set(exp["nets"]), f"extra/missing nets: {set(net_nodes) ^ set(exp['nets'])}")
for nd in exp["no_connect"]:
    check(pin_net.get(nd) == "NC", f"{nd} should be unconnected, is {pin_net.get(nd)}")

# ---------------------------------------------------------------- 3a. module pins vs official pinout
rows = list(csv.DictReader(open(ROOT / "pinout_v2.csv", encoding="utf-8")))
gpio = set()
for row in rows:
    nd, s = f'{row["connector"]}.{row["pin"]}', row["signal"]
    got = pin_net.get(nd)
    if s == "GND":
        want = "GND"
    elif "5V0" in s:
        want = "+5V"
    elif "3V3 Output" in s:
        want = "+3V3"
    elif s.startswith(("VDD_1V8", "VDD_2V5", "MIPI")):
        want = "NC"
    elif s.startswith("VCCIO"):
        want = "VCCIO" + re.sub(r"\D", "", s.split()[0])
    elif s == "RECONFIG":
        want = "RECONFIG_N"
    else:
        want = s
        if row["fpga_ball"] and s.startswith("IO"):
            gpio.add(s)
    check(got == want, f"{nd} ({s}): net {got}, expected {want}")
check(len(gpio) == 68, f"{len(gpio)} GPIOs in pinout, expected 68")

# ---------------------------------------------------------------- 3b. every GPIO broken out
offboard = {}
for g in sorted(gpio):
    nodes = net_nodes.get(g, set())
    mod = [n for n in nodes if n.split(".")[0] in ("J1", "J2")]
    other = [n for n in nodes if n.split(".")[0] not in ("J1", "J2")]
    check(len(mod) == 1 and other, f"GPIO {g}: module pins {mod}, other {other}")
    offboard[g] = other

# ---------------------------------------------------------------- 3c. Dock headers vs Dock PDF labels
words = pymupdf.open(ROOT / "sources" / "Tang_Primer_25K_Dock_60033_Schematic.pdf")[0].get_text("words")
dock40 = {m.group(1) for w in words if (m := re.fullmatch(r"[A-L]\d{1,2}_(IO\w+?)_40P", w[4]))}
dockpmod = {m.group(1) for w in words if w[0] > 680 and w[1] < 235
            and (m := re.fullmatch(r"[A-L]\d{1,2}_(IO[TBLR]\d+[AB])", w[4]))}
on = lambda ref: {pin_net[n] for n in pin_net if n.split(".")[0] == ref and pin_net[n].startswith("IO")}
check(on("J3") == dock40, f"J3 signals != Dock 40-pin labels: {on('J3') ^ dock40}")
check(on("J4") | on("J5") | on("J6") == dockpmod, f"PMOD signals != Dock PMOD labels: {(on('J4')|on('J5')|on('J6')) ^ dockpmod}")
for ref in ("J3", "J4", "J5", "J6"):     # differential pairs must sit side by side (odd/even of one row)
    pins = {int(n.split(".")[1]): pin_net[n] for n in pin_net if n.split(".")[0] == ref}
    for p, s in pins.items():
        if s.startswith("IO") and s.endswith("A"):
            mate = s[:-1] + "B"
            if mate in pins.values():
                q = next(k for k, v in pins.items() if v == mate)
                check((p - 1) // 2 == (q - 1) // 2, f"{ref}: pair {s}/{mate} on pins {p}/{q} not in one row")
print(f"Dock header check: J3 {len(on('J3'))} signals, PMODs {len(on('J4') | on('J5') | on('J6'))} signals")


# ---------------------------------------------------------------- 3d. circuit rules
def both(ref, a, b):
    return {pin_net.get(f"{ref}.1"), pin_net.get(f"{ref}.2")} == {a, b}


def value(ref):
    return comps[ref].findtext("value")


check(both("R3", "+3V3", "READY") and value("R3") == "49.9k", "READY needs 49.9k pull-up (D9)")
check(both("R5", "+3V3", "DONE") and value("R5") == "49.9k", "DONE needs 49.9k pull-up (D9)")
check(both("R9", "+3V3", "RECONFIG_N"), "RECONFIG_N needs pull-up to 3V3 (UG714)")
check(both("SW1", "RECONFIG_N", "GND"), "RECONFIG button must go to GND (UG714)")
check(both("R8", "JTAG_TCK", "GND") and value("R8") == "5.1k", "TCK needs 5.1k pull-down (spec p5, Dock)")
for net in ("READY", "RECONFIG_N"):                 # nothing may pull these straight to GND
    for nd in net_nodes[net]:
        ref = nd.split(".")[0]
        if ref.startswith("R"):
            check(pin_net.get(f"{ref}.1") != "GND" and pin_net.get(f"{ref}.2") != "GND", f"{net} pulled down by {ref}")
for v in ("VCCIO01", "VCCIO23", "VCCIO67"):
    refs = {n.split(".")[0] for n in net_nodes[v]}
    check({"J1", "J2"} & refs and any(r.startswith("FB") for r in refs), f"{v} must connect module pins and a bead")
for fb in ("FB1", "FB2", "FB3"):
    check(pin_net.get(f"{fb}.1") == "+3V3", f"{fb} must be fed from +3V3 (module VDD_3V3)")
check({"J2.46", "J2.48", "J2.50"} <= net_nodes["+3V3"], "module VDD_3V3 pins must be the +3V3 source")
check({f"J2.{p}" for p in (52, 54, 56, 58, 60)} <= net_nodes["+5V"], "module VCC_5V pins on +5V")
check(both("F1", "VBUS", "+5V"), "fuse between VBUS and +5V")
check({"J10.A4", "J10.A9", "J10.B4", "J10.B9"} <= net_nodes["VBUS"], "USB-C VBUS pins")
check(both("R1", "CC1", "GND") and both("R2", "CC2", "GND") and value("R1") == "5.1k", "USB-C 5.1k CC pull-downs")
# polarity: diode footprints have pad 1 = cathode. Unidirectional TVS cathode on VBUS, LED cathodes on GND (D21)
check(pin_net.get("D1.1") == "VBUS" and pin_net.get("D1.2") == "GND", "TVS D1: cathode (1) must be VBUS, anode (2) GND")
check(comps["D1"].find("libsource").get("part") != "D_TVS", "D1 must not use the bidirectional D_TVS symbol")
for led in ("D2", "D3", "D4"):
    check(pin_net.get(f"{led}.1") == "GND", f"{led}: LED cathode (1) must be on GND")
jt = {p: pin_net.get(f"J7.{p}") for p in range(1, 9)}
check(jt == {1: "JTAG_TMS", 2: "JTAG_TDI", 3: "JTAG_TCK", 4: "NC", 5: "JTAG_TDO", 6: "GND", 7: "+3V3", 8: "NC"},
      f"J7 must match Dock J7 with 4/8 open: {jt}")
check([pin_net.get(f"J8.{p}") for p in (1, 2, 3)] == ["GND", "IOB56A", "IOB56B"], "UART J8 = GND, RX(IOB56A), TX(IOB56B)")
check("+5V" not in {pin_net.get(f"J8.{p}") for p in (1, 2, 3)} and "+3V3" not in {pin_net.get(f"J8.{p}") for p in (1, 2, 3)},
      "UART header must not carry power (D7)")
for pin in ("IOT3A", "IOT3B"):
    check(any(nd.startswith("SW") for nd in net_nodes[pin]), f"{pin} button missing (D5)")

# ---------------------------------------------------------------- 4. symbol pins vs footprint pads
def fp_pads(fpid):
    lib, name = fpid.split(":")
    p = (K / "carrier_v2.pretty" / f"{name}.kicad_mod") if lib == "carrier_v2" else FPDIR / f"{lib}.pretty" / f"{name}.kicad_mod"
    if not p.exists():
        return None
    t = p.read_text(encoding="utf-8")
    return {m.group(1) for m in re.finditer(r'\(pad "([^"]*)" (smd|thru_hole|connect)', t) if m.group(1)}


libpins = defaultdict(set)
for lp in xml.iter("libpart"):
    for p in lp.iter("pin"):
        libpins[(lp.get("lib"), lp.get("part"))].add(p.get("num"))
for ref, c in sorted(comps.items()):
    fpid = c.findtext("footprint") or ""
    ls = c.find("libsource")
    pins = libpins[(ls.get("lib"), ls.get("part"))]
    pads = fp_pads(fpid) if fpid else None
    if not check(pads is not None, f"{ref}: footprint '{fpid}' not found"):
        continue
    check(pins <= pads, f"{ref} ({fpid}): symbol pins without pads: {sorted(pins - pads)}")
    check(pads <= pins, f"{ref} ({fpid}): pads without symbol pins: {sorted(pads - pins)}")

# ---------------------------------------------------------------- report
print(f"GPIO breakout: {len(offboard)} of 68 reach a header/button/UART")
if fails:
    print(f"\nFAILED: {len(fails)} problem(s)")
    for m in fails:
        print("  -", m)
    sys.exit(1)
print("\nALL CHECKS PASSED (ERC clean, netlist = intent, pinout = official, headers = Dock, pads = pins)")

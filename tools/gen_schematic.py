"""Generate the Tang Primer 25K carrier v2 schematic (KiCad 10) from verified sources.

Inputs
  ../pinout_v2.csv                                  module connector J1/J2, pin -> signal (4-way checked)
  ../sources/Tang_Primer_25K_Dock_60033_Schematic.pdf  Dock header pinouts (J3 40-pin, PMOD J4/J5/J6),
                                                       read from the PDF text so nothing is hand-typed
  KiCad 10 standard symbol libraries                 symbols are embedded verbatim
Outputs (../kicad/)
  carrier_v2.kicad_sch, carrier_v2.kicad_pro, fp-lib-table, expected_nets.json (for verify_schematic.py)

Style: every connected pin gets a 2.54 mm wire stub ending in a net label or power symbol;
unused pins get a no-connect flag. Design decisions D4-D11 are in ../PLAN.md.

Run: python gen_schematic.py   (system Python with pymupdf), then verify_schematic.py
"""
import csv, json, math, re, uuid
from collections import defaultdict
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "kicad"
SYMDIR = Path(r"C:\Program Files\KiCad\10.0\share\kicad\symbols")
PROJECT = "carrier_v2"
NS = uuid.UUID("6f1c7a52-25c0-4b7e-9a3e-25c0ca7741e2")
ROOT_UUID = str(uuid.uuid5(NS, "root"))
POWER_NETS = {"GND": "power:GND", "+5V": "power:+5V", "+3V3": "power:+3V3"}
STUB = 2.54


def U(*key):
    return str(uuid.uuid5(NS, "/".join(map(str, key))))


def f(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ------------------------------------------------------------------ s-expressions
def sexpr_block(text, start):
    depth = 0
    in_str = False
    i = start
    while i < len(text):
        c = text[i]
        if in_str:
            if c == "\\":
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    raise ValueError("unbalanced s-expression")


def parse(s):
    toks = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', s)
    stack, cur = [], []
    for t in toks:
        if t == "(":
            stack.append(cur); cur = []
        elif t == ")":
            done = cur; cur = stack.pop(); cur.append(done)
        else:
            cur.append(t[1:-1] if t.startswith('"') else t)
    return cur[0]


# ------------------------------------------------------------------ library symbols
_libtext, _symcache = {}, {}


def lib_symbol(lib_id):
    """Return (embedded text, pins[{num,name,type,x,y,angle}]) for e.g. 'Device:R'."""
    if lib_id in _symcache:
        return _symcache[lib_id]
    lib, name = lib_id.split(":")
    if lib not in _libtext:
        _libtext[lib] = (SYMDIR / f"{lib}.kicad_sym").read_text(encoding="utf-8")
    t = _libtext[lib]
    m = re.search(r'\n\t\(symbol "%s"' % re.escape(name), t)
    if not m:
        raise KeyError(lib_id)
    blk = sexpr_block(t, m.start() + 2)
    if "(extends" in blk[:400]:
        raise ValueError(f"{lib_id} uses extends; flatten it first")
    tree = parse(blk)
    pins = []
    for sub in tree:
        if isinstance(sub, list) and sub and sub[0] == "symbol":
            mm = re.fullmatch(re.escape(name) + r"_(\d+)_(\d+)", sub[1])
            if not mm or int(mm.group(1)) > 1 or int(mm.group(2)) > 1:
                continue
            for p in sub:
                if isinstance(p, list) and p and p[0] == "pin":
                    at = next(x for x in p if isinstance(x, list) and x[0] == "at")
                    nm = next(x for x in p if isinstance(x, list) and x[0] == "name")
                    nu = next(x for x in p if isinstance(x, list) and x[0] == "number")
                    pins.append(dict(type=p[1], x=float(at[1]), y=float(at[2]), angle=float(at[3]),
                                     name=nm[1], num=nu[1]))
    text = '(symbol "%s:%s"' % (lib, name) + blk[len('(symbol "%s"' % name):]
    _symcache[lib_id] = (text, pins)
    return _symcache[lib_id]


# ------------------------------------------------------------------ schematic model
items = []          # schematic s-expression strings (after lib_symbols)
used_libs = []
expected = defaultdict(set)     # net -> {"REF.PIN"}
nc_expected = set()
ref_seen = set()
pwr_counter = [0]


def _use(lib_id):
    if lib_id not in used_libs:
        used_libs.append(lib_id)


def wire(x1, y1, x2, y2):
    items.append(f'\t(wire (pts (xy {f(x1)} {f(y1)}) (xy {f(x2)} {f(y2)}))\n\t\t(stroke (width 0) (type default))\n'
                 f'\t\t(uuid "{U("w", x1, y1, x2, y2)}")\n\t)')


def label(name, x, y, ang):
    just = "left bottom" if ang in (0, 90) else "right bottom"
    items.append(f'\t(label "{name}" (at {f(x)} {f(y)} {ang}) (fields_autoplaced yes)\n'
                 f'\t\t(effects (font (size 1.27 1.27)) (justify {just}))\n\t\t(uuid "{U("l", name, x, y)}")\n\t)')


def text(s, x, y, size=2.54, bold=True):
    b = " (bold yes)" if bold else ""
    s = s.replace('"', '\\"')
    items.append(f'\t(text "{s}" (exclude_from_sim no) (at {f(x)} {f(y)} 0)\n'
                 f'\t\t(effects (font (size {size} {size}){b}) (justify left bottom))\n\t\t(uuid "{U("t", s, x, y)}")\n\t)')


def no_connect(x, y):
    items.append(f'\t(no_connect (at {f(x)} {f(y)}) (uuid "{U("nc", x, y)}"))')


def symbol(lib_id, ref, value, x, y, rot=0, footprint="", props=None, in_bom=True, hide_ref=False,
           fields_xy=None, value_angle=0):
    _use(lib_id)
    _, pins = lib_symbol(lib_id)
    pin_uuids = "".join(f'\t\t(pin "{p["num"]}" (uuid "{U("p", ref, p["num"])}"))\n'
                        for p in {p["num"]: p for p in pins}.values())
    if fields_xy is None:
        fields_xy = ((x + 2.54, y - 1.27, "left"), (x + 2.54, y + 1.27, "left"))
    (rx, ry, rj), (vx, vy, vj) = fields_xy
    hide = " (hide yes)" if hide_ref else ""
    rj = "" if rj == "center" else f" (justify {rj})"       # KiCad has no 'center' keyword (default)
    vj = "" if vj == "center" else f" (justify {vj})"
    extra = ""
    for k, v in (props or {}).items():
        extra += (f'\t\t(property "{k}" "{v}" (at {f(x)} {f(y)} 0)\n'
                  f'\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)\n')
    items.append(
        f'\t(symbol (lib_id "{lib_id}") (at {f(x)} {f(y)} {rot}) (unit 1)\n'
        f'\t\t(exclude_from_sim no) (in_bom {"yes" if in_bom else "no"}) (on_board yes) (dnp no)\n'
        f'\t\t(uuid "{U("s", ref)}")\n'
        f'\t\t(property "Reference" "{ref}" (at {f(rx)} {f(ry)} 0)\n\t\t\t(effects (font (size 1.27 1.27)){rj}{hide})\n\t\t)\n'
        f'\t\t(property "Value" "{value}" (at {f(vx)} {f(vy)} {value_angle})\n\t\t\t(effects (font (size 1.27 1.27)){vj})\n\t\t)\n'
        f'\t\t(property "Footprint" "{footprint}" (at {f(x)} {f(y)} 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)\n'
        f'\t\t(property "Datasheet" "" (at {f(x)} {f(y)} 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)\n'
        f'\t\t(property "Description" "" (at {f(x)} {f(y)} 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)\n'
        f'{extra}{pin_uuids}'
        f'\t\t(instances (project "{PROJECT}" (path "/{ROOT_UUID}" (reference "{ref}") (unit 1))))\n\t)')
    return pins


def power_symbol(net, x, y, direction):
    """Power symbol at (x,y) with its body pointing in `direction` (screen dx,dy)."""
    lib_id = POWER_NETS[net]
    pwr_counter[0] += 1
    ref = f"#PWR{pwr_counter[0]:03d}"
    # GND body points down at rot 0; +5V/+3V3 bodies point up at rot 0. KiCad rot is CCW on screen.
    body0 = (0, 1) if net == "GND" else (0, -1)
    rot = 0
    for r in (0, 90, 180, 270):
        c, s = round(math.cos(math.radians(r))), round(math.sin(math.radians(r)))
        # CCW on screen (y down): (x, y) -> (x*c + y*s, -x*s + y*c)
        v = (body0[0] * c + body0[1] * s, -body0[0] * s + body0[1] * c)
        if v == direction:
            rot = r
            break
    if direction[1] == 0:       # sideways symbol: keep its name horizontal so it can't hit the next pin's label
        # field angles are relative to the symbol, so counter-rotate
        symbol(lib_id, ref, net, x, y, rot, in_bom=False, hide_ref=True,
               fields_xy=((x, y, "center"), (x + direction[0] * 5.6, y, "center")), value_angle=(360 - rot) % 360)
    else:
        symbol(lib_id, ref, net, x, y, rot, in_bom=False, hide_ref=True,
               fields_xy=((x, y, "center"), (x, y + direction[1] * 3.8, "center")))
    return ref


def place(lib_id, ref, value, x, y, nets, footprint, props=None, fields_xy=None, in_bom=True):
    """Place a symbol (rotation 0) and attach every pin: net name, 'NC', or error if missing."""
    assert ref not in ref_seen, ref
    ref_seen.add(ref)
    _, pins = lib_symbol(lib_id)
    nums = {p["num"] for p in pins}
    missing = nums - set(nets)
    extra = set(nets) - nums
    assert not missing and not extra, f"{ref}: missing {sorted(missing)} extra {sorted(extra)}"
    if fields_xy is None:
        sx = [x + p["x"] for p in pins]
        sy = [y - p["y"] for p in pins]
        down = any(round(p["angle"]) == 90 for p in pins)    # pins leaving the bottom of the body
        if len(set(round(v, 3) for v in sx)) == 1:          # vertical two-pin part
            fields_xy = ((x + 2.54, y - 1.27, "left"), (x + 2.54, y + 1.27, "left"))
        elif down:                                          # keep both fields above the body
            fields_xy = ((x, min(sy) - 7.0, "center"), (x, min(sy) - 4.0, "center"))
        else:
            fields_xy = ((x, min(sy) - 4.0, "center"), (x, max(sy) + 4.0, "center"))
    symbol(lib_id, ref, value, x, y, 0, footprint, props, in_bom=in_bom, fields_xy=fields_xy)
    # group pins by connection point (stacked pins share one stub)
    by_pt = defaultdict(list)
    for p in pins:
        by_pt[(round(x + p["x"], 4), round(y - p["y"], 4))].append(p)
    for (px, py), group in by_pt.items():
        netset = {nets[p["num"]] for p in group}
        assert len(netset) == 1, f"{ref}: stacked pins {[p['num'] for p in group]} on different nets {netset}"
        net = netset.pop()
        if net == "NC":
            for p in group:
                nc_expected.add(f"{ref}.{p['num']}")
            no_connect(px, py)
            continue
        for p in group:
            expected[net].add(f"{ref}.{p['num']}")
        a = math.radians(group[0]["angle"] + 180)          # away from the body, library coords (y up)
        d = (round(math.cos(a)), -round(math.sin(a)))       # screen direction
        qx, qy = px + d[0] * STUB, py + d[1] * STUB
        wire(px, py, qx, qy)
        if net in POWER_NETS:
            power_symbol(net, qx, qy, d)
        else:
            ang = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[d]
            label(net, qx, qy, ang)


def pwr_flag(net, x, y):
    """PWR_FLAG at (x,y), wire down, then the net's power symbol or label."""
    pwr_counter[0] += 1
    ref = f"#FLG{pwr_counter[0]:03d}"
    symbol("power:PWR_FLAG", ref, "PWR_FLAG", x, y, 0, in_bom=False, hide_ref=True,
           fields_xy=((x, y - 3.5, "center"), (x, y - 3.5, "center")))
    wire(x, y, x, y + STUB)
    if net in POWER_NETS:
        power_symbol(net, x, y + STUB, (0, 1))
    else:
        label(net, x, y + STUB, 270)


# ------------------------------------------------------------------ net data
def module_nets():
    """J1/J2 pin -> net from pinout_v2.csv (D1)."""
    rows = list(csv.DictReader(open(ROOT / "pinout_v2.csv", encoding="utf-8")))
    m = {"J1": {}, "J2": {}}
    for r in rows:
        s = r["signal"]
        if s == "GND":
            n = "GND"
        elif s.startswith("VDD_5V0"):
            n = "+5V"
        elif s.startswith("VDD_3V3"):
            n = "+3V3"                      # module 3V3 OUTPUT feeds the carrier (D8)
        elif s.startswith(("VDD_1V8", "VDD_2V5", "MIPI")):
            n = "NC"
        elif s.startswith("VCCIO"):
            n = {"VCCIO0/1": "VCCIO01", "VCCIO2/3": "VCCIO23", "VCCIO6/7": "VCCIO67"}[s.split()[0]]
        elif s == "RECONFIG":
            n = "RECONFIG_N"
        else:
            n = s                           # GPIO, READY, DONE, JTAG_*
        m[r["connector"]][r["pin"]] = n
    return m, {r["signal"]: r["fpga_ball"] for r in rows if r["fpga_ball"]}


def dock_headers(balls):
    """Read Dock J3 (2x20) and PMOD J4/J5/J6 (2x6) signal pins from the Dock PDF (D4)."""
    words = pymupdf.open(ROOT / "sources" / "Tang_Primer_25K_Dock_60033_Schematic.pdf")[0].get_text("words")
    nums = [w for w in words if re.fullmatch(r"\d{1,2}", w[4]) and 590 < w[0] < 760 and 70 < w[1] < 235]
    hdr = {"J3": {}, "J4": {}, "J5": {}, "J6": {}}
    for w in words:
        m = re.fullmatch(r"([A-L]\d{1,2})_(IO[TBLR]\d+[AB])(?:_40P)?", w[4])
        if not m or not (550 < w[0] < 800 and 70 < w[1] < 235):
            continue
        ball, sig = m.groups()
        assert balls.get(sig) == ball, f"Dock label {w[4]}: ball {ball} != pinout_v2 {balls.get(sig)}"
        yc = (w[1] + w[3]) / 2
        same = [n for n in nums if abs((n[1] + n[3]) / 2 - yc) < 1.6]
        if w[0] < 600:                                   # J3 left column -> odd pin to its right
            conn, cand = "J3", [n for n in same if 595 < n[0] < 620]
        elif w[0] < 660:                                 # J3 right column -> even pin to its left
            conn, cand = "J3", [n for n in same if 620 < n[0] < 640]
        else:                                            # PMODs: left label->even pin, right label->odd pin
            conn = "J4" if yc < 110 else ("J5" if yc < 175 else "J6")
            cand = [n for n in same if (720 < n[0] < 732)] if w[0] < 720 else [n for n in same if 745 < n[0] < 756]
        assert len({c[4] for c in cand}) == 1, f"pin for {w[4]}: {[c[4] for c in cand]}"
        hdr[conn][cand[0][4]] = sig
    # power pins (drawn as symbols in the Dock PDF; checked visually, see PLAN.md D4)
    hdr["J3"].update({"11": "+5V", "12": "GND"})
    for c in ("J4", "J5", "J6"):
        hdr[c].update({"1": "+3V3", "2": "+3V3", "3": "GND", "4": "GND"})
    assert sorted(map(int, hdr["J3"])) == list(range(1, 41)), sorted(map(int, hdr["J3"]))
    for c in ("J4", "J5", "J6"):
        assert sorted(map(int, hdr[c])) == list(range(1, 13)), (c, sorted(map(int, hdr[c])))
    return hdr


# ------------------------------------------------------------------ build
def build():
    mod, balls = module_nets()
    hdr = dock_headers(balls)

    FP_DF40 = "carrier_v2:DF40C-60DS-0.4V_51_Sipeed"
    R0402 = "Resistor_SMD:R_0402_1005Metric"
    C0402 = "Capacitor_SMD:C_0402_1005Metric"
    C0805 = "Capacitor_SMD:C_0805_2012Metric"
    C1206 = "Capacitor_SMD:C_1206_3216Metric"
    LED = "LED_SMD:LED_0603_1608Metric"
    BTN = "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A"

    text("Tang Primer 25K carrier v2 - generated by tools/gen_schematic.py (do not hand-edit; change the script)", 15.24, 22.86, 2.0)
    text("MODULE (DF40C-60DS-0.4V(51) x2, Sipeed footprint)  J1/J2 pin map = pinout_v2.csv", 15.24, 33.02)
    place("Connector_Generic:Conn_02x30_Odd_Even", "J1", "DF40C-60DS-0.4V(51)", 50.8, 116.84, mod["J1"], FP_DF40,
          {"MPN": "Hirose DF40C-60DS-0.4V(51)"})
    place("Connector_Generic:Conn_02x30_Odd_Even", "J2", "DF40C-60DS-0.4V(51)", 147.32, 116.84, mod["J2"], FP_DF40,
          {"MPN": "Hirose DF40C-60DS-0.4V(51)"})

    text("HEADERS - pin-compatible with Sipeed 25K Dock J3 / J4 / J5 / J6", 223.52, 33.02)
    place("Connector_Generic:Conn_02x20_Odd_Even", "J3", "Dock 40-pin (2x20)", 256.54, 101.6, hdr["J3"],
          "Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical")
    for ref, y in (("J4", 63.5), ("J5", 101.6), ("J6", 139.7)):
        place("Connector_Generic:Conn_02x06_Odd_Even", ref, f"PMOD {ref} (Dock {ref})", 345.44, y, hdr[ref],
              "Connector_PinSocket_2.54mm:PinSocket_2x06_P2.54mm_Horizontal")

    text("JTAG (Dock J7 pinout; 4=+5V and 8=BL616_EN left open)  /  UART  /  AUX", 391.16, 33.02)
    place("Connector_Generic:Conn_02x04_Odd_Even", "J7", "JTAG", 414.02, 60.96,
          {"1": "JTAG_TMS", "2": "JTAG_TDI", "3": "JTAG_TCK", "4": "NC", "5": "JTAG_TDO", "6": "GND",
           "7": "+3V3", "8": "NC"}, "Connector_PinHeader_2.54mm:PinHeader_2x04_P2.54mm_Vertical")
    place("Connector_Generic:Conn_01x03", "J8", "UART (GND, FPGA_RX, FPGA_TX)", 414.02, 91.44,
          {"1": "GND", "2": "IOB56A", "3": "IOB56B"}, "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical")
    place("Connector_Generic:Conn_01x04", "J9", "AUX (Dock USB-host pins)", 414.02, 119.38,
          {"1": "GND", "2": "IOT23B", "3": "IOT23A", "4": "+3V3"},
          "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical")

    # ---- power input (D8)
    text("POWER - USB-C 5 V in; module makes 3V3; beads feed VCCIO (as on the Dock)", 15.24, 190.5)
    usb = {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "SH": "GND",
           "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
           "A5": "CC1", "B5": "CC2", "A6": "NC", "B6": "NC", "A7": "NC", "B7": "NC", "A8": "NC", "B8": "NC"}
    place("Connector:USB_C_Receptacle_USB2.0_16P", "J10", "USB-C (power only)", 45.72, 236.22, usb,
          "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", {"MPN": "HRO TYPE-C-31-M-12"})
    place("Device:Fuse", "F1", "2A fast", 99.06, 223.52, {"1": "VBUS", "2": "+5V"},
          "Fuse:Fuse_1206_3216Metric", {"MPN": "1206 2A fast-acting (e.g. Littelfuse 0466002)"})
    # SMF5.0A is UNIdirectional: cathode (pin/pad 1, band) to VBUS, anode to GND. Device:D_TVS is the
    # bidirectional symbol (A1/A2) and hid this; D_Zener has K=1/A=2 like the SOD-123F footprint (D21).
    place("Device:D_Zener", "D1", "SMF5.0A", 99.06, 246.38, {"1": "VBUS", "2": "GND"}, "Diode_SMD:D_SOD-123F",
          {"MPN": "SMF5.0A (5 V unidirectional TVS)"})
    place("Device:R", "R1", "5.1k", 119.38, 236.22, {"1": "CC1", "2": "GND"}, R0402)
    place("Device:R", "R2", "5.1k", 129.54, 236.22, {"1": "CC2", "2": "GND"}, R0402)
    for i, (ref, val, fp) in enumerate((("C1", "47uF 10V", C1206), ("C2", "22uF 10V", C0805), ("C3", "22uF 10V", C0805))):
        place("Device:C", ref, val, 144.78 + 15.24 * i, 236.22, {"1": "+5V", "2": "GND"}, fp)
    place("Device:C", "C4", "22uF 10V", 193.04, 236.22, {"1": "+3V3", "2": "GND"}, C0805)
    for i, (fb, c, net) in enumerate((("FB1", "C5", "VCCIO01"), ("FB2", "C6", "VCCIO23"), ("FB3", "C7", "VCCIO67"))):
        x = 213.36 + 25.4 * i
        place("Device:FerriteBead_Small", fb, "30R 2A", x, 233.68, {"1": "+3V3", "2": net},
              "Inductor_SMD:L_0603_1608Metric", {"MPN": "Sunlord GZ1608D300TF (30R@100MHz, 2A; Dock uses PZ1608D300-3R0TF)"})
        place("Device:C", c, "100nF", x + 12.7, 236.22, {"1": net, "2": "GND"}, C0402)
    for i, net in enumerate(("+5V", "+3V3", "GND", "VBUS")):
        pwr_flag(net, 40.64 + 15.24 * i, 284.48)
    text("Keep total 3V3 draw from headers under ~500 mA (module buck also powers the FPGA).", 15.24, 297.18, 1.5, False)

    # ---- configuration (D9)
    text("CONFIG - READY / DONE / TCK as Sipeed Dock; RECONFIG_N button to GND (Gowin UG714)", 294.64, 190.5)
    place("Device:R", "R3", "49.9k", 299.72, 210.82, {"1": "+3V3", "2": "READY"}, R0402)
    place("Device:R", "R4", "49.9k", 312.42, 210.82, {"1": "READY", "2": "LED_READY"}, R0402)
    place("Device:LED", "D3", "READY green", 337.82, 210.82, {"1": "GND", "2": "LED_READY"}, LED)
    place("Device:R", "R5", "49.9k", 299.72, 243.84, {"1": "+3V3", "2": "DONE"}, R0402)
    place("Device:R", "R6", "49.9k", 312.42, 243.84, {"1": "DONE", "2": "LED_DONE"}, R0402)
    place("Device:LED", "D4", "DONE green", 337.82, 243.84, {"1": "GND", "2": "LED_DONE"}, LED)
    place("Device:R", "R7", "4.7k", 299.72, 276.86, {"1": "+3V3", "2": "LED_PWR"}, R0402)
    place("Device:LED", "D2", "POWER green", 337.82, 276.86, {"1": "GND", "2": "LED_PWR"}, LED)
    place("Device:R", "R8", "5.1k", 360.68, 210.82, {"1": "JTAG_TCK", "2": "GND"}, R0402)
    place("Device:R", "R9", "10k", 375.92, 210.82, {"1": "+3V3", "2": "RECONFIG_N"}, R0402)
    place("Device:C", "C8", "100nF", 386.08, 210.82, {"1": "RECONFIG_N", "2": "GND"}, C0402)
    place("Switch:SW_Push", "SW1", "RECONFIG", 414.02, 210.82, {"1": "RECONFIG_N", "2": "GND"}, BTN,
          {"MPN": "XKB TS-1187A-B-A-B"})

    # ---- user buttons (D5)
    text("USER BUTTONS - as Dock S1/S2 (active high; enable FPGA pull-down)", 294.64, 307.34)
    for i, (sw, r, c, pin) in enumerate((("SW2", "R10", "C9", "IOT3A"), ("SW3", "R11", "C10", "IOT3B"))):
        y = 330.2 + 30.48 * i
        place("Device:R", r, "100R", 299.72, y, {"1": "+3V3", "2": f"BTN_{pin}"}, R0402)
        place("Switch:SW_Push", sw, f"S{i + 1} ({pin})", 335.28, y, {"1": f"BTN_{pin}", "2": pin}, BTN,
              {"MPN": "XKB TS-1187A-B-A-B"})
        place("Device:C", c, "100nF", 358.14, y, {"1": pin, "2": "GND"}, C0402)

    # ---- mounting holes
    text("MOUNTING", 459.74, 307.34)
    for i in range(4):
        ref = f"H{i + 1}"
        hx = 462.28 + 12.7 * i
        place("Mechanical:MountingHole", ref, "M2.5", hx, 325.12, {},
              "MountingHole:MountingHole_2.7mm_M2.5", fields_xy=((hx, 320.04, "center"), (hx, 330.2, "center")),
              in_bom=False)


def write():
    OUT.mkdir(exist_ok=True)
    libs = "\n".join("\t\t" + lib_symbol(l)[0].replace("\n", "\n\t") for l in used_libs)
    sch = (f'(kicad_sch\n\t(version 20250114)\n\t(generator "eeschema")\n\t(generator_version "9.0")\n'
           f'\t(uuid "{ROOT_UUID}")\n\t(paper "A2")\n'
           f'\t(title_block\n\t\t(title "Tang Primer 25K Carrier v2")\n\t\t(date "2026-11-23")\n\t\t(rev "2.0")\n'
           f'\t\t(comment 1 "Dock-compatible headers; pinout 4-way verified (spec, core sch, Dock sch, Sipeed footprint)")\n'
           f'\t\t(comment 2 "Generated by carrier_v2/tools/gen_schematic.py")\n\t)\n'
           f'\t(lib_symbols\n{libs}\n\t)\n' + "\n".join(items) +
           f'\n\t(sheet_instances (path "/" (page "1")))\n\t(embedded_fonts no)\n)\n')
    (OUT / f"{PROJECT}.kicad_sch").write_text(sch, encoding="utf-8")
    pro = OUT / f"{PROJECT}.kicad_pro"
    if not pro.exists():
        pro.write_text(json.dumps({"meta": {"filename": f"{PROJECT}.kicad_pro", "version": 3}}, indent=2) + "\n",
                       encoding="utf-8")
    (OUT / "fp-lib-table").write_text(
        '(fp_lib_table\n\t(version 7)\n\t(lib (name "carrier_v2") (type "KiCad") (uri "${KIPRJMOD}/carrier_v2.pretty") '
        '(options "") (descr "Tang 25K carrier v2 project footprints"))\n)\n', encoding="utf-8")
    (OUT / "expected_nets.json").write_text(json.dumps(
        {"nets": {k: sorted(v) for k, v in sorted(expected.items())}, "no_connect": sorted(nc_expected)},
        indent=1), encoding="utf-8")
    print(f"wrote {PROJECT}.kicad_sch: {len(ref_seen)} parts, {len(expected)} nets, "
          f"{sum(len(v) for v in expected.values())} connected pins, {len(nc_expected)} no-connect pins")


if __name__ == "__main__":
    build()
    write()

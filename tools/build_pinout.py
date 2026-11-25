"""Build carrier_v2/pinout_v2.csv: every core-board BTB pin, cross-checked.

Sources (all in ../sources):
  A. Tang_Primer_25K_Specification_V1.0_en.pdf, pages 6-9 (official pin tables)
  B. Tang_Primer_25K_52300_Schematic.pdf, page 3 (FPGA symbol -> net label -> ball)
     and page 5 (connector symbol, checked by eye; see PLAN.md decisions log)
  C. Tang_Primer_25K_Dock_60033_Schematic.pdf (how Sipeed's own carrier uses each pin)
  D. sipeed_tang_primer_25k.cst (Sipeed example constraints)
v1 comparison: ../reference_v1/spec_nets.py (the v1 netlist actually used on the v1 PCB).

Usage:  python build_pinout.py      (needs: pip install pymupdf)
"""
import csv, re, runpy, sys
from pathlib import Path
import pymupdf

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "sources"
OUT = HERE.parent / "pinout_v2.csv"
SPEC = SRC / "Tang_Primer_25K_Specification_V1.0_en.pdf"
CORE = SRC / "Tang_Primer_25K_52300_Schematic.pdf"

BALL = re.compile(r"^[A-L](1[01]|[1-9])$")


def spec_tables():
    """Parse spec pages 6-9 into {(conn, pin): dict}."""
    doc = pymupdf.open(SPEC)
    rows = {}
    for page, conn, first in ((5, "J2", 1), (6, "J2", 2), (7, "J1", 1), (8, "J1", 2)):
        lines = [l.strip() for l in doc[page].get_text().splitlines() if l.strip()]
        lines = lines[lines.index("Connector") + 1:]
        expect, i = first, 0
        while i < len(lines) and expect <= 60:
            if lines[i] != str(expect):
                raise SystemExit(f"spec p{page + 1}: expected pin {expect}, got {lines[i]!r}")
            # the next pin number starts a row only if a ball or a fixed name follows it
            # (bank numbers like "5" can equal the next pin number)
            def starts_row(k):
                return lines[k] == str(expect + 2) and (
                    k + 1 >= len(lines) or BALL.match(lines[k + 1])
                    or lines[k + 1].startswith(("GND", "VCCIO", "VDD", "MIPI")))
            j = i + 1
            while j < len(lines) and not starts_row(j):
                j += 1
            cells = lines[i + 1:j]
            # GCLK cells can wrap onto two lines ending in "/": re-join them
            joined = []
            for c in cells:
                if joined and joined[-1].endswith("/"):
                    joined[-1] += c
                else:
                    joined.append(c)
            cells = joined
            if cells and BALL.match(cells[0]):
                ball, bank, volt, name, *extra = cells
                rows[(conn, expect)] = dict(kind="IO", ball=ball, bank=bank, bank_v=volt,
                                            name=name, special=" ".join(extra))
            else:
                text = " ".join(cells)
                rows[(conn, expect)] = dict(kind="FIXED", ball="", bank="", bank_v="", name=text, special="")
            expect += 2
            i = j
    return rows


def schematic_balls():
    """Net label -> ball from the FPGA symbol page of the core schematic."""
    words = pymupdf.open(CORE)[2].get_text("words")
    balls = [w for w in words if BALL.match(w[4])]
    labels = [w for w in words if re.fullmatch(r"(IO[TBLR]\d+[AB]|READY|DONE|RECONFIG|TCK|TMS|TDI|TDO)", w[4])]
    res = {}
    for l in labels:
        yc = (l[1] + l[3]) / 2
        c = [b for b in balls if b[2] <= l[0] and l[0] - b[2] < 60 and abs((b[1] + b[3]) / 2 + 2.05 - yc) < 1.0]
        if c:
            res.setdefault(l[4], set()).add(max(c, key=lambda b: b[2])[4])
    return {k: v.pop() for k, v in res.items() if len(v) == 1}


# How Sipeed's own Dock (60033) uses the pins we care about (read from its schematic, page 1-2).
DOCK = {
    "IOB56A": "Dock: FPGA_UART_RX (to BL616 debugger)",
    "IOB56B": "Dock: FPGA_UART_TX (to BL616 debugger)",
    "READY": "Dock: 49.9k pull-up to 3V3 + LED via 49.9k",
    "DONE": "Dock: 49.9k pull-up to 3V3 + LED via 49.9k",
    "RECONFIG": "Dock: not connected (internal pull-up)",
    "JTAG_TCK": "Dock: 5.1k pull-down + BL616 JTAG",
    "JTAG_TMS": "Dock: BL616 JTAG", "JTAG_TDI": "Dock: BL616 JTAG", "JTAG_TDO": "Dock: BL616 JTAG",
    "IOT23A": "Dock: USB-A host D+", "IOT23B": "Dock: USB-A host D-",
    "IOT3A": "Dock: button S1", "IOT3B": "Dock: button S2",
    "VCCIO0/1 Input": "Dock: from module VDD_3V3 via ferrite bead",
    "VCCIO2/3 Input": "Dock: from module VDD_3V3 via ferrite bead",
    "VCCIO6/7 Input": "Dock: from module VDD_3V3 via ferrite bead",
    "VDD_5V0 Input": "Dock: USB-C VBUS via 2A fuse",
}
CFG_NAME = {"RECONFIG": "RECONFIG", "READY": "READY", "DONE": "DONE",
            "JTAG_TCK": "TCK", "JTAG_TMS": "TMS", "JTAG_TDI": "TDI", "JTAG_TDO": "TDO"}


def main():
    spec = spec_tables()
    sch = schematic_balls()
    v1 = runpy.run_path(str(HERE.parent / "reference_v1" / "spec_nets.py"))
    v1map = {("J1", p): n for p, (n, _) in v1["J1"].items()} | {("J2", p): n for p, (n, _) in v1["J2"].items()}
    v1_alias = {"UART_TX": "IOT56A", "UART_RX": "IOT56B", "+3V3": None, "GND": "GND", "+5V": None}

    out, problems = [], []
    for conn in ("J1", "J2"):
        for pin in range(1, 61):
            s = spec[(conn, pin)]
            if s["kind"] == "IO":
                sig = s["special"].split()[0] if s["special"].split() and s["special"].split()[0].startswith("JTAG") else s["name"]
                for k in ("RECONFIG", "READY", "DONE"):
                    if k in s["special"]:
                        sig = k
                lookup = CFG_NAME.get(sig, sig)
                sb = sch.get(lookup, "")
                agree = "yes" if sb == s["ball"] else ("n/a" if not sb else "NO")
            else:
                sig, sb, agree = s["name"], "", "n/a"
            # v1 comparison
            v1n = v1map[(conn, pin)]
            v1_cmp = v1_alias.get(v1n, v1n)
            if s["name"] == "GND":
                ok = v1n == "GND"
            elif "VCCIO" in s["name"]:
                ok = v1n == "+3V3"
            elif "VDD_5V0" in s["name"]:
                ok = v1n == "+5V"
            elif s["name"].startswith(("VDD_1V8", "VDD_2V5", "VDD_3V3")):
                ok = v1n.startswith("VDD_")
            elif s["name"].startswith("MIPI"):
                ok = v1n.startswith("M0_")
            elif sig in CFG_NAME:
                ok = v1n in (sig, "JTAG_" + sig.replace("JTAG_", ""))
            else:
                ok = v1_cmp == s["name"]
            note = ""
            if not ok:
                note = f"v1 netlist has '{v1n}' here"
                problems.append(f"{conn}.{pin}: official={s['name']} v1={v1n}")
            if v1n in ("UART_TX", "UART_RX"):
                note = (note + "; " if note else "") + "v1 used this pin as UART; Sipeed's UART is IOB56A/IOB56B (J1.19/J1.21)"
            if agree == "NO":
                problems.append(f"{conn}.{pin}: spec ball {s['ball']} != schematic ball {sb}")
            out.append(dict(connector=conn, pin=pin, signal=sig, fpga_ball=s["ball"], bank=s["bank"],
                            bank_voltage=s["bank_v"], special_function=s["special"],
                            schematic_ball=sb, spec_vs_schematic=agree,
                            dock_usage=DOCK.get(sig, DOCK.get(s["name"], "")),
                            v1_net=v1n, v1_correct="yes" if ok else "NO", note=note,
                            source="Spec V1.0 p%d; core sch p3/p5" % ({("J2", 1): 6, ("J2", 0): 7, ("J1", 1): 8, ("J1", 0): 9}[(conn, pin % 2)])))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)
    gpio = [r for r in out if r["fpga_ball"] and r["signal"] not in CFG_NAME]
    print(f"wrote {OUT.name}: {len(out)} pins, {len(gpio)} plain GPIOs, "
          f"{sum(r['spec_vs_schematic'] == 'yes' for r in out)} balls agree spec vs schematic")
    print("problems:" if problems else "no problems")
    for p in problems: print("  ", p)


if __name__ == "__main__":
    main()

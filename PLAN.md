# Tang Primer 25K carrier, v2: fix plan

Goal: a carrier board for the Tang Primer 25K core module that powers it,
programs it over JTAG, and breaks out its GPIOs. It must pass KiCad ERC/DRC
with zero errors and be checked against official sources before ordering.

v1 (`tang25k_carrier_full_package.zip`) is used only as a reference for
*intent*. Its PCB is not reused: the parts are double-rotated, it has
~850 copper shorts and 16+ unconnected nets.

## Rules for v2
- **Every pin comes from an official source.** That means Sipeed's core-board
  schematic, pin table or official footprint, or Gowin's datasheets. Each
  pin in the final pinout table cites its source. Community files are only
  used for cross-checking.
- **Electrical decisions get written down** in the "Decisions" log at the
  bottom of this file, with the reason.
- **Layout is done in KiCad itself**, with hand placement, Freerouting or
  manual routing, and KiCad's own DRC. There is no custom geometry generator.
- **Nothing is ordered** until DRC is clean, footprints are printed 1:1 and
  test-fitted, and the pinout is cross-checked twice.

## Steps

### 1. Gather official sources
- Sipeed core-board schematic, pin table and official PCB footprint (from
  `dl.sipeed.com/shareURL/TANG/Primer_25K`: 02_Schematic, 06_PCB_Lib,
  01_Specification).
- Sipeed 25K **Dock** schematic. It shows how Sipeed handles VCCIO,
  RECONFIG/READY/DONE, JTAG and 5 V on a working carrier.
- Sipeed example constraint files (`sipeed/TangPrimer-25K-example`, `*.cst`).
  These cross-check Dock pin to FPGA ball.
- Gowin GW5A datasheet and the Arora V programming/configuration guide.
  These cover RECONFIG_N, READY, DONE, JTAG and power-up behaviour.
- Hirose DF40 drawings: which part is on the module, which mates with it,
  the land pattern and the stack height.
- **Done when:** each file is saved in `carrier_v2/sources/` with its URL in
  `sources/SOURCES.md`.

### 2. Build the verified 120-pin table
- For each pin, record: connector, pin, signal name, FPGA ball, bank, source,
  and whether it matches v1.
- Resolve J1.13 / J1.15 (v1's ball column and netlist disagree).
- Confirm which pins are VCCIO *inputs*, which are module power *outputs*,
  and where 5 V goes in.
- Break out IOB56A, IOB56B and IOB60A, which v1 dropped.
- **Done when:** `pinout_v2.csv` is complete and every row has a source.

### 3. Fix the configuration circuits
- RECONFIG_N is active-low. The button goes to GND, with no pull-down. Add a
  pull-up only if the module lacks one.
- READY: remove v1's pull-down. Add a pull-up if the module lacks one.
- DONE: drive the LED through a small N-MOSFET (2N7002-class) so it doesn't
  load the DONE pin.
- **Done when:** the circuit matches Gowin's recommended circuit and the Dock.

### 4. Redesign 5 V input and the 3.3 V rail
- Decide the VCCIO source: the module's own 3.3 V output, as the Dock does,
  or a separate regulator on the carrier.
- Replace the SS34 diode OR plus AMS1117 with lower-drop parts: a P-MOSFET
  ideal-diode OR and a low-dropout LDO, if one is still needed.
- Add 22–47 µF bulk capacitance at the module's 5 V pins, a VBUS TVS diode,
  and a resettable fuse.
- **Done when:** a voltage budget table shows ≥3.2 V on VCCIO and ≥4.5 V at the
  module from a worst-case 4.75 V USB supply.

### 5. Choose the JTAG programmer
- Gowin's Programmer does not support Altera USB-Blaster cables.
- Options:
  - (a) A header in the pinout of a Gowin-supported cable.
  - (b) A 2×5 header for an FT2232H/CH347 adapter used with openFPGALoader.
  - (c) A USB JTAG chip on the board itself.
- **Done when:** the choice is made, and the pinout plus the exact programming
  command are documented.

### 6. Redraw the schematic properly
- Use real wires and labels, power flags and no-connect flags.
- The symbol and footprint libraries live inside the project, so it opens on
  any machine.
- **Done when:** KiCad ERC reports 0 errors.

### 7. Footprint and test-fit
- Use Sipeed's official core-board footprint, and check it against the Hirose
  land pattern.
- Print at 1:1 and lay the real module on the paper to check pin 1
  orientation and the mounting holes.
- **Done when:** the paper fit matches.

### 8. Placement and socket fan-out
- Stackup: F.Cu signal / In1 **solid GND** / In2 power / B.Cu signal.
- Outer socket rows escape outward on F.Cu.
- Inner rows escape into the ~11 mm gap between the two sockets, with vias
  placed there. No vias between the 0.4 mm-pitch pads.
- Headers, power and the JTAG header get their own non-overlapping zones,
  checked with KiCad courtyards.

### 9. Routing and DRC
- Load JLCPCB 4-layer design rules.
- Route about 70 slow GPIO nets, then the power nets. Pour GND and add
  stitching vias.
- **Done when:** KiCad DRC shows 0 errors and 0 unconnected items, and the 3D
  view looks right.

### 10. Fabrication files
- Gerbers, drill files, BOM and pick-and-place (CPL) for JLCPCB, including
  assembly of the DF40 sockets.
- Review in JLCPCB's DFM viewer before ordering.

### 11. Bring-up checklist
1. Power the board without the module and measure the rails.
2. Fit the module and measure current draw.
3. Run a JTAG scan with openFPGALoader.
4. Load a blink bitstream and run a UART echo test.
5. Test every header pin with a walking-ones bitstream.

## Tools needed on your PC
- **KiCad 10.0.8**, installed 23 Nov 2026 at `C:\Program Files\KiCad\10.0`,
  with `kicad-cli` at `...\10.0\bin\kicad-cli.exe`. Symbol and footprint
  libraries are complete. 3D models were trimmed to the 14 folders this board
  uses, and the demos were removed. To restore the rest, re-run the installer
  (`D:\Claude\_downloads\kicad-10.0.8-x86_64.exe`, SHA-256 verified) and choose
  Modify.
- openFPGALoader and/or Gowin EDA for bring-up.

## Status
| Step | State |
|---|---|
| 1. Sources | **Done**, including Sipeed's official footprint, dimension drawing, STEP model and Gowin UG714 (see `sources/SOURCES.md`) |
| 2. Pinout | **Done**: `pinout_v2.csv`, built by `tools/build_pinout.py` |
| 3. Config circuits | **Done** (D9): READY/DONE pull-ups + LEDs, TCK pull-down, RECONFIG_N button to GND |
| 4. Power | **Done** (D8): USB-C → fuse/TVS → +5V; module VDD_3V3 → beads → VCCIO; no carrier regulator |
| 5. JTAG | **Done** (D10): Dock J7 pinout, +5V and BL616_EN pins left open |
| 6. Schematic | **Done**: `kicad/carrier_v2.kicad_sch` (46 parts, 89 nets). **ERC 0 errors / 0 warnings**; `tools/verify_schematic.py` passes all checks; mutation-tested |
| 7. Footprint test-fit | Footprint done (D11). **Your side:** print `DF40C-60DS-0.4V_51_Sipeed` 1:1 once the PCB layout exists and lay the module on it |
| 8. Placement + fan-out | **Done**: `kicad/carrier_v2.kicad_pcb` built by `tools/gen_pcb.py` (D12–D14). DRC: **0 clearance/courtyard/silk errors, schematic parity 0**; only unrouted connections remain |
| 9. Routing + DRC | **Done**: routed with Freerouting 1.9.0 (`tools/route_pcb.py`), cleaned with `tools/cleanup_pcb.py`. **DRC: 0 errors, 0 unconnected, schematic parity 0.** Warnings left: 90 × PMOD outline past the board edge (same as the Dock) and 1 × 0.6 mm VCCIO01 stub (the router joins it partway along, so it can't be removed). 1.96 m of copper (F 683 / In2 972 / B 302 mm), 117 vias, no signals on the In1 GND plane |
| 10. Fabrication files | **Done**: `fab/` built by `tools/make_fab.py`. Gerbers and drill zip (64 × 40 mm, 4 layers), JLCPCB BOM (LCSC numbers on 12 lines, 7 generic lines left for auto-match) and CPL, hand-solder list, `fab/ORDERING.md`. Power re-checked: VBUS/+5V 0.6 mm ≈ 1.65 A, +3V3 0.4 mm ≈ 1.23 A (IPC-2221, outer 1 oz, 10 °C rise). **Final DRC: 0 errors, 0 unconnected, parity 0.** Warnings: 90 PMOD-outline overhang, 2 harmless stubs, **1 via pair 0.40 mm apart drill-edge to drill-edge** (JLC guideline 0.5; check the JLC DFM report) |
| 11. Bring-up | After the boards arrive |

## Facts established in steps 1–2
1. **All 120 pins checked.** The spec tables and the schematic agree on all 75 FPGA-ball pins. There are 68 plain GPIOs plus RECONFIG, READY, DONE and 4 JTAG pins.
2. **The only v1 pin error is J1.13 / J1.15, which were swapped.** Officially, J1.13 = IOT58B (ball F6) and J1.15 = GND. v1 tied IOT58B to ground and wired a ground pin to the header as "T58B".
3. **v1's UART was on the wrong pins.** Sipeed's UART (Dock debugger and example code) is **IOB56A = FPGA RX (B3, J1.19)** and **IOB56B = FPGA TX (C3, J1.21)**. v1 used IOT56A/IOT56B and left IOB56A, IOB56B and IOB60A unconnected.
4. **The carrier must supply VCCIO0/1, VCCIO2/3 and VCCIO6/7.** Sipeed's Dock feeds them from the module's own **VDD_3V3 output (J2.46/48/50)** through ferrite beads, with no extra regulator.
5. **The module accepts 3.6–5.5 V on VCC_5V** (spec p5); its regulators are on the module. A diode drop at the input is therefore harmless to the module.
6. **The spec requires the carrier to set READY, DONE and JTAG_TCK with resistors.** The Dock uses 49.9 k pull-ups on READY and DONE, each with an LED through 49.9 k to GND, and a 5.1 k pull-down on TCK. RECONFIG is left unconnected (internal pull-up).
7. **The Dock's 5 V input** is USB-C VBUS → 2 A fuse → +5 V, with a TVS diode, 5.1 k CC resistors, 220 µF on +5 V and on 3V3, and 3× 22 µF on +5 V.
8. **The Dock's JTAG header** (J7, 2×4, 2.54 mm) is: 1 TMS, 2 TDI, 3 TCK, 4 +5V, 5 TDO, 6 GND, 7 +3V3, 8 BL616_EN. Shorting BL616_EN to GND disables the Dock's on-board debugger.
9. **The DF40 land pattern in v1 is wrong.** The Hirose recommended pattern for the **receptacle DF40C-60DS-0.4V(51)** (1.5 mm stack) is 0.2 mm pads at 0.4 mm pitch, outer span 3.78 mm, inner gap 2.38 mm. That gives **0.70 mm pads with rows 3.08 mm apart**. v1, and the community footprint it copied, use 1.14–1.2 mm pads with rows 2.28 mm apart, which matches neither the receptacle nor the header (header: 0.23 × 0.66 mm pads, rows 2.71 mm apart). The connector is **not polarized**, so pin-1 orientation must come from Sipeed's drawing.

10. **Sipeed's official carrier footprint** (`sources/sipeed_official/Tang_Primer_25K_Footprint.kicad_pcb`) matches the Hirose receptacle pattern exactly: 0.20 × 0.70 mm pads, rows at ±1.54 mm. Its J1 and J2 centres are 13.97 mm apart, both rotated 180°. **v2 uses this footprint as-is.**
11. **Gowin UG714 (official) confirms the boot-pin behaviour.** RECONFIG_N has an internal weak pull-up, and a low pulse triggers reconfiguration. READY must not be pulled down during power-up. DONE goes high on success.

## Decisions log
| # | Decision | Reason | Source |
|---|---|---|---|
| D1 | Use `pinout_v2.csv` as the only pin reference for v2 | Three-way check: spec tables, schematic symbol, schematic connector page | Spec p6–9, core sch p3/p5 |
| D2 | UART header on IOB56A (FPGA RX) / IOB56B (FPGA TX) | Matches Sipeed's Dock and example code, so their bitstreams work unchanged | Dock sch p1–2, `.cst` |
| D3 | Break out all 68 GPIOs, including IOB56A, IOB56B, IOB60A and IOT58B | v1 lost 3 GPIOs and grounded IOT58B | `pinout_v2.csv` |

| D4 | **Connectors copy the Dock's**: J3 2×20 header (38 GPIO + 5 V + GND) and three 2×6 right-angle PMOD sockets, with the same pin numbers and FPGA pins as Dock J3/J4/J5/J6 | Sipeed's PMOD/SDRAM/HDMI examples and your own Dock `.cst` files work unchanged; together with D5–D7 all 68 GPIOs are reachable | Dock sch p1 (text + close-up check) |
| D5 | User buttons S1/S2 on IOT3A (H11) / IOT3B (H10), active-high: 3V3 → 100 Ω → switch → pin, 100 nF to GND | Same as the Dock; Sipeed examples use H11 as reset with an internal pull-down | Dock sch p1, `.cst` |
| D6 | AUX 1×4 header: GND, IOT23B, IOT23A, 3V3 | These are the Dock's USB-host pins; v2 has no USB-A, so they go to a header | Dock sch p1, p3 |
| D7 | UART 1×3 header: GND, FPGA_RX (IOB56A/B3), FPGA_TX (IOB56B/C3), **no VCC pin** | A USB-UART adapter can't back-power the board | D2 |
| D8 | Power: **USB-C only** (JST dropped). VBUS → 2 A fuse → +5 V, SMF5.0A TVS, 5.1 k CC pull-downs, 47 µF + 2× 22 µF on +5 V. **+3V3 = the module's VDD_3V3 output** (J2.46/48/50) with 22 µF, then 3 ferrite beads (30 Ω @ 100 MHz, 3 A) to VCCIO0/1, VCCIO2/3 and VCCIO6/7. **No regulator on the carrier.** Keep the total 3V3 draw from the headers under ~500 mA, because the module's buck converter also powers the FPGA | P2, approved; same as the Dock | Spec p5, Dock sch p1–2 |
| D9 | Config: READY and DONE get 49.9 k pull-up plus 49.9 k + green LED; TCK 5.1 k pull-down; RECONFIG_N 10 k pull-up, 100 nF and a button to GND; power LED via 4.7 k | P1, approved; UG714 | Dock sch p1, UG714 p18–19 |
| D10 | JTAG J7: 2×4, Dock J7 pinout (1 TMS, 2 TDI, 3 TCK, 5 TDO, 6 GND, 7 3V3); **pins 4 (+5V) and 8 (BL616_EN) not connected** | P3, approved | Dock sch p2 |
| D11 | DF40 footprint = Sipeed's official one (`kicad/carrier_v2.pretty/DF40C-60DS-0.4V_51_Sipeed`), made by `tools/make_df40_footprint.py` | **4-way pin check**: spec tables, core schematic, Dock schematic, and Sipeed's own pad nets (120/120 match) | `sources/sipeed_official` |

| D12 | **DF40 fan-out**: every connected socket pad gets a 0.1 mm stub straight away from the socket body to a **0.46/0.2 mm via**; vias alternate between two rows (0.33 mm and 0.93 mm past the pad end). No vias between pads or in Hirose's 'layout prohibited' area. Worst-case gaps: via–stub 0.12 mm, via hole–hole 0.52 mm, row-B via to PMOD pad 0.27 mm. Stubs and vias are locked | The 0.4 mm pitch leaves 0.2 mm between pads, too little for any trace. The gap to the PMOD/40-pin rows (1.4–1.9 mm) only fits two staggered rows | Hirose catalog p4, JLCPCB capabilities |
| D13 | **Design rules** (`carrier_v2.kicad_pro`): board minimum 0.1 mm track and clearance, via 0.46/0.2, annular ring 0.13, hole-to-hole 0.5, copper-to-edge 0.3. Default and Power classes use 0.1 mm clearance (Power tracks 0.4 mm). Routing will use 0.15 mm clearance in the router | JLCPCB 4-layer minimums are 0.09 mm trace/space, 0.2 mm drill, 0.45 mm via, 0.13 mm annular ring, 0.5 mm hole-to-hole. **kicad-cli 10.0.8 ignored a `.kicad_dru` file** (tested: neither stricter nor looser rules changed the result), so a fan-out-only rule isn't possible | [JLCPCB capabilities](https://jlcpcb.com/capabilities/pcb-capabilities) |
| D14 | **Mechanical layout copies the Dock** (`sources/sipeed_official/dock_layout.json`): outline 64×40 mm, J1/J2, J3, J4–J6 and H1–H4 at the Dock's coordinates. Each is placed by matching every pad to the Dock's pads, **anchored on pin 1** (without the anchor, the symmetric DF40 also 'matched' at 0°, which would have reversed every pin). Exceptions: J7 is 0.5 mm lower (the Dock's JTAG courtyard overlaps its 40-pin); USB-C is a different part, placed by its body with the shell 0.3 mm past the right edge | Sipeed modules and enclosures that fit the Dock fit this board | Dock iBOM |

| D15 | **Routing widths**: signals 0.12 mm with 0.1 mm clearance and 0.46/0.2 mm vias; power (+5V, +3V3, VBUS, VCCIO) 0.3 mm with 0.6/0.3 vias. Router vias kept apart with a Specctra via-to-via clearance; the last 2 too-close pairs were nudged apart by `cleanup_pcb.py` | A trace leaving a row-A fan-out via passes between row-B vias 0.34 mm apart: 0.12 + 2×0.1 = 0.32 fits | JLCPCB capabilities |
| D16 | **GND stitch vias**: every SMD ground pad (except sockets and USB-C) gets its own via to the In1 plane, placed before routing (19 vias) | Without them, routed traces cut the outer GND pours into islands and left C5 and pour fragments unconnected | DRC history |
| D17 | **Router setup**: In1.Cu is a *power* layer (solid GND plane, no signals); signals use F.Cu, In2.Cu and B.Cu; In2 gets a +3V3 pour and F/B get GND pours after routing. **Freerouting 1.9.0** (5 MB jar, Java 17+) runs on the installed Java 21, with a 20-minute hard time limit | The v2.5.0 native CLI crashed on its first pass and then hung for 3 h. v2.2+ jars need Java 25. Without the power-layer setting, Freerouting routed signals through the GND plane | Freerouting logs |

| D18 | **Power widths** (after measuring, step 10): `Power5V` (+5V, /VBUS) 0.6 mm and `Power3V3` (+3V3) 0.4 mm, both restricted to the outer 1 oz layers via Specctra `use_layer`; clearance 0.1 mm at the socket. VCCIO stays at 0.12 mm (low current) | The first routing had VBUS at 0.12 mm (≈0.5 A, against a 2 A fuse: the pattern missed the `/` prefix on label nets) and 54 mm of +3V3 on 0.5 oz inner copper (≈0.3 A) | IPC-2221 |
| D19 | **USB-C shell tied to its GND pins**: the two back shell pads get 0.3 mm F.Cu links to A1/A12. The front pads use the pours (direct links there would cross CC and the NPTH pegs) | One shell pad ended up isolated from GND in a routing run | DRC |
| D21 | **D1 TVS polarity fixed (25 Nov 2026)**: SMF5.0A is unidirectional. v2 used KiCad's bidirectional `Device:D_TVS` symbol with pin 1 on GND, so the cathode (footprint pad 1, band) sat on GND and USB 5 V would have forward-biased it and blown F1. Now `Device:D_Zener` (K=1/A=2), cathode on VBUS; the footprint is rotated 180° (270°) with pad nets swapped, so copper is unchanged and only the silkscreen cathode mark and CPL rotation (−90) move. `verify_schematic.py` now checks D1 and LED polarity. All LCSC numbers pinned; `carrier_v2_bom_mpn.csv` adds manufacturer + MPN | Caught in JLCPCB's 3D placement preview | Device.kicad_sym, SMF5.0A datasheet |
| D20 | **Parts for JLCPCB**: DF40 C597938, USB-C C165948, TS-1187A C318884, SMF5.0A C169426, 2 A 1206 fuse C354895, **ferrite Sunlord GZ1608D300TF C24821** (the Dock's PZ1608D300-3R0TF isn't listed at LCSC; same 30 Ω @ 100 MHz, 2 A), LED KT-0603G C12624, 22 µF 0805 C45783 (25 V). **ENIG** finish for the 0.4 mm DF40 | Checked on lcsc.com / jlcpcb.com, Nov 2026 | LCSC/JLCPCB part pages |

**Review notes from step 9 (resolved in step 10):**
- The 5 V path (USB-C → fuse → module) is routed at 0.3 mm. Partly inner-layer (0.5 oz) copper, so check its width and current before ordering, and widen if needed.
- The In2 +3V3 pour is heavily cut up by signal routes. +3V3 is also routed as tracks, so connectivity doesn't depend on the pour, but check the 3V3 feed to the PMODs.

### Approved proposals (signed off 23 Nov 2026; implemented as D8–D10)
- **P1 (config).** Copy the Dock exactly: 49.9 k pull-up plus LED on READY and on DONE, and a 5.1 k pull-down on TCK. Add a RECONFIG button **to GND** with a 10 k pull-up and 100 nF. Remove v1's READY and RECONFIG pull-downs.
- **P2 (power).** Feed VCCIO from the module's VDD_3V3 through 3 ferrite beads, as the Dock does, and **drop the AMS1117**. 5 V input: USB-C → 2 A fuse → TVS → +5 V, with bulk capacitors as on the Dock. If the JST input stays, OR it with a P-MOSFET ideal diode instead of the SS34 diodes.
- **P3 (JTAG).** Make the carrier's JTAG header pin-for-pin identical to the Dock's J7 (2×4). Leave **+5V not connected** so two supplies never fight. Then the carrier can be programmed with an FT2232H or CH347 USB-JTAG adapter and openFPGALoader (recommended, cheap), or with a Gowin cable. Using the Dock's own BL616 debugger is **unverified**: without a module, the Dock's 3.3 V rail (which powers the BL616) is dead, so it would have to be back-fed from the carrier through the 3V3 pin. Test this on the bench before relying on it.

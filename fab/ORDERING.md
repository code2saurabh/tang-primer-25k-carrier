# Ordering the Tang 25K carrier v2 from JLCPCB

**Status:** design checks pass, but this board has **not been built yet**. It's a first prototype, so
order the minimum quantity (5 boards, 2 assembled).

## 1. PCB (upload `carrier_v2_jlcpcb_gerbers.zip`)
| Setting | Choose | Why |
|---|---|---|
| Layers | **4** | Signals on top/In2/bottom, In1 = solid GND plane |
| Stackup | JLC04161H-7628 (default 1.6 mm) | No controlled-impedance nets |
| Thickness | 1.6 mm | Same as the Dock |
| Outer / inner copper | 1 oz / 0.5 oz (default) | Power traces are sized for this (D18) |
| Min via hole / diameter | **0.2 mm / 0.45 mm** (board uses 0.2/0.46) | Needed by the module-socket fan-out; a small surcharge may apply |
| Surface finish | **ENIG** | The DF40 sockets have 0.4 mm pitch. HASL is too uneven for them |
| Via covering | **Plugged** | "Tented" is greyed out once 0.2 mm vias are chosen; Plugged is free and fine |
| Confirm production file | **Yes** ($1.05) | Lets you see JLC's DFM/production file (the 0.40 mm via pair) before they build |
| Remove order number | Specify a location, or 'yes' if offered | Keeps the silkscreen clean |

**Before paying, open JLCPCB's Gerber viewer / DFM report** and check:
- The outline is 64 × 40 mm, with 4 mounting holes.
- Hole-to-hole spacing: one pair of 0.2 mm vias under the module is **0.40 mm** apart, drill edge to drill edge (JLC guideline 0.5 mm; PLAN.md step 9 note).
  - If the DFM flags it, stop and ask for a re-route of that net.
- Nothing is flagged as a short or open.

## 2. Assembly (PCBA, top side)
Upload `carrier_v2_jlcpcb_bom.csv` and `carrier_v2_jlcpcb_cpl.csv`.

- **Every line has an LCSC number** (see `carrier_v2_bom_mpn.csv` for manufacturer and MPN). JLC still flags the resistor lines ("comment does not match") and lines that share a part (LEDs, switches) and leaves them unticked: tick them all.
  - 22 µF: C45783 is the 25 V version. That's better than the 10 V in the schematic, so the mismatch is fine.
- **Check every part in JLC's 3D placement preview.** Rotation conventions differ between KiCad and JLC. Look especially at:
  - **J1/J2 (DF40 sockets):** pin 1 must sit where the silkscreen "1" is.
  - **J10 (USB-C):** the mouth must face the right board edge.
  - **D1 (TVS, SOD-123F):** the cathode band must be on the VBUS side (towards F1, the upper pad). Fixed in the files on 25 Nov 2026 (PLAN D21). Any quote or cart item made from the older upload is wrong and must be re-uploaded.
  - **D2–D4 (LEDs):** cathode to GND.
  - Fix any wrong rotation in JLC's tool; the CPL itself doesn't need to change.
- PCBA type: **Economic**, top side, PCBA qty **2**. Standard needs a board of at least 70 × 70 mm with edge rails, so it doesn't fit this 64 × 40 board.
- **Confirm Parts Placement: Yes.** A JLC engineer shows you the placement before soldering; you have 72 h to approve it.

## 3. Solder yourself (`hand_solder.csv`)
| Part | What |
|---|---|
| J3 | 2×20 male pin header, 2.54 mm (Dock 40-pin) |
| J4, J5, J6 | 2×6 **right-angle female** headers, 2.54 mm (PMOD), mouths facing the bottom edge |
| J7 | 2×4 male header (JTAG, Dock J7 pinout) |
| J8 | 1×3 male header (UART: GND, FPGA RX, FPGA TX) |
| J9 | 1×4 male header (AUX: GND, IOT23B, IOT23A, 3V3) |

You can buy these at Robu or any electronics shop, or add JLC through-hole assembly if you prefer.

## 4. First power-up
Follow PLAN.md step 11:
1. Check for shorts between 5 V, 3V3 and GND **before** fitting the module.
2. Power from USB-C with the module removed, and check that the 5 V reaches the socket pins.
3. Only then fit the Tang Primer 25K.

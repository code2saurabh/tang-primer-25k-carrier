# Sources for carrier v2

Gathered 23 Nov 2026. "Official" means published by Sipeed, Gowin or Hirose.

| File | What it is | Official? | Where it came from | Used for |
|---|---|---|---|---|
| `Tang_Primer_25K_52300_Schematic.pdf` | Core board schematic, PCB rev 52300 (dated May 2023) | Sipeed | Sipeed download station; copy taken from github.com/martinpalsson/kicad-sipeed-tang-core-boards (`docs/`, commit 1ca274e, Feb 2026) | Connector pin → net (p5), net → FPGA ball (p3), module power tree (p4) |
| `Tang_Primer_25K_Specification_V1.0_en.pdf` | Core board specification V1.0 (Sep 2023) | Sipeed | Same repo as above | Official pin tables (p6–9), carrier requirements and 5 V range (p5) |
| `Tang_Primer_25K_Dock_60033_Schematic.pdf` | Sipeed's own carrier (the 25K Dock) | Sipeed | Same repo as above | Proven reference for VCCIO, READY/DONE/RECONFIG, TCK, UART, 5 V input |
| `sipeed_tang_primer_25k.cst` | Sipeed LiteX example constraints | Sipeed | github.com/sipeed/TangPrimer-25K-example (`litex/src/`) | Confirms UART RX = B3, TX = C3, clock = E2 |
| `Hirose_DF40_catalog_2014.pdf` | Hirose DF40 series catalog (2014 edition) | Hirose | Adafruit-hosted copy of the Hirose catalog | Land patterns for DF40C-60DS (receptacle, p4) and DF40C-60DP (header, p10) |
| `ball_map_from_schematic.csv` | Net → ball, extracted by script from schematic p3 | Derived | `tools/build_pinout.py` | Cross-check against the spec tables |
| `tang_primer_25k_b2b_connectors.ods` | Community pin spreadsheet | **Community** | martinpalsson repo | Not used as a source; kept for reference only |

### Added 23 Nov 2026 (downloaded by you)
| File | What it is | Official? | Used for |
|---|---|---|---|
| `sipeed_official/Tang_Primer_25K_Footprint.kicad_pcb` | Sipeed's carrier footprint: 2× `BTB-DF40C-60DS-0.4V(51)` (J1, J2) | Sipeed | **The v2 socket footprint.** Pads are 0.20 × 0.70 mm at 0.4 mm pitch, with rows at ±1.54 mm (3.08 mm apart), matching the Hirose catalog. Connector centres are 13.97 mm apart and both are rotated 180°. |
| `sipeed_official/Tang_Primer_25K_52300_Dimension.pdf` / `.dxf` | Core-board dimension drawing | Sipeed | Outline, mounting holes, keep-out (DXF imports into KiCad) |
| `sipeed_official/Tang_Primer_25K_52300_Step.rar` | Core-board 3D model (STEP) | Sipeed | 3D fit check in KiCad |
| `sipeed_official/Tang_Primer_25K_Dock_60033_Step.rar` | Dock 3D model (STEP) | Sipeed | Reference only (contains the positioned receptacles) |
| `sipeed_official/Tang_Primer_25K_Dock_60033_ibom.html` | Dock interactive BOM | Sipeed | Dock part values and placement reference |
| `gowin/UG714E.pdf` | Gowin UG714, Arora V 25K programming & configuration guide | Gowin | Confirms the RECONFIG_N / READY / DONE / JTAG behaviour |

The two Hirose TraceParts zips (`196000211…df40c-60ds…zip`, `196000225…df40c-60dp…zip`) were moved to the Recycle Bin. They held only CATIA `.3dxml` 3D files, which KiCad can't use, and no 2D drawing. The land pattern is covered by the Sipeed footprint plus the Hirose catalog.

## Gowin configuration pins: CONFIRMED in `gowin/UG714E.pdf` p18–19, p41, p47
UG714 says: RECONFIG_N is an input with an internal weak pull-up, and one low pulse triggers reconfiguration. READY and DONE are pulled up. READY must not be pulled down during power-on and configuration. DONE goes high after a successful configuration and stays low while RECONFIG_N or READY is low. v1's pull-downs on READY and RECONFIG would have blocked configuration.

### Earlier notes (secondary sources, now superseded by UG714)
- **RECONFIG_N** is active-low and has a pull-up. Pulling it low restarts configuration.
- **READY and DONE** are open-drain outputs with an internal weak pull-up. DONE goes high when configuration succeeds.
- These come from search summaries of Gowin GW5A documents, not the Gowin PDF itself. Sipeed's Dock design is consistent with them: 49.9 k pull-ups on READY/DONE, nothing on RECONFIG.
- To do: download Gowin **UG714** (Arora V 25K programming & configuration guide) from gowinsemi.com, which needs a free login, and confirm.

## Still missing
- Sipeed's official core-board PCB footprint (`dl.sipeed.com/shareURL/TANG/Primer_25K/06_PCB_Lib`) and mechanical drawing (`04_Mechanical_drawing`). The download portal is a JavaScript app, so it needs a browser. Needed in step 7 to fix connector positions and pin-1 orientation.
- The current Hirose drawing for DF40C-60DS-0.4V(51), from hirose.com. The 2014 catalog is very likely still valid, but confirm it.

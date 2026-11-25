"""Tang Primer 25K carrier PCB - electrical specification (single source of truth).

Pinout source: Sipeed Tang_Primer_25K_52300_Schematic.pdf (core board, sheet 5,
J1/J2 connector pages) - decoded pin-by-pin. Where the Specification v1.0 PDF
tables disagreed with the schematic (VDD_5V0 rows, VCCIO0/1 rows), the
SCHEMATIC was taken as authoritative.

Geometry source: community footprint github.com/martinpalsson/
kicad-sipeed-tang-core-boards (tang-primer-25k-core-board.kicad_mod), verified
against the official dimension drawing (mounting holes 19.0 x 14.0 mm grid,
x=+-9.5 y=+-7.0) and cross-checked pin-by-pin against the schematic decode.
Socket row spacing = 2.28 mm (NOT the 2.64 mm in nosuz's DF40C footprint).

Coordinates: carrier origin = module center. Module plugs land exactly on the
mp footprint pad positions:
  J2 (top socket):    odd pins  y=+5.86, even pins y=+8.14, x=-5.8+0.4*k
  J1 (bottom socket): even pins y=-5.86, odd pins  y=-8.14
      (pin 1 and 2 of BOTH connectors are at x=-5.8)
"""

# ---------------------------------------------------------------- net names
P5V = "+5V"
P3V3 = "+3V3"
GND = "GND"
P5V_USB = "+5V_USB"      # VBUS pin of USB-C, before ORing diode
P5V_JST = "+5V_JST"      # JST input, before ORing diode

# ------------------------------------------------------- J2 pin -> net
# kind: GND / P5V / P3V3(VCCIO) / GPIO / JTAG / CFG / NC
J2 = {
    1: (GND, "GND"),
    2: (P3V3, "P3V3"),          # VCCIO2/3
    3: ("IOB4A", "GPIO"),
    4: (P3V3, "P3V3"),          # VCCIO2/3
    5: ("IOB4B", "GPIO"),
    6: ("IOR18A", "GPIO"),
    7: ("IOB26A", "GPIO"),
    8: ("IOR18B", "GPIO"),
    9: ("IOB26B", "GPIO"),
    10: ("IOR20A", "GPIO"),
    11: ("IOB24A", "GPIO"),
    12: ("IOR20B", "GPIO"),
    13: ("RECONFIG", "CFG"),
    14: ("IOR22A", "GPIO"),
    15: ("IOB12B", "GPIO"),
    16: ("IOR22B", "GPIO"),
    17: ("IOB14B", "GPIO"),
    18: ("IOR24A", "GPIO"),
    19: (GND, "GND"),
    20: ("IOR24B", "GPIO"),
    21: ("JTAG_TCK", "JTAG"),
    22: ("IOR31A", "GPIO"),
    23: ("JTAG_TMS", "JTAG"),
    24: ("IOR31B", "GPIO"),
    25: ("JTAG_TDO", "JTAG"),
    26: ("IOR33A", "GPIO"),
    27: ("JTAG_TDI", "JTAG"),
    28: ("IOR33B", "GPIO"),
    29: (GND, "GND"),
    30: ("IOB89A", "GPIO"),
    31: ("M0_D3P", "MIPI"),
    32: ("IOB89B", "GPIO"),
    33: ("M0_D3N", "MIPI"),
    34: ("IOB91A", "GPIO"),
    35: (GND, "GND"),
    36: ("IOB91B", "GPIO"),
    37: ("M0_D2P", "MIPI"),
    38: ("VDD_1V8", "NC_PWR"),   # core board output, unused on carrier
    39: ("M0_D2N", "MIPI"),
    40: ("VDD_1V8", "NC_PWR"),
    41: (GND, "GND"),
    42: ("VDD_2V5", "NC_PWR"),
    43: ("M0_CKP", "MIPI"),
    44: ("VDD_2V5", "NC_PWR"),
    45: ("M0_CKN", "MIPI"),
    46: ("VDD_3V3O", "NC_PWR"),
    47: (GND, "GND"),
    48: ("VDD_3V3O", "NC_PWR"),
    49: ("M0_D1P", "MIPI"),
    50: ("VDD_3V3O", "NC_PWR"),
    51: ("M0_D1N", "MIPI"),
    52: (P5V, "P5V"),
    53: (GND, "GND"),
    54: (P5V, "P5V"),
    55: ("M0_D0P", "MIPI"),
    56: (P5V, "P5V"),
    57: ("M0_D0N", "MIPI"),
    58: (P5V, "P5V"),
    59: (GND, "GND"),
    60: (P5V, "P5V"),
}

# ------------------------------------------------------- J1 pin -> net
J1 = {
    1: (GND, "GND"),
    2: (GND, "GND"),
    3: ("IOT31A", "GPIO"),
    4: ("IOT61A", "GPIO"),
    5: ("IOT31B", "GPIO"),
    6: ("IOT61B", "GPIO"),
    7: ("UART_TX", "UART"),      # IOT56A on core board
    8: ("IOT63A", "GPIO"),
    9: ("UART_RX", "UART"),      # IOT56B
    10: ("IOT63B", "GPIO"),
    11: ("IOT58A", "GPIO"),
    12: ("IOT66A", "GPIO"),
    13: (GND, "GND"),
    14: ("IOT66B", "GPIO"),
    15: ("IOT58B", "GPIO"),
    16: ("IOT68A", "GPIO"),
    17: ("READY", "CFG"),
    18: ("IOT68B", "GPIO"),
    19: ("IOB56A", "GPIO"),
    20: ("IOT72A", "GPIO"),
    21: ("IOB56B", "GPIO"),
    22: ("IOT72B", "GPIO"),
    23: ("IOB60A", "GPIO"),
    24: (P3V3, "P3V3"),          # VCCIO0/1
    25: ("DONE", "CFG"),
    26: (P3V3, "P3V3"),          # VCCIO0/1
    27: (GND, "GND"),
    28: (GND, "GND"),
    29: (P3V3, "P3V3"),          # VCCIO6/7
    30: ("IOT23A", "GPIO"),
    31: (P3V3, "P3V3"),          # VCCIO6/7
    32: ("IOT23B", "GPIO"),
    33: ("IOT1A", "GPIO"),
    34: ("IOT21A", "GPIO"),
    35: ("IOT1B", "GPIO"),
    36: ("IOT21B", "GPIO"),
    37: ("IOT3A", "GPIO"),
    38: ("IOT19A", "GPIO"),
    39: ("IOT3B", "GPIO"),
    40: ("IOT19B", "GPIO"),
    41: ("IOT7A", "GPIO"),
    42: ("IOT15A", "GPIO"),
    43: ("IOT7B", "GPIO"),
    44: ("IOT15B", "GPIO"),
    45: (GND, "GND"),
    46: ("IOT11A", "GPIO"),
    47: ("IOL9A", "GPIO"),
    48: ("IOT11B", "GPIO"),
    49: ("IOL9B", "GPIO"),
    50: (GND, "GND"),
    51: ("IOL5A", "GPIO"),
    52: ("IOL3A", "GPIO"),
    53: ("IOL5B", "GPIO"),
    54: ("IOL3B", "GPIO"),
    55: ("IOL12A", "GPIO"),
    56: ("IOL14A", "GPIO"),
    57: ("IOL12B", "GPIO"),
    58: ("IOL14B", "GPIO"),
    59: (GND, "GND"),
    60: (GND, "GND"),
}

# Socket pad positions (from mp footprint, verified): x = -5.8 + 0.4*k
# where k = index of the pin within its row.  Row assignment:
#   J2: odd pins (1,3,...59) at y=+5.86 ; even (2,4,...60) at y=+8.14
#   J1: even pins (2,4,...60) at y=-5.86 ; odd (1,3,...59) at y=-8.14
def socket_pad_xy(conn, pin):
    if conn == "J2":
        if pin % 2 == 1:
            k = (pin - 1) // 2
            y = 5.86
        else:
            k = pin // 2 - 1
            y = 8.14
    else:
        if pin % 2 == 0:
            k = pin // 2 - 1
            y = -5.86
        else:
            k = (pin - 1) // 2
            y = -8.14
    return (-5.8 + 0.4 * k, y)

# --------------------------------------------------------- header maps
# Each entry: (pin number, net, short silks label)
def gpio_c_map():
    """Top header: bank2/3 GPIO (J2 even 6..36) + 3V3 + GND fillers. 26 pins."""
    nets = [(J2[p][0], _short(J2[p][0])) for p in range(6, 37, 2)]  # 16 GPIO
    pins = [(1, GND, "GND"), (2, GND, "GND")]
    for i, (net, s) in enumerate(nets):
        pins.append((3 + i, net, s))
    pins += [(19, GND, "GND"), (20, P3V3, "3V3"), (21, GND, "GND"),
             (22, P3V3, "3V3"), (23, GND, "GND"), (24, P3V3, "3V3"),
             (25, P3V3, "3V3"), (26, GND, "GND")]
    return pins

def gpio_a_map():
    """Left header: bank5 (J2 odd), bank1 (J1 even), bank0 (J1 odd), READY. 26 pins."""
    nets = ([("IOB4A", "B4A"), ("IOB4B", "B4B"), ("IOB26A", "B26A"),
             ("IOB26B", "B26B"), ("IOB24A", "B24A"), ("IOB12B", "B12B"),
             ("IOB14B", "B14B")]              # bank5 x7
            + [(J1[p][0], _short(J1[p][0])) for p in range(4, 23, 2)]   # bank1 x10
            + [(J1[p][0], _short(J1[p][0])) for p in (3, 5, 7, 9, 11, 15)])  # bank0 x6
    pins = [(i + 1, net, s) for i, (net, s) in enumerate(nets)]  # pins 1..23
    pins += [(24, GND, "GND"), (25, "READY", "RDY"), (26, GND, "GND")]
    return pins

def gpio_b_map():
    """Right header: bank7 + bank6, exactly 26 signals, no fillers."""
    nets = [(J1[p][0], _short(J1[p][0])) for p in range(30, 49, 2)]    # bank7 even
    nets += [(J1[p][0], _short(J1[p][0])) for p in (33, 35, 37, 39, 41, 43)]  # bank7 odd
    nets += [(J1[p][0], _short(J1[p][0])) for p in (52, 54, 56, 58)]   # bank6 even
    nets += [(J1[p][0], _short(J1[p][0])) for p in (47, 49, 51, 53, 55, 57)]  # bank6 odd
    return [(i + 1, net, s) for i, (net, s) in enumerate(nets)]

def _short(net):
    """Short silks name: IOT61A -> T61A, IOR18A -> R18A, IOB4A -> B4A, IOL3A -> L3A."""
    if net.startswith("IOT"):
        return "T" + net[3:]
    if net.startswith("IOR"):
        return "R" + net[3:]
    if net.startswith("IOL"):
        return "L" + net[3:]
    if net.startswith("IOB"):
        return "B" + net[3:]
    return net

JTAG_MAP = [(1, "JTAG_TCK", "TCK"), (2, GND, "GND"), (3, "JTAG_TDO", "TDO"),
            (4, P3V3, "3V3"), (5, "JTAG_TMS", "TMS"), (6, "NC", "NC"),
            (7, "NC", "NC"), (8, "NC", "NC"), (9, "JTAG_TDI", "TDI"),
            (10, GND, "GND")]
UART_MAP = [(1, P3V3, "3V3"), (2, "UART_TX", "TX"), (3, "UART_RX", "RX"),
            (4, GND, "GND")]

# --------------------------------------------------------- placements
BOARD = {"cx": 0.0, "cy": 0.0, "w": 72.0, "h": 50.0, "corner_r": 2.0}

PLACE = {
    "GPIO_C": {"ref": "J3", "origin": (15.24, 16.9), "rot": 90, "fp": "PinHeader_2x13_P2.54mm_Vertical"},
    "GPIO_A": {"ref": "J4", "origin": (-25.4, -15.24), "rot": 0, "fp": "PinHeader_2x13_P2.54mm_Vertical"},
    "GPIO_B": {"ref": "J5", "origin": (24.13, -15.24), "rot": 0, "fp": "PinHeader_2x13_P2.54mm_Vertical"},
    "JTAG":   {"ref": "J6", "origin": (-27.94, -18.36), "rot": -90, "fp": "PinHeader_2x05_P2.54mm_Vertical"},
    "UART":   {"ref": "J7", "origin": (-12.7, -20.9), "rot": 90, "fp": "PinHeader_1x04_P2.54mm_Vertical"},
    "USBC":   {"ref": "J8", "origin": (-24.0, 18.74), "rot": 180, "fp": "USB_C_Receptacle_HRO_TYPE-C-31-M-12"},
    "AMS":    {"ref": "U1", "origin": (-29.7, 10.5), "rot": -90, "fp": "SOT-223-3_TabPin2"},
    "D_USB":  {"ref": "D1", "origin": (-17.6, 19.0), "rot": 90, "fp": "D_SMA"},
    "D_JST":  {"ref": "D2", "origin": (-28.0, -3.0), "rot": 90, "fp": "D_SMA"},
    "JST":    {"ref": "J9", "origin": (-31.4, -8.5), "rot": 0, "fp": "JST_XH_B2B-XH-AM_1x02_P2.50mm_Vertical"},
    "SW_RE":  {"ref": "SW1", "origin": (-26.5, -21.5), "rot": 0, "fp": "SW_PUSH_6mm"},
    "LED_PWR": {"ref": "D3", "origin": (17.5, 13.8), "rot": 90, "fp": "LED_0603_1608Metric"},
    "LED_DONE": {"ref": "D4", "origin": (7.5, -15.0), "rot": 0, "fp": "LED_0603_1608Metric"},
}

# discrete resistor/capacitor placements: (ref, value, footprint, x, y, rot)
RESISTS = [
    ("R1", "5.1k", "R_0603_1608Metric", -22.75, 17.8, 0),   # CC1 pulldown
    ("R2", "5.1k", "R_0603_1608Metric", -25.25, 17.8, 0),   # CC2 pulldown
    ("R3", "10k",  "R_0603_1608Metric", -32.0, -14.5, 90),  # TCK pulldown
    ("R4", "10k",  "R_0603_1608Metric", -29.0, -14.5, 90),  # TMS pullup
    ("R5", "10k",  "R_0603_1608Metric", -30.3, -17.3, 90),  # TDI pullup
    ("R6", "10k",  "R_0603_1608Metric", -32.0, -17.3, 90),  # READY pulldown
    ("R7", "10k",  "R_0603_1608Metric", -13.4, -13.6, 90),  # RECONFIG pulldown
    ("R8", "1k",   "R_0603_1608Metric", 7.5, -12.2, 90),    # DONE LED series
    ("R9", "1k",   "R_0603_1608Metric", 17.5, 17.0, -90),   # PWR LED series
]
CAPS = [
    ("C1", "10u", "C_0805_2012Metric", -34.0, 8.6, 0),      # AMS in
    ("C2", "10u", "C_0805_2012Metric", -29.9, 17.2, 90),    # AMS out
    ("C3", "100n", "C_0603_1608Metric", -34.0, 6.4, 0),
    ("C4", "100n", "C_0603_1608Metric", -30.2, 20.6, 90),
]

# module mounting holes (under module holes, tied to GND): x=+-9.5 y=+-7.0
MOD_HOLES = [(x, y) for x in (-9.5, 9.5) for y in (-7.0, 7.0)]
# board corner mounting holes M2.5 (NPTH)
CORNER_HOLES = [(-32.5, -22.5), (32.5, -22.5), (-32.5, 22.5), (32.5, 22.5)]

# net classes: (name, width, clearance)
CLASS_SIG = ("sig", 0.2, 0.15)
CLASS_PWR5 = ("pwr5", 0.5, 0.15)
CLASS_PWR3 = ("pwr3", 0.45, 0.15)

# hand-routed power: list of (net, width, [(x, y, layer)]) polylines.
# layer: 'F' or 'B'; layer change inside a polyline = via at that point.
POWER_PATHS = [
    # 3V3 main trunk: AMS VOUT (upper tab) -> via -> B.Cu corridor (left of
    # GPIO field) -> riser between GND columns -> above-field corridor ->
    # PWR LED branch.  GPIO_C 3V3 pins fed from above/below between GND cols.
    (P3V3, 0.45, [(-29.7, 13.65, 'F'), (-29.9, 14.6, 'B'), (-29.9, 18.17, 'B'),
                  (-16.3, 18.17, 'B')]),
    # GPIO_C pin 25 (3V3, row1) from corridor end
    (P3V3, 0.45, [(-16.51, 18.17, 'B'), (-15.24, 16.9, 'B')]),
    # riser up between GND columns, then above-field corridor to the right
    (P3V3, 0.45, [(-13.97, 18.17, 'B'), (-13.97, 21.3, 'B')]),
    (P3V3, 0.45, [(-13.97, 21.3, 'B'), (19.0, 21.3, 'B')]),
    # GPIO_C pin 24 (3V3, row2, x=-12.7) drop between GND columns
    (P3V3, 0.45, [(-13.97, 21.3, 'B'), (-13.97, 19.44, 'B'), (-12.7, 19.44, 'B')]),
    # GPIO_C pin 22 (3V3, row2, x=-10.16)
    (P3V3, 0.45, [(-8.89, 21.3, 'B'), (-8.89, 19.44, 'B'), (-10.16, 19.44, 'B')]),
    # GPIO_C pin 20 (3V3, row2, x=-7.62)
    (P3V3, 0.45, [(-6.35, 21.3, 'B'), (-6.35, 19.44, 'B'), (-7.62, 19.44, 'B')]),
    # PWR LED resistor feed: via down at x=17.5 to R9 pad 1
    (P3V3, 0.45, [(17.5, 21.3, 'B'), (17.5, 16.21, 'F')]),
    # link the two AMS VOUT tabs on F.Cu, then bottom trunk
    (P3V3, 0.45, [(-29.7, 13.65, 'F'), (-29.7, 7.35, 'F')]),
    (P3V3, 0.45, [(-29.7, 7.35, 'F'), (-29.7, 5.5, 'B'), (-29.7, -19.6, 'B')]),
    (P3V3, 0.45, [(-29.7, -19.6, 'B'), (-16.0, -19.6, 'B')]),
    # JTAG Vref: via -> JTAG pin 4
    (P3V3, 0.45, [(-24.1, -19.6, 'B'), (-24.1, -19.3, 'F'), (-25.4, -20.9, 'F')]),
    # UART 3V3: via -> UART pin 1
    (P3V3, 0.45, [(-16.0, -19.6, 'B'), (-16.0, -20.9, 'F'), (-12.7, -20.9, 'F')]),
    # TMS pullup feed (R4 pad 2)
    (P3V3, 0.45, [(-29.85, -15.29, 'B'), (-29.0, -15.29, 'F')]),
    # TDI pullup feed (R5 pad 2)
    (P3V3, 0.45, [(-29.85, -18.09, 'B'), (-30.3, -18.09, 'F')]),
    # SW1 pad2 feed: leg east extension + north spine + west branch
    (P3V3, 0.45, [(-11.0, -19.6, 'B'), (6.5, -19.6, 'B')]),
    (P3V3, 0.45, [(6.5, -19.6, 'B'), (6.5, -1.6, 'B'), (6.5, -1.4, 'F'),
                  (6.5, -1.5, 'F')]),
    (P3V3, 0.45, [(-14.5, 11.5, 'F'), (-14.5, 10.65, 'F')]),
    (P3V3, 0.45, [(-26.5, -19.6, 'B'), (-26.5, -17.0, 'B')]),
    # VCCIO0/1 (J1 24/26, inner row) -> east side x=+6.5 -> top corridor
    (P3V3, 0.45, [(-1.0, -3.9, 'F'), (-1.0, -1.5, 'F'), (6.5, -1.5, 'F'),
                  (6.5, 11.5, 'F'), (-16.4, 11.5, 'F'), (-16.4, 18.17, 'F'),
                  (-16.4, 18.17, 'B')]),
    (P3V3, 0.45, [(-0.6, -4.6, 'F'), (-0.6, -2.2, 'F'), (-1.0, -2.2, 'F')]),
    # VCCIO6/7 (J1 29/31, outer row) -> B.Cu down x=-0.2 -> west y=-15.6
    (P3V3, 0.45, [(-0.2, -9.6, 'B'), (-0.2, -15.6, 'B'), (-29.7, -15.6, 'B')]),
    (P3V3, 0.45, [(0.2, -9.6, 'B'), (0.2, -10.0, 'B'), (-0.2, -10.0, 'B')]),
    # VCCIO2/3 (J2 2/4, outer row) -> up over the socket -> top corridor
    (P3V3, 0.45, [(-5.8, 9.6, 'F'), (-5.8, 11.5, 'F'), (-16.4, 11.5, 'F'),
                  (-16.4, 18.17, 'F'), (-16.4, 18.17, 'B')]),
    (P3V3, 0.45, [(-5.4, 10.3, 'F'), (-5.4, 12.4, 'F'), (-19.0, 12.4, 'F'),
                  (-19.0, 18.17, 'F'), (-19.0, 18.17, 'B')]),
]

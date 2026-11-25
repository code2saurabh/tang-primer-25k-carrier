"""Decode Sipeed's Dock interactive BOM into ../sources/sipeed_official/dock_layout.json.

Keeps the board outline and, for each footprint, its pads (position, size, type, pin-1 flag).
These are the Dock's real PCB coordinates (KiCad frame, mm). gen_pcb.py copies the Dock's
mechanical layout (module sockets, 40-pin, PMODs, JTAG, USB-C, mounting holes) from them.

Run with system Python:  pip install lzstring  ;  python extract_dock_layout.py
"""
import json, re
from pathlib import Path

import lzstring

SRC = Path(__file__).resolve().parent.parent / "sources" / "sipeed_official"
html = (SRC / "Tang_Primer_25K_Dock_60033_ibom.html").read_text(encoding="utf-8")
b64 = re.search(r'var pcbdata = JSON\.parse\(LZString\.decompressFromBase64\("([^"]+)"\)\)', html).group(1)
d = json.loads(lzstring.LZString().decompressFromBase64(b64))
out = {
    "source": "Tang_Primer_25K_Dock_60033_ibom.html (" + d["metadata"]["date"] + ")",
    "edges": d["edges"],
    "edges_bbox": d["edges_bbox"],
    "footprints": {
        f["ref"]: {"layer": f["layer"], "center": f["bbox"]["pos"], "angle": f["bbox"]["angle"],
                   "pads": [{k: p[k] for k in ("pos", "size", "angle", "shape", "type", "layers", "pin1", "drillsize")
                             if k in p} for p in f["pads"]]}
        for f in d["footprints"]},
}
(SRC / "dock_layout.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("wrote dock_layout.json:", len(out["footprints"]), "footprints; board bbox", d["edges_bbox"])

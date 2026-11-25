"""Post-route cleanup driven only by KiCad's own DRC report (PLAN step 9).

  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" cleanup_pcb.py
Repeats up to 8 rounds:
  * hole_to_hole: move the via that is not part of the fixed fan-out/stitching (router via) straight
    away from its neighbour by the missing distance + 0.03 mm, dragging attached track ends along.
  * via_dangling / track_dangling: delete exactly the items DRC names (fan-out vias the router did
    not need, router stubs).
After each round DRC runs again; if the number of unconnected items or errors goes up, the round is
undone and cleanup stops. Saves the board with zones refilled.
"""
import json, math, re, shutil, subprocess, sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
K = HERE.parent / "kicad"
PCB = K / "carrier_v2.kicad_pcb"
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
REPORT = K / "routing" / "cleanup_drc.json"
mm = pcbnew.FromMM


def drc():
    subprocess.run([CLI, "pcb", "drc", "--severity-all", "--refill-zones", "--format", "json", "-o", str(REPORT),
                    str(PCB)], capture_output=True)
    j = json.loads(REPORT.read_text(encoding="utf-8"))
    v = j["violations"]
    errors = sum(1 for x in v if x["severity"] == "error")
    return j, v, len(j["unconnected_items"]), errors


def P(v):
    return (pcbnew.ToMM(v.x), pcbnew.ToMM(v.y))


def near(a, b, tol=0.006):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def in_socket_area(p):
    """Fan-out region around the DF40 sockets (Dock coordinates)."""
    return 125.8 < p[0] < 138.8 and (73.8 < p[1] < 80.6 or 87.8 < p[1] < 94.6)


def one_round(viol):
    board = pcbnew.LoadBoard(str(PCB))
    items = list(board.GetTracks())
    vias = [t for t in items if t.GetClass() == "PCB_VIA"]
    tracks = [t for t in items if t.GetClass() == "PCB_TRACK"]
    doomed, moved = [], 0
    for x in viol:
        it = x["items"]
        if x["type"] == "via_dangling":
            pos = (it[0]["pos"]["x"], it[0]["pos"]["y"])
            doomed += [v for v in vias if near(P(v.GetStart()), pos)]
        elif x["type"] == "track_dangling":
            m = re.match(r"Track \[(.*)\] on (\S+), length ([\d.]+) mm", it[0]["description"])
            net, layer, length = m.group(1), m.group(2), float(m.group(3))
            pos = (it[0]["pos"]["x"], it[0]["pos"]["y"])
            doomed += [t for t in tracks if t.GetNetname() == net and board.GetLayerName(t.GetLayer()) == layer
                       and abs(pcbnew.ToMM(t.GetLength()) - length) < 0.001
                       and (near(P(t.GetStart()), pos, 0.02) or near(P(t.GetEnd()), pos, 0.02))]
        elif x["type"] == "hole_to_hole":
            pts = [(i["pos"]["x"], i["pos"]["y"]) for i in it[:2]]
            pair = [next((v for v in vias if near(P(v.GetStart()), q)), None) for q in pts]
            if None in pair:
                continue
            if x.get("_delete"):                    # drop a GND stitch via (not a socket fan-out via)
                for v in pair:
                    if v.GetNetname() == "GND" and v.IsLocked() and not in_socket_area(P(v.GetStart())):
                        doomed.append(v)
                        doomed += [t for t in tracks if t.IsLocked() and
                                   (near(P(t.GetStart()), P(v.GetStart())) or near(P(t.GetEnd()), P(v.GetStart())))]
                        break
                continue
            mover, other = pair[x.get("_mover", 0)], pair[1 - x.get("_mover", 0)]
            if in_socket_area(P(mover.GetStart())) and mover.IsLocked():
                continue                                   # never move socket fan-out vias
            actual = float(re.search(r"actual ([\d.]+) mm", x["description"]).group(1))
            d = 0.5 - actual + 0.03
            mx, my = P(mover.GetStart()); ox, oy = P(other.GetStart())
            L = math.hypot(mx - ox, my - oy) or 1
            nx, ny = mx + (mx - ox) / L * d, my + (my - oy) / L * d
            new = pcbnew.VECTOR2I(mm(nx), mm(ny))
            for t in tracks:
                if t.GetNetname() == mover.GetNetname():
                    if near(P(t.GetStart()), (mx, my)):
                        t.SetStart(new)
                    if near(P(t.GetEnd()), (mx, my)):
                        t.SetEnd(new)
            mover.SetPosition(new)
            moved += 1
    seen = set()
    for it in doomed:
        if id(it) not in seen:
            seen.add(id(it))
            board.Remove(it)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(PCB), board)
    return len(seen), moved


if len(sys.argv) > 2 and sys.argv[1] == "--round":
    print("ROUND %d %d" % one_round(json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))))
    raise SystemExit
j, viol, unconn, errors = drc()
backup = K / "routing" / "before_cleanup.kicad_pcb"
shutil.copyfile(PCB, backup)
print(f"start: {unconn} unconnected, {errors} errors, "
      f"{sum(x['type'] in ('via_dangling', 'track_dangling') for x in viol)} dangling, "
      f"{sum(x['type'] == 'hole_to_hole' for x in viol)} hole-to-hole")


def attempt(todo, label):
    """Apply one batch; keep it only if unconnected items and errors do not go up."""
    global j, viol, unconn, errors
    snapshot = K / "routing" / "round.kicad_pcb"
    shutil.copyfile(PCB, snapshot)
    # KiCad's Python can't load a board twice in one process: run the edit in a child process
    job = K / "routing" / "round_todo.json"
    job.write_text(json.dumps(todo), encoding="utf-8")
    r = subprocess.run([sys.executable, __file__, "--round", str(job)], capture_output=True, text=True)
    removed, moved = map(int, re.search(r"ROUND (\d+) (\d+)", r.stdout).groups())
    j2, viol2, unconn2, errors2 = drc()
    if unconn2 > unconn or errors2 > errors:
        shutil.copyfile(snapshot, PCB)
        print(f"{label}: would cause {unconn2} unconnected / {errors2} errors - undone")
        return False
    print(f"{label}: removed {removed}, moved {moved} -> {unconn2} unconnected, {errors2} errors")
    j, viol, unconn, errors = j2, viol2, unconn2, errors2
    return removed or moved


# phase A: dangling items one at a time (a 'dangling' stub can still be the only link for a pad)
for rnd in range(1, 4):
    batch = [x for x in viol if x["type"] in ("via_dangling", "track_dangling")]
    if not batch:
        break
    progress = False
    for x in batch:
        progress |= bool(attempt([x], "delete " + x["items"][0]["description"]))
    if not progress:
        break
# phase B: each hole-to-hole pair: move one via, else the other, else drop a GND stitch via
for x in [x for x in viol if x["type"] == "hole_to_hole"]:
    for opt in ({"_mover": 0}, {"_mover": 1}, {"_delete": True}):
        if attempt([dict(x, **opt)], f"hole-to-hole {opt} " + " / ".join(i["description"] for i in x["items"][:2])):
            break
left = {t: sum(v["type"] == t for v in viol) for t in ("via_dangling", "track_dangling", "hole_to_hole")}
print(f"end: {unconn} unconnected, {errors} errors, left {left}")

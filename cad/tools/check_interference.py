"""
조립 상태 전수 간섭 검사 (#59).

모든 프린트 부품과 구매품(외형 모형)을 조립 위치에 놓고, 모든 부품 쌍이 겹치는지 OpenSCAD로 계산한다.
1) 부품마다 STL을 뽑아 경계 상자(bounding box)를 구한다.
2) 경계 상자가 겹치는 쌍만 intersection()을 렌더해 겹친 부피를 잰다.
3) 겹친 부피가 ALLOW_CM3보다 크면 "간섭"으로 보고한다. 의도된 접촉(예: 기둥이 소켓에 꽂힘)은
   CAD에 여유(tube_clearance)가 있어 겹침 0이어야 정상이다.

베인은 중립(0°)과 하드스톱 각도(±vane_stop_deg) 세 상태를 따로 검사한다.
구매품 치수는 PURCHASED 블록에 출처와 함께 둔다. 실측이 나오면 그 값을 고친다.

실행: python cad/tools/check_interference.py        (약 5-15분)
표준 라이브러리만 쓴다. OpenSCAD 찾는 방법은 export_print_parts.py와 같다.
"""
import argparse
import itertools
import math
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_print_parts import MARKER, SCAD, check_stl, find_openscad, load_stl  # noqa: E402

ALLOW_CM3 = 0.001

# 구매품 외형 모형. 출처: MG90S 공식(TowerPro) 22.8 x 12.2 x 28.5 mm, 4S 1300 mAh 2026-10-17 실측,
# FS-iA6B 제조사 47 x 26.2 x 15 mm, Hobbywing 3A UBEC 43 x 17 x 7 mm, EDF 하우징 실측 외경 72 / 길이 92 mm.
PURCHASED = """
module p_edf() { cylinder(h = edf_body_len, r = edf_housing_od / 2, $fn = 96); }
module p_columns() { columns(); }
module p_legs() { legs(); }
module p_spars() { for (i = [0 : n_vanes - 1]) rotate([0, 0, i * 360 / n_vanes + az_vane])
    translate([vane_inner_r, 0, vane_pivot_z]) rotate([0, 90, 0]) cylinder(h = vane_spar_len, r = vane_spar_d / 2, $fn = 16); }
module p_servos() { servo_blocks(); } // CAD의 현재 서보 외형 가정을 그대로 사용한다. MG90S 실측 아님(#219).
module p_battery() {   // 실측 최대 치수(2026-10-17): 길이 76, 폭 34, 두께 33
    rotate([0, 0, 90]) translate([shelf_r_inner + 34 / 2 + 4, 0, shelf_top_z + 33 / 2]) cube([34, batt_l_max, 33], center = true); }
module p_esc() { mock_esc(); }
module p_perfboard() { rotate([0, 0, 270]) translate([avi_board_r, 0, avi_board_z]) cube([50, 70, 1.6], center = true); }
module p_receiver() { rotate([0, 0, 270]) translate([avi_board_r + receiver_xy[0], receiver_xy[1], avi_board_z + 0.8 + receiver_bottom_gap + receiver_size[2]/2]) cube(receiver_size, center = true); }
module p_teensy() { rotate([0, 0, 270]) translate([avi_board_r + avi_teensy_xy[0], avi_teensy_xy[1], avi_board_z + 4]) cube([18, 36, 5], center=true); }
module p_imu() { rotate([0, 0, 270]) translate([avi_board_r + avi_imu_xy[0], avi_imu_xy[1], avi_board_z + 3]) cube([16, 18, 3], center=true); }
module p_ubec() { rotate([0, 0, 270]) translate([ubec_r, 0, shelf_top_z - shelf_t - 3.5 - 0.1]) cube([17, 43, 7], center = true); }
module p_bail() { bail(); }
module p_ballast() {   // 질량표와 같은 강철 고리 2개. 재료 밀도·구멍을 포함해 높이를 계산한다.
    rotate([0, 0, 270]) for (sy = [-ballast_y, ballast_y])
        translate([ballast_x, sy, shelf_top_z - shelf_t - ballast_h - 0.1]) difference() {
            cylinder(h = ballast_h, d = ballast_od, $fn = 48);
            translate([0,0,-1]) cylinder(h = ballast_h + 2, d = ballast_hole_d, $fn = 32);
        }
}
"""

PARTS = {
    # 프린트 부품 (export_print_parts.py와 같은 형상, 조립 위치)
    "top_plate": "translate([0,0,top_plate_bot_z]) top_plate();",
    "vane_ring": "vane_ring();",
    "vanes_0": "vanes(0);",
    "edf_clamp": "edf_clamp();",
    "battery_shelf": "rotate([0,0,90]) equip_shelf_battery();",
    "avionics_shelf": "rotate([0,0,270]) equip_shelf_avionics();",
    "esc_bracket": "rotate([0,0,270]) esc_bracket();",
    "couplers": "for (i=[0:n_vanes-1]) rotate([0,0,i*360/n_vanes + az_vane]) translate([servo_mount_r + 1.5, 0, vane_pivot_z]) vane_coupler();",
    "foot_pads": "foot_pads();",
    # 구매품
    "edf": "p_edf();", "columns": "p_columns();", "legs": "p_legs();", "spars": "p_spars();",
    "servos": "p_servos();", "battery": "p_battery();", "esc": "p_esc();", "perfboard": "p_perfboard();",
    "receiver": "p_receiver();", "teensy": "p_teensy();", "imu": "p_imu();", "ubec": "p_ubec();", "bail": "p_bail();", "ballast": "p_ballast();",
}
# 베인 양끝 편향도 중립 베인을 제외한 모든 고정 부품과 비교한다.
DEFLECTED = {"vanes_+stop": "vanes(vane_stop_deg);", "vanes_-stop": "vanes(-vane_stop_deg);"}
DEFLECT_PAIRS = tuple(name for name in PARTS if name != "vanes_0")
# 의도된 접촉(같은 축의 끼움): 여유를 두고 설계했으므로 겹침이 있으면 그대로 보고한다. 제외 쌍 없음.


def bbox(stl):
    pts = [p for t in load_stl(stl) for p in t]
    if not pts:
        return None
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def overlap(a, b, eps=0):
    return all(a[0][i] < b[1][i] - eps and b[0][i] < a[1][i] - eps for i in range(3))


CONTACT_WARNINGS = {
    "WARNING: Object may not be a valid 2-manifold and may need repair!",
    "EXPORT-WARNING: Exported object may not be a valid 2-manifold and may need repair",
}


def planar_components(triangles):
    """Return axis-aligned, zero-thickness connected components, or None.

    Exact exported coordinates only: no epsilon and no cancellation of signed volumes.
    A mixture of a flat contact and a real solid must fail this classification.
    Other orientations remain unclassified and fail closed if OpenSCAD warns.
    """
    if not triangles or any(not math.isfinite(x) for t in triangles for p in t for x in p):
        return None
    neighbours = {}
    for i, t in enumerate(triangles):
        for p in t:
            neighbours.setdefault(p, []).append(i)
    remaining = set(range(len(triangles)))
    planes = []
    while remaining:
        todo = [remaining.pop()]
        points = set()
        while todo:
            for p in triangles[todo.pop()]:
                points.add(p)
                for i in neighbours[p]:
                    if i in remaining:
                        remaining.remove(i)
                        todo.append(i)
        axes = [i for i in range(3) if len({p[i] for p in points}) == 1]
        if not axes:
            return None
        planes.append((axes[0], next(iter(points))[axes[0]]))
    return planes



class EmptyIntersection(ValueError):
    """A successful STL export without triangles needs a separate contact proof."""


def off_contact(path, result):
    """Only accept zero-thickness OFF components; never infer contact from empty STL."""
    problems = [line.strip() for line in result.stderr.splitlines()
                if line.strip().startswith(("ERROR:", "WARNING:", "EXPORT-WARNING:"))]
    if result.returncode or any(line not in CONTACT_WARNINGS for line in problems):
        raise ValueError("OFF contact render failed: " + result.stderr[-1500:])
    tokens = path.read_text(encoding="utf-8").split()
    if not tokens or tokens.pop(0) != "OFF":
        raise ValueError("invalid OFF header")
    try:
        nv, nf, _ = (int(tokens.pop(0)) for _ in range(3))
        if nv < 3 or nf < 1:
            raise ValueError("empty OFF")
        vertices = [tuple(float(tokens.pop(0)) for _ in range(3)) for _ in range(nv)]
        triangles, used = [], set()
        for _ in range(nf):
            n = int(tokens.pop(0))
            if n < 3:
                raise ValueError("invalid OFF face")
            ids = [int(tokens.pop(0)) for _ in range(n)]
            if any(i < 0 or i >= nv for i in ids):
                raise ValueError("invalid OFF index")
            used.update(ids)
            triangles.extend((vertices[ids[0]], vertices[ids[i]], vertices[ids[i+1]])
                             for i in range(1, n-1))
        if tokens or used != set(range(nv)):
            raise ValueError("unclassified OFF data")
    except (IndexError, TypeError) as error:
        raise ValueError("truncated OFF") from error
    planes = planar_components(triangles)
    if not planes:
        raise ValueError("empty STL has non-planar OFF geometry; inspect manually")
    return planes


def classify_render(stl, result, intersection=False):
    """Validate a real OpenSCAD result; never accept a warning as an empty result."""
    lines = [line.strip() for line in result.stderr.splitlines()]
    problems = [line for line in lines if line.startswith(("ERROR:", "WARNING:", "EXPORT-WARNING:"))]
    empty = "Current top level object is empty" in [line.rstrip(".") for line in lines]
    if empty:
        if intersection and not problems and result.returncode in (0, 1):
            return "empty", None
        raise ValueError("empty part or failed render: " + result.stderr[-1500:])
    if result.returncode != 0 or not stl.is_file():
        raise ValueError(f"render failed (exit {result.returncode}): " + result.stderr[-1500:])
    triangles = load_stl(stl)
    if not triangles:
        if intersection and not problems:
            raise EmptyIntersection("empty STL requires OFF contact proof")
        raise ValueError("empty STL")
    if any(not math.isfinite(x) for t in triangles for p in t for x in p):
        raise ValueError("non-finite STL")
    # Only intersections of already validated solids can be classified as contacts.
    planes = planar_components(triangles) if intersection else None
    if intersection and planes and all(line in CONTACT_WARNINGS for line in problems):
        return "contact", planes
    if problems:
        raise ValueError("OpenSCAD error or unclassified warning: " + "\n".join(problems))
    size, volume, open_edges = check_stl(stl)
    if size is None or open_edges or volume <= 0 or not math.isfinite(volume):
        raise ValueError(f"invalid solid STL: open_edges={open_edges}, volume={volume}")
    return "solid", volume


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", help="Keep SCAD, STL and render logs for inspection (use a fresh directory)")
    args = parser.parse_args()
    exe = find_openscad()
    head = SCAD.read_text(encoding="utf-8").split(MARKER)[0] + PURCHASED
    parts = dict(PARTS, **DEFLECTED)
    with tempfile.TemporaryDirectory() as temporary:
        tmp = Path(args.out).resolve() if args.out else Path(temporary)
        if args.out:
            tmp.mkdir(parents=True, exist_ok=False)

        def render(name, body, intersection=False):
            scad = tmp / f"{name}.scad"
            scad.write_text(head + "\n" + body + "\n", encoding="utf-8")
            stl = tmp / f"{name}.stl"
            r = subprocess.run([exe, "--render", "-o", str(stl), str(scad)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            (tmp / f"{name}.log").write_text(r.stderr, encoding="utf-8")
            try:
                try:
                    kind, value = classify_render(stl, r, intersection)
                except EmptyIntersection:
                    off = tmp / f"{name}.off"
                    proof = subprocess.run([exe, "--render", "-o", str(off), str(scad)],
                                           capture_output=True, text=True, encoding="utf-8", errors="replace")
                    (tmp / f"{name}.off.log").write_text(proof.stderr, encoding="utf-8")
                    kind, value = "contact", off_contact(off, proof)
            except (ValueError, OSError) as error:
                sys.exit(f"{name}: {error}")
            print(f"{name}: {kind}" + (f" {value}" if kind == "contact" else ""), flush=True)
            return stl, kind, value

        boxes = {}
        for n, body in parts.items():
            stl, _, _ = render(n, body)
            boxes[n] = (stl, bbox(stl))
        pairs = [(a, b) for a, b in itertools.combinations(PARTS, 2)]
        pairs += [(v, o) for v in DEFLECTED for o in DEFLECT_PAIRS]
        hits, checked, contacts = [], 0, 0
        for a, b in pairs:
            if not overlap(boxes[a][1], boxes[b][1]):
                continue
            checked += 1
            body = f"intersection() {{ {parts[a]} {parts[b]} }}"
            stl, kind, volume = render(f"x_{a}_{b}".replace("+", "p").replace("-", "m"), body, True)
            if kind == "contact":
                contacts += 1
            if kind != "solid":
                continue
            if volume > ALLOW_CM3:
                bb = bbox(stl)
                hits.append((a, b, volume, bb))
        print(f"부품 {len(parts)}개, 쌍 {len(pairs)}개 중 경계 상자가 겹친 {checked}쌍을 정밀 검사")
        print(f"두께 없는 축 정렬 면·선 접촉 {contacts}쌍, 부피 허용값 {ALLOW_CM3} cm3")
        if not hits:
            print("간섭 없음")
            return
        print(f"간섭 {len(hits)}건")
        print("| 부품 A | 부품 B | 겹친 부피 (cm3) | 겹친 위치 x / y / z 범위 (mm) |")
        print("|---|---|---|---|")
        for a, b, vol, bb in hits:
            rng = " / ".join(f"{bb[0][i]:.1f}~{bb[1][i]:.1f}" for i in range(3))
            print(f"| {a} | {b} | {vol:.3f} | {rng} |")
        sys.exit(1)


if __name__ == "__main__":
    main()

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
import itertools
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_print_parts import MARKER, SCAD, check_stl, find_openscad, load_stl  # noqa: E402

ALLOW_CM3 = 0.001

# 구매품 외형 모형. 출처: MG90S 공식(TowerPro) 22.8 x 12.2 x 28.5 mm, 4S 850 mAh 리스팅 60 x 30 x 30.5 mm,
# FS-iA6B 매뉴얼 47 x 26.2 x 15 mm, Hobbywing 3A UBEC 43 x 17 x 7 mm, EDF 하우징 실측 외경 72 / 길이 92 mm.
PURCHASED = """
module p_edf() { cylinder(h = edf_body_len, r = edf_housing_od / 2, $fn = 96); }
module p_columns() { columns(); }
module p_legs() { legs(); }
module p_spars() { for (i = [0 : n_vanes - 1]) rotate([0, 0, i * 360 / n_vanes + az_vane])
    translate([vane_inner_r, 0, vane_pivot_z]) rotate([0, 90, 0]) cylinder(h = vane_spar_len, r = vane_spar_d / 2, $fn = 16); }
module p_servos() {   // MG90S 공식 치수: 접선 22.8, 수직 12.2, 반경 방향 몸통 깊이 22.8(귀 아래 F 18.5 + 귀), 출력축 쪽 위로 혼 보스
    for (i = [0 : n_vanes - 1]) rotate([0, 0, i * 360 / n_vanes + az_vane])
        translate([servo_plate_r + servo_boss_t, -6, vane_pivot_z - 12.2 / 2]) cube([22.8, 22.8, 12.2]);
}
module p_battery() {   // 실측 최대 치수(2026-10-17): 길이 76, 폭 34, 두께 33
    rotate([0, 0, 90]) translate([shelf_r_inner + 34 / 2 + 4, 0, shelf_top_z + 33 / 2]) cube([34, batt_l_max, 33], center = true); }
module p_esc() { mock_esc(); }
module p_perfboard() { rotate([0, 0, 270]) translate([shelf_r_inner + 25, 0, shelf_top_z + 12]) cube([50, 70, 1.6], center = true); }
module p_receiver() { rotate([0, 0, 270]) translate([shelf_r_inner + 25 - 14, 22, shelf_top_z + 12 + 0.8 + 7.5]) cube([26.2, 47, 15], center = true); }
module p_ubec() { rotate([0, 0, 270]) translate([shelf_r_inner + 30, 0, shelf_top_z - shelf_t - 3.5 - 0.1]) cube([17, 43, 7], center = true); }
module p_bail() { bail(); }
module p_ballast() {   // 최대 무게추: 와셔 묶음 Ø12 x 높이 18, 선반 판 아래
    rotate([0, 0, 270]) for (sy = [-ballast_y, ballast_y]) translate([ballast_x, sy, shelf_top_z - shelf_t - 18.1]) cylinder(h = 18, r = 6, $fn = 24); }
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
    "receiver": "p_receiver();", "ubec": "p_ubec();", "bail": "p_bail();", "ballast": "p_ballast();",
}
# 베인을 하드스톱까지 꺾은 상태는 베인링·스파·커플러와만 따로 본다
DEFLECTED = {"vanes_+stop": "vanes(vane_stop_deg);", "vanes_-stop": "vanes(-vane_stop_deg);"}
DEFLECT_PAIRS = ("vane_ring", "spars", "couplers", "edf")
# 의도된 접촉(같은 축의 끼움): 여유를 두고 설계했으므로 겹침이 있으면 그대로 보고한다. 제외 쌍 없음.


def bbox(stl):
    pts = [p for t in load_stl(stl) for p in t]
    if not pts:
        return None
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def overlap(a, b, eps=0.01):
    return all(a[0][i] < b[1][i] - eps and b[0][i] < a[1][i] - eps for i in range(3))


def main():
    exe = find_openscad()
    head = SCAD.read_text(encoding="utf-8").split(MARKER)[0] + PURCHASED
    parts = dict(PARTS, **DEFLECTED)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        def render(name, body):
            scad = tmp / f"{name}.scad"
            scad.write_text(head + "\n" + body + "\n", encoding="utf-8")
            stl = tmp / f"{name}.stl"
            r = subprocess.run([exe, "--render", "-o", str(stl), str(scad)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            # 정상적인 빈 결과(교집합 없음)와 렌더 실패를 구분한다(#61 리뷰). 빈 결과는 OpenSCAD가
            # "top level object is empty"를 출력한다. 그 밖에 STL이 없거나 exit가 0이 아니면 실패다.
            empty = "empty" in r.stderr.lower()
            if not empty and (r.returncode != 0 or not stl.exists()):
                sys.exit(f"{name}: OpenSCAD 렌더 실패 (exit {r.returncode})\n{r.stderr[-1500:]}")
            return stl, empty, r

        boxes = {}
        for n, body in parts.items():
            stl, empty, r = render(n, body)
            if empty:
                sys.exit(f"{n}: 부품 형상이 비어 있다\n{r.stderr[-1500:]}")
            boxes[n] = (stl, bbox(stl))
        pairs = [(a, b) for a, b in itertools.combinations(PARTS, 2)]
        pairs += [(v, o) for v in DEFLECTED for o in DEFLECT_PAIRS]
        hits, checked = [], 0
        for a, b in pairs:
            if not overlap(boxes[a][1], boxes[b][1]):
                continue
            checked += 1
            body = f"intersection() {{ {parts[a]} {parts[b]} }}"
            stl, empty, r = render(f"x_{a}_{b}".replace("+", "p").replace("-", "m"), body)
            if empty:
                continue
            size, vol, _ = check_stl(stl)
            if size is not None and vol > ALLOW_CM3:
                bb = bbox(stl)
                hits.append((a, b, vol, bb))
        print(f"부품 {len(parts)}개, 쌍 {len(pairs)}개 중 경계 상자가 겹친 {checked}쌍을 정밀 검사")
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

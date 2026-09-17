// ============================================================================
//  베인 링 — EDF 배기면 아래 고정, 베인 4 + 서보 4(방사) + 다리 4소켓
//            + 중앙 언더슬렁 구속 소켓(M6 ×3, CG 조절)
//  재료: PETG, 벽 4, 인필 40%. 베인 하우징 세워서 출력.
//  출발점: printables.com/model/803977 (64mm EDF 3축 TVC) 개조 가능.
//  ⚠ 형상 스케치. vane_sweep_check()로 ±15° 간섭 확인 후 확정.
// ============================================================================
include <params.scad>
$fn = 120;

module vane() {
    difference() {
        union() {
            hull() {
                cylinder(h = vane_span, d = vane_thick);
                translate([vane_chord - vane_thick/2, 0, 0])
                    cylinder(h = vane_span, d = vane_thick*0.7);
            }
            translate([vane_chord*0.30, 0, -6]) cylinder(h = 7, d = 6);
            translate([vane_chord*0.30, 0, vane_span-1]) cylinder(h = 7, d = 6);
        }
        translate([vane_chord*0.45, 0, -1]) cylinder(h = vane_span + 2, d = vane_spar_d);
        translate([vane_chord*0.30, 0, -8]) cylinder(h = vane_span + 18, d = vane_pivot_d);
        translate([vane_chord*0.30 + 4, 0, -4]) rotate([90,0,0])
            cylinder(h = 8, d = pushrod_d + 0.3, center = true);
    }
}

module vane_ring() {
    difference() {
        union() {
            cylinder(h = vane_ring_h, d = vane_ring_od);
            // 기둥 소켓 보스 (윗면)
            for (i = [0:col_n-1])
                rotate([0,0, i*360/col_n + 45])
                    translate([col_pcd/2, 0, 0])
                        cylinder(h = vane_ring_h + col_socket_depth, d = col_rod_d + 6);
            // 중앙 언더슬렁 소켓 러그 (아랫면)
            translate([0,0,-12]) cylinder(h = 12, d = 20);
        }
        // 배기 통과
        translate([0,0,-1]) cylinder(h = vane_ring_h + 2, d = edf_exit_od + 4);

        // 기둥 구멍
        for (i = [0:col_n-1])
            rotate([0,0, i*360/col_n + 45])
                translate([col_pcd/2, 0, -1])
                    cylinder(h = vane_ring_h + col_socket_depth + 2, d = col_rod_d);

        // 베인 피벗 부싱 + 서보 포켓 + 링키지 (4)
        for (i = [0:vane_n-1])
            rotate([0,0, i*360/vane_n]) {
                translate([vane_ring_od/2 - 3, 0, vane_ring_h/2])
                    rotate([0,90,0]) cylinder(h = 14, d = vane_pivot_d + 0.2, center = true);
                translate([vane_ring_od/2 + 4, 0, vane_ring_h/2])
                    cube([servo_body_l, servo_body_w + 1, servo_body_h + 1], center = true);
                for (s = [-1,1])
                    translate([vane_ring_od/2 + 4 + s*servo_lug_span/2, 0, vane_ring_h/2])
                        cylinder(h = 30, d = servo_lug_screw_d, center = true);
            }

        // 다리 소켓 (4, 베인과 45° 엇갈림, 스플레이)
        for (i = [0:leg_n-1])
            rotate([0,0, i*360/leg_n + 45])
                translate([vane_ring_od/2 - 2, 0, vane_ring_h/2])
                    rotate([0, 90 - leg_splay, 0])
                        cylinder(h = 26, d = leg_rod_d, center = true);

        // 중앙 언더슬렁 M6 ×3 (CG 조절)
        for (k = [0:uslung_holes_n-1])
            translate([(k - 1)*uslung_hole_pitch, 0, -13])
                cylinder(h = 16, d = uslung_screw_d);
    }
}

module vane_sweep_check() {
    vane_ring();
    for (i = [0:vane_n-1])
        rotate([0,0, i*360/vane_n])
            translate([vane_ring_od/2 - vane_root_from_axis, 0, vane_ring_h/2 - vane_span/2])
                for (a = [-vane_deflect_max : 5 : vane_deflect_max])
                    rotate([0,0,a]) color("red", 0.25) vane();
}

vane_ring();
// vane();
// vane_sweep_check();

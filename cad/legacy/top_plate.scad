// ============================================================================
//  상판 — 64mm EDF 마운트 + 기둥 4소켓 + 베일 2점 + 흡기 개방
//  재료: PETG (모터 폐열 ~50°C), 벽 4라인, 인필 40%. 합판 4mm 대체 가능.
//  ⚠ 형상 스케치. EDF 끼움부만 20mm 링으로 먼저 시험 출력(제작 순서 2).
// ============================================================================
include <params.scad>
$fn = 96;

module top_plate() {
    difference() {
        union() {
            cylinder(h = top_plate_t, d = top_plate_d);
            // EDF 하우징 감싸는 숏칼라 (아래로 돌출)
            translate([0,0,-16])
                cylinder(h = 16 + 0.01, d = edf_housing_od + 2*3);
            // 기둥 소켓 보스
            for (i = [0:col_n-1])
                rotate([0,0, i*360/col_n + 45])
                    translate([col_pcd/2, 0, -col_socket_depth])
                        cylinder(h = col_socket_depth + top_plate_t, d = col_rod_d + 6);
        }
        // EDF 하우징 관통
        translate([0,0,-17]) cylinder(h = 40, d = edf_housing_od + 0.6);
        // EDF 마운트 볼트
        for (i = [0:edf_mount_n-1])
            rotate([0,0, i*360/edf_mount_n])
                translate([edf_mount_pcd/2, 0, -12])
                    cylinder(h = 30, d = edf_mount_screw_d);
        // 기둥 구멍 + 고정 M3 (측면)
        for (i = [0:col_n-1])
            rotate([0,0, i*360/col_n + 45]) {
                translate([col_pcd/2, 0, -col_socket_depth - 1])
                    cylinder(h = col_socket_depth + top_plate_t + 2, d = col_rod_d);
                translate([col_pcd/2, 0, -col_socket_depth/2])
                    rotate([0,90,0]) cylinder(h = 20, d = 3.2, center = true);
            }
        // 베일 2점 (Ø3 스틸봉)
        for (s = [-1,1])
            translate([s*bail_width/2, 0, -1])
                cylinder(h = top_plate_t + 2, d = bail_rod_d);
        // 흡기 개방 — EDF 립 안쪽은 팬이 채우므로, 칼라 외곽~기둥 사이 링을 비움
        difference() {
            translate([0,0,-1]) cylinder(h = top_plate_t + 2, d = top_plate_d - 14);
            translate([0,0,-2]) cylinder(h = top_plate_t + 4, d = edf_housing_od + 10);
            // 스포크 4개 남김
            for (i = [0:3])
                rotate([0,0, i*90])
                    translate([-6, -top_plate_d, -2]) cube([12, 2*top_plate_d, top_plate_t + 4]);
        }
    }
}

top_plate();

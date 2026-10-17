// COSMOS 호퍼 완성 모습 렌더 (발표·설명용, #59)
// ⚠️ 프린트 대상이 아니다. 발주 STL은 cad/tools/export_print_parts.py 로 만든다.
// 프린트 부품 형상은 hopper_params.scad 의 모듈을 그대로 쓰고, 구매품(EDF, 배터리, 전자부품)과
// 배선을 외형만 더한다. 구매품 치수 중 실측이 아닌 것은 공칭값이다(아래 주석).
//
// 렌더 예:
//   openscad -o cad/renders/showcase.png --imgsize=1600,1200 --camera=600,-720,420,0,0,30 --projection=p cad/showcase.scad
include <hopper_params.scad>
render_mode = "showcase";   // hopper_params.scad 의 preview/print 분기를 끈다

$fn = 64;

// ---------- 색 ----------
C_PRINT  = [0.93, 0.93, 0.95];   // PETG 흰색
C_CF     = [0.12, 0.12, 0.13];   // 탄소관
C_EDF    = [0.10, 0.10, 0.11];
C_LIP    = [0.75, 0.76, 0.78];
C_FAN    = [0.20, 0.45, 0.85];
C_ACCENT = [0.95, 0.35, 0.10];

// ---------- 배선 도우미: 점 목록을 따라 굵기 d의 선을 그린다 ----------
module wire(pts, d = 1.6, c = "red") {
    color(c) for (i = [0 : len(pts) - 2])
        hull() { translate(pts[i]) sphere(d = d, $fn = 12); translate(pts[i + 1]) sphere(d = d, $fn = 12); }
}
function rot(p, a) = [p[0] * cos(a) - p[1] * sin(a), p[0] * sin(a) + p[1] * cos(a), p[2]];

// ---------- EDF 본체 (구매품, 하우징 외경 72 실측 / 내부는 공칭 외형) ----------
module edf_unit() {
    r_out = edf_housing_od / 2;
    r_in  = r_out - 2.5;
    // 하우징
    color(C_EDF) difference() {
        cylinder(h = edf_body_len, r = r_out);
        translate([0, 0, -1]) cylinder(h = edf_body_len + 2, r = r_in);
    }
    // 흡입구 립 (둥근 테)
    color(C_LIP) translate([0, 0, edf_body_len])
        rotate_extrude($fn = 96) translate([r_out - 1.2, 0]) circle(r = 2.6, $fn = 24);
    // 팬 로터: 스피너 + 블레이드 12장
    translate([0, 0, edf_body_len - 18]) {
        color(C_LIP) cylinder(h = 14, r1 = 13, r2 = 6);
        color(C_FAN) for (i = [0 : 11]) rotate([0, 0, i * 30])
            translate([13, 0, 4]) rotate([28, 0, 0]) cube([r_in - 14, 9, 1.2]);
    }
    // 모터 캔과 고정자 날개 8장
    color([0.3, 0.3, 0.32]) translate([0, 0, 18]) cylinder(h = 50, r = 14);
    color(C_EDF) for (i = [0 : 7]) rotate([0, 0, i * 45 + 11])
        translate([14, -0.8, 22]) cube([r_in - 14, 1.6, 26]);
    // 꼬리 원뿔
    color([0.3, 0.3, 0.32]) translate([0, 0, 2]) cylinder(h = 16, r1 = 7, r2 = 14);
}

// ---------- 전자부품 (구매품 외형) ----------
avi_r = shelf_r_inner + 25;          // mock_avionics 와 같은 위치
avi_z = shelf_top_z + 12;

module avionics_detail() {
    rotate([0, 0, 270]) translate([avi_r, 0, avi_z]) {
        // 만능기판 50x70
        color([0.15, 0.45, 0.20]) cube([50, 70, 1.6], center = true);
        for (x = [-22 : 2.54 : 22], y = [-32 : 2.54 : 32])
            color([0.75, 0.65, 0.35]) translate([x, y, 0.8]) cylinder(h = 0.2, r = 0.5, $fn = 6);
        // Teensy 4.0 (35x17 실측) + 핀헤더 + USB
        translate([0, -8, 4]) {
            color([0.10, 0.40, 0.18]) cube([17, 35, 1.6], center = true);
            color("black") for (s = [-1, 1]) translate([s * 7.6, 0, -2.2]) cube([2.4, 33, 2.6], center = true);
            color(C_LIP) translate([0, 18.5, 1.6]) cube([8, 6, 3], center = true);
            color([0.15, 0.15, 0.15]) translate([0, 2, 1.4]) cube([10, 10, 1.2], center = true);
        }
        // BNO085 모듈 (GY 보라색 기판)
        translate([10, 22, 3]) {
            color([0.45, 0.20, 0.60]) cube([16, 18, 1.6], center = true);
            color("black") translate([0, 0, 1.3]) cube([5, 5, 1], center = true);
        }
        // 수신기
        translate([-14, 22, 6]) {
            color([0.15, 0.15, 0.15]) cube([14, 22, 10], center = true);
            wire([[0, 11, 3], [0, 30, 20], [-6, 45, 40]], 0.8, "black");
            wire([[2, 11, 3], [4, 32, 18], [12, 44, 36]], 0.8, "black");
        }
        // Teensy ↔ IMU 점퍼선 (SPI 7가닥, 색은 설명용)
        for (k = [0 : 6]) {
            cs = ["orange", "yellow", "green", "blue", "purple", "white", "gray"];
            wire([[-6.4 + k * 2.54 * 0.5, 9, 3.5], [-2 + k, 14, 9], [4 + k, 19, 6], [6 + k, 21, 4]], 0.9, cs[k]);
        }
    }
}

module battery_detail() {
    rotate([0, 0, 90]) translate([shelf_r_inner + batt_w / 2 + 4, 0, shelf_top_z + batt_h / 2]) {
        color([0.20, 0.20, 0.22]) cube([batt_w, batt_l, batt_h], center = true);
        color(C_ACCENT) cube([batt_w + 0.4, 22, batt_h + 0.4], center = true);       // 라벨 띠
        color([0.2, 0.2, 0.9]) for (s = [-1, 1]) translate([0, s * 20, 0])          // 벨크로 스트랩
            cube([batt_w + 1.2, 6, batt_h + 1.2], center = true);
        // 주 전원선과 XT60
        wire([[-6, -batt_l / 2, 0], [-6, -batt_l / 2 - 12, 2], [-4, -batt_l / 2 - 22, 4]], 2.6, "red");
        wire([[6, -batt_l / 2, 0], [6, -batt_l / 2 - 12, 2], [4, -batt_l / 2 - 22, 4]], 2.6, "black");
        color([0.95, 0.80, 0.10]) translate([0, -batt_l / 2 - 28, 4]) cube([16, 12, 8], center = true);
        // 밸런스 리드
        for (k = [0 : 4]) wire([[-8 + k * 1.6, batt_l / 2, 4], [-8 + k * 1.6, batt_l / 2 + 10, 8]], 0.7,
                               ["red", "black", "white", "white", "white"][k]);
    }
}

// 킬스위치 (상판 위, 손이 닿는 곳)
module kill_switch() {
    translate([0, 52, top_plate_top_z]) {
        color("red") cube([22, 14, 10], center = false);
        color("black") translate([11, 7, 10]) rotate([20, 0, 0]) cylinder(h = 10, r = 2.5);
    }
}

module esc_detail() {
    rotate([0, 0, 270]) translate([shelf_r_inner + 5 + esc_t / 2, 0, shelf_top_z - shelf_t - 26]) {
        color([0.10, 0.35, 0.80]) cube([esc_t, esc_l, esc_w], center = true);       // 열수축 튜브
        color(C_LIP) translate([-esc_t / 2 - 0.5, 0, 0]) cube([1, esc_l - 6, esc_w - 6], center = true);
        // 모터 3상선 → EDF
        for (k = [-1, 0, 1]) wire([[-esc_t / 2, k * 4, -esc_w / 2],
                                   [-12, k * 4, -esc_w / 2 - 14],
                                   [-(shelf_r_inner + 6) + edf_housing_od / 2 + 2, k * 4, 40]],
                                  1.8, "black");
        // DShot 신호선 → 아비오닉스
        wire([[0, esc_l / 2, esc_w / 2], [6, esc_l / 2 + 6, esc_w / 2 + 18], [19, 0, 38]], 0.9, "white");
    }
}

// 서보선: 서보에서 가장 가까운 기둥(45° 계열)을 타고 올라간 뒤, 흡입구(반경 39) 바깥 원호를 돌아
// 아비오닉스 선반의 배선 슬롯으로 올라간다. 흡입구 위를 가로지르면 선이 팬에 빨려 들어간다.
// 슬롯은 ESC(270° ±21°) 양옆이라 원호가 ESC를 지나지 않는다.
function arc(r, a0, a1, z, n = 12) = [for (k = [0 : n]) rot([r, 0, z], a0 + (a1 - a0) * k / n)];
slot_c = [(wire_slot_x0 + wire_slot_x1) / 2, (wire_slot_y0 + wire_slot_y1) / 2];   // 선반 로컬
slot_r = norm(slot_c);
slot_da = atan2(slot_c[1], slot_c[0]);           // 270°에서 벌어진 각
// 0°·45° 쪽 기둥은 −90°(= 270°) 오른쪽 슬롯으로, 135°·225° 쪽은 왼쪽 슬롯으로 간다
function slot_a(ca) = (ca < 90 || ca > 270) ? -90 + slot_da : 270 - slot_da;
module servo_leads() {
    for (i = [0 : n_vanes - 1]) {
        a = i * 360 / n_vanes + az_vane;
        col_a = (a + 45) % 360;
        ca = col_a > 270 ? col_a - 360 : col_a;       // 315°는 −45°로 보고 −90° 쪽으로 돈다
        ta = slot_a(col_a);
        r_arc = col_mount_r + 5 + i * 1.5;             // 원호를 조금씩 벌려 겹치지 않게
        z1 = shelf_top_z - 22 + i * 3;
        s0 = rot([servo_plate_r + servo_boss_t + servo_body_h, 8, vane_pivot_z + 4], a);
        c0 = rot([r_arc, 0, vane_ring_top_z + 6], ca);
        up0 = rot([slot_r, 0, z1], ta);
        up1 = rot([slot_r, 0, shelf_top_z + 3], ta);
        dst = rot([avi_r - 10, 0, shelf_top_z + 5], 270 + (ta < 0 ? 8 : -8));
        path = concat([s0, (s0 + c0) / 2 + [0, 0, 6], c0], arc(r_arc, ca, ta, z1), [up0, up1, dst]);
        for (k = [0 : 2])
            wire([for (q = path) q + [0, 0, k * 1.0]], 0.9, ["brown", "red", "orange"][k]);
    }
}

// ---------- 조립 ----------
color(C_PRINT) translate([0, 0, top_plate_bot_z]) top_plate();
color(C_CF)    columns();
color(C_PRINT) vane_ring();
color(C_ACCENT) vanes();
color(C_CF)    legs();
color(C_LIP)   bail();
color(C_PRINT) edf_clamp();
color(C_PRINT) rotate([0, 0, 90])  equip_shelf_battery();
color(C_PRINT) rotate([0, 0, 270]) equip_shelf_avionics();
color(C_PRINT) rotate([0, 0, 270]) esc_bracket();
color([0.55, 0.55, 0.58]) for (i = [0 : n_vanes - 1]) rotate([0, 0, i * 360 / n_vanes + az_vane])
    translate([servo_mount_r + 1.5, 0, vane_pivot_z]) vane_coupler();
color([0.15, 0.15, 0.15]) foot_pads();
servo_blocks();
edf_unit();
avionics_detail();
battery_detail();
esc_detail();
servo_leads();
kill_switch();

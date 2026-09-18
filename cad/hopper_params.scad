// ============================================================
// PRJ-01 TVC 착륙 호퍼 — 파라메트릭 스켈레톤 (rev C, 오픈 스탠드오프 프레임)
// 참조: docs/design/00-hopper-master-design.md §4 (좌표계·전체 치수)
//
// 이 파일은 SolidGeek Onshape 포크의 "대안"으로 마스터 설계도가 언급한
// cad/*.scad 경로를 실제로 구현한 것. §4 표의 심볼명을 그대로 변수명으로 썼다.
//
// ⚠️ 지금 값은 전부 "DESIGN(가정)" — 부품 도착 후 캘리퍼스 실측하면
//    아래 "MEASURED — 실측 후 이 값만 바꾸면 됨" 섹션만 고치면 전체 형상이 갱신됨.
// ============================================================

// ---------- MEASURED — 실측 후 이 값만 바꾸면 됨 ----------
// 2026-09-13 실측: 이 EDF는 마운트 볼트 플랜지가 없는 제품으로 확인됨
// (사진 확인 결과 하우징 중심부 4홀은 모터→허브 내부 고정용, 프레임 마운트용 아님)
// → PCD/볼트홀 방식 대신 분할 클램프(collar clamp) 방식으로 설계 변경
edf_housing_od   = 72;   // EDF 하우징 외경 (mm) — 줄자 둘레 22.7cm ÷ π 환산값 (앞쪽 넓은 부분, 클램프 기준)
edf_body_od_min  = 70;   // 참고: 뒤쪽(모터쪽) 둘레 22cm ÷ π 환산값 — 단차 작아 설계상 무시, 클램프가 오차 흡수
edf_has_bolt_flange = false;  // 이 제품엔 볼트 플랜지 없음 → 클램프 마운트로 전환
edf_clamp_gap      = 3;      // 클램프 내경 여유 (실측이 정확하지 않을 수 있어 1.5→3mm로 확대, 슬롯홀과 함께 오차 흡수)
edf_clamp_h        = 12;     // 클램프 밴드 폭(높이, mm)
edf_body_len        = 92;    // EDF 몸통 세로 길이(mm) — 배기면(z=0) ~ 흡입구 립 끝. 실측 9~9.3cm 평균
edf_clamp_z_from_exit = 70;  // 배기면(z=0) 기준 클램프 높이 — 립 근처(72mm 지름 구간)를 잡도록 흡입구 쪽에 가깝게 배치

// ---------- DESIGN — §4 표 값 그대로 (구조 결정 후 바뀌면 여기 수정) ----------
col_len              = 200;  // 기둥 길이(상판~베인링)
top_plate_t          = 4;    // 상판 두께
vane_ring_h          = 28;   // 베인 링 높이
vane_gap_below_exit  = 22;   // EDF 배기면 → 베인 피벗축
foot_below_exit      = 140;  // EDF 배기면 → 발 바닥
H_total              = 350;  // 전체 높이(베일 팁~발), 참고용 — 검증에 사용
foot_circle          = 360;  // 발 원 지름
leg_len              = 210;  // 다리 길이(로드, 참고용 — 실제 배치는 아래서 계산)

vane_chord = 25;   // 베인 시위
vane_span  = 45;   // 베인 스팬
vane_thick = 2.5;  // 베인 두께
n_vanes    = 4;

col_od   = 6;   // D1 기둥 로드 Ø6mm CF 튜브
leg_od   = 6;   // D2 다리 로드 Ø6mm CF 튜브
n_cols   = 4;
n_legs   = 4;

bail_od  = 3;   // D4 상단 베일 Ø3mm 스틸봉

// ---------- 아비오닉스/배터리 트레이 · 서보 · 발 (플레이스홀더 — 표준 부품 규격 기준) ----------
// ⚠️ 이 구간은 실측이 아니라 "표준 부품 공칭 치수"로 넣은 것 — 실측 아니어도 되고,
//    부품 실물 받으면 살짝만 조정하면 됨 (Teensy·MG90S 외형은 규격품이라 거의 안 바뀜)
teensy_l = 36; teensy_w = 18;         // Teensy 4.0 보드 (핀헤더 포함 여유치)
esc_l    = 36; esc_w    = 24;         // AM32 75A ESC 보드
tray_gap_from_top = 53;               // 트레이를 상판에서 얼마나 아래에 다는지 — EDF 몸통 상단(92mm) 위 여유 공간에 배치
tray_t   = 3;

batt_l = 105; batt_w = 34; batt_h = 25;  // 4S 1300mAh 90C 팩 공칭 치수
batt_gap_from_top = 83;                   // EDF 몸통 상단(92mm) 바로 위, 아비오닉스 트레이보다 아래 (CG 트림용, ±10mm 슬라이드 가능)

servo_l = 23; servo_w = 12.2; servo_h = 29;  // MG90S 공칭 치수
foot_pad_d = 16; foot_pad_h = 8;             // D5 EVA/EPP 발 범퍼 (플레이스홀더)

$fn = 48; // 렌더 품질 (렌더 느리면 24로 낮추기)

// ---------- 좌표계 ----------
// z = 0 : EDF 배기면 (§4 기준면). 위로 +z, 아래로 -z.
vane_ring_top_z = -vane_gap_below_exit;                 // 베인링 상단
vane_ring_bot_z = vane_ring_top_z - vane_ring_h;         // 베인링 하단
top_plate_bot_z = vane_ring_top_z + col_len;             // 상판 하단 (기둥이 여기서 베인링까지)
top_plate_top_z = top_plate_bot_z + top_plate_t;
foot_z          = -foot_below_exit;                      // 발 바닥
bail_top_z      = foot_z + H_total;                      // 검증용: 베일 팁

vane_ring_od = edf_housing_od + 24;
vane_ring_id = edf_housing_od + 4;
leg_top_r    = vane_ring_od/2;        // 다리 상단 부착 반경 (베인링에서 시작)
leg_bot_r    = foot_circle/2;         // 다리 하단(발) 반경
// ⚠️ 버그 수정(2026-09-13): col_mount_r가 예전엔 edf_housing_od/2+25로 따로 계산돼서
//    vane_ring_od/2(=leg_top_r)보다 13mm나 커버렸음 → 기둥이 베인링 바깥 허공에서 끝나
//    실제로 안 닿는 상태였음. 기둥도 다리와 같은 반경(링 바깥 표면)에서 시작하도록 통일.
col_mount_r  = leg_top_r;             // 상판 위 기둥 부착 반경 = 베인링 바깥 반경 (다리와 동일선상, 45도만 엇갈림)
edf_clamp_id = edf_housing_od + edf_clamp_gap;  // 클램프 내경 = 실측 외경 + 여유
edf_clamp_z  = edf_clamp_z_from_exit;  // 클램프 높이 — 배기면(z=0) 기준, 실측 몸통 길이(edf_body_len) 안에 들어오는 값
edf_body_top_z = edf_body_len;         // 참고용: EDF 몸통 상단(흡입구 립) z — 검증 echo에 사용
tube_clearance = 0.3;                  // 소켓 구멍 여유 (Ø6mm 탄소관 삽입용, mm)
socket_depth   = 12;                   // 베인링에 뚫는 소켓 구멍 깊이 (mm, 링 높이 28mm 중)

// ---------- 모듈 ----------

module top_plate() {
    // 볼트 플랜지 없는 EDF라 상판엔 흡기 공기 통로용 홀만 뚫음 (마운트는 edf_clamp()가 담당)
    // ⚠️ D1 탄소관(기둥)은 프린트하는 게 아니라 실제 구매품 — 상판엔 관통 소켓 구멍만 뚫고 여기에 접착
    difference() {
        cylinder(h=top_plate_t, r=col_mount_r + 15, center=false);
        // EDF 흡기 통로 홀 — 하우징보다 살짝 크게(공기 흐름 여유, 접촉 없음)
        translate([0,0,-1]) cylinder(h=top_plate_t+2, r=edf_housing_od/2 + 3, center=false);
        // D1 탄소관(기둥) 삽입용 관통 소켓 4개
        for (i=[0:n_cols-1]) {
            a = i*360/n_cols + 45;
            translate([col_mount_r*cos(a), col_mount_r*sin(a), -1])
                cylinder(h=top_plate_t+2, r=col_od/2 + tube_clearance, center=false);
        }
    }
}

module edf_clamp() {
    // 분할 클램프(collar clamp) — 볼트 플랜지 없는 EDF 하우징을 감싸서 고정
    // 반원 두 조각 + 양쪽 조임 탭(볼트 2개로 조여서 실측 오차 흡수)
    tab_w = 10; tab_t = 4; bolt_hole_d = 3.2; slot_len = 4; // M3 조임볼트 + 슬롯 여유(mm)
    tab_l = (col_mount_r - edf_clamp_id/2) + 8; // 탭을 기둥까지 뻗어서 지퍼타이/스크류로 기둥에 고정
    gap = 6; // 반원 사이 벌어진 틈(조임 여유)
    translate([0,0,edf_clamp_z]) {
        for (side = [0, 1]) {
            mirror([0, side, 0])
                difference() {
                    union() {
                        // 반원 밴드 (180도보다 살짝 못 미치게, 틈 확보)
                        rotate_extrude(angle=170, $fn=64)
                            translate([edf_clamp_id/2, 0, 0])
                                square([2.5, edf_clamp_h], center=false);
                        // 양끝 조임 탭
                        rotate([0,0,0])
                            translate([edf_clamp_id/2 - 2, -tab_w/2, 0])
                                cube([tab_l, tab_w, edf_clamp_h]);
                        rotate([0,0,170])
                            translate([edf_clamp_id/2 - 2, -tab_w/2, 0])
                                cube([tab_l, tab_w, edf_clamp_h]);
                    }
                    // 탭 볼트홀 — 원형 대신 슬롯(장공)으로 파서, 실측 오차 있어도 조립 때 옆으로 밀어 맞출 여유를 줌
                    translate([edf_clamp_id/2 + tab_l/2 - 1, 0, -1])
                        hull() {
                            translate([0, -slot_len/2, 0]) cylinder(h=edf_clamp_h+2, r=bolt_hole_d/2, $fn=24);
                            translate([0,  slot_len/2, 0]) cylinder(h=edf_clamp_h+2, r=bolt_hole_d/2, $fn=24);
                        }
                    rotate([0,0,170])
                        translate([edf_clamp_id/2 + tab_l/2 - 1, 0, -1])
                            hull() {
                                translate([0, -slot_len/2, 0]) cylinder(h=edf_clamp_h+2, r=bolt_hole_d/2, $fn=24);
                                translate([0,  slot_len/2, 0]) cylinder(h=edf_clamp_h+2, r=bolt_hole_d/2, $fn=24);
                            }
                }
        }
    }
}

module columns() {
    for (i=[0:n_cols-1]) {
        a = i*360/n_cols + 45; // 사각 배치
        translate([col_mount_r*cos(a), col_mount_r*sin(a), vane_ring_top_z])
            cylinder(h=col_len, r=col_od/2, center=false);
    }
}

module vane_ring() {
    // ⚠️ D1(기둥)·D2(다리) 탄소관도 프린트하는 게 아니라 실제 구매품 — 링 위/아래 면에
    //    소켓 구멍만 뚫어서 기둥은 위에서, 다리는 아래에서 꽂아 접착하는 구조로 변경
    translate([0,0,vane_ring_bot_z])
        difference() {
            cylinder(h=vane_ring_h, r=vane_ring_od/2, center=false);
            translate([0,0,-1]) cylinder(h=vane_ring_h+2, r=vane_ring_id/2, center=false);
            // 기둥(위쪽) 소켓 — 링 윗면에서 아래로 뚫음
            for (i=[0:n_cols-1]) {
                a = i*360/n_cols + 45;
                translate([col_mount_r*cos(a), col_mount_r*sin(a), vane_ring_h - socket_depth])
                    cylinder(h=socket_depth+1, r=col_od/2 + tube_clearance, center=false);
            }
            // 다리(아래쪽) 소켓 — 링 아랫면에서 위로 뚫음
            // +90 오프셋 = 기둥(+45)과 45도 엇갈리게 = 진짜 스태거 배치 (원래 주석엔 있었지만 실제 코드는 기둥과 같은 각도였던 버그 수정)
            for (i=[0:n_legs-1]) {
                a = i*360/n_legs + 90;
                translate([leg_top_r*cos(a), leg_top_r*sin(a), -1])
                    cylinder(h=socket_depth+1, r=leg_od/2 + tube_clearance, center=false);
            }
        }
}

module vanes() {
    // 정지 상태(중립) 베인 4개 @90도 — 실제 서보 구동각은 조립 후 반영
    ring_mid_z = (vane_ring_top_z + vane_ring_bot_z)/2;
    for (i=[0:n_vanes-1]) {
        a = i*360/n_vanes;
        translate([vane_ring_od/2*cos(a), vane_ring_od/2*sin(a), ring_mid_z - vane_span/2])
            rotate([0,0,a])
                cube([vane_thick, vane_chord, vane_span], center=true);
    }
}

module legs() {
    for (i=[0:n_legs-1]) {
        a = i*360/n_legs + 90; // 기둥(+45)과 45도 엇갈리게 배치(다리 사이로 배기 흐름 확보)
        p1 = [leg_top_r*cos(a), leg_top_r*sin(a), vane_ring_bot_z];
        p2 = [leg_bot_r*cos(a), leg_bot_r*sin(a), foot_z];
        hull() {
            translate(p1) sphere(r=leg_od/2);
            translate(p2) sphere(r=leg_od/2);
        }
    }
}

module bail() {
    // 상판 위 손잡이(베일) — 세로로 선 아치형. 정확한 굽힘 형상은 실물 벤딩으로 결정
    bail_r = col_mount_r * 0.6;
    translate([0,0,top_plate_top_z])
        rotate([90,0,0])
            rotate_extrude(angle=180, $fn=64)
                translate([bail_r,0,0]) circle(r=bail_od/2);
}

// 아래 두 개(_plate)가 실제로 프린트되는 부분 — Teensy/ESC/배터리 실물은 나중에 스트랩/케이블타이로 고정
module avionics_tray_plate() {
    z = top_plate_bot_z - tray_gap_from_top;
    tray_w = max(teensy_w, esc_w) + 10;
    tray_l = teensy_l + esc_l + 15;
    translate([0,0,z])
        cube([tray_l, tray_w, tray_t], center=true);
}
module battery_tray_plate() {
    z = top_plate_bot_z - batt_gap_from_top;
    translate([0,0,z])
        cube([batt_l+6, batt_w+6, tray_t], center=true);
}

// 아래 두 개는 조립 미리보기용 — Teensy/ESC/배터리 실물 자리를 색블록으로 표시만 함 (프린트 대상 아님!)
module avionics_tray() {
    avionics_tray_plate();
    z = top_plate_bot_z - tray_gap_from_top;
    translate([-esc_l/2-2, 0, z+tray_t/2+2])
        color("green") cube([teensy_l, teensy_w, 4], center=true);
    translate([teensy_l/2+2, 0, z+tray_t/2+3])
        color("darkslategray") cube([esc_l, esc_w, 6], center=true);
}
module battery_tray() {
    battery_tray_plate();
    z = top_plate_bot_z - batt_gap_from_top;
    translate([0,0,z+tray_t/2+batt_h/2])
        color("dimgray") cube([batt_l, batt_w, batt_h], center=true);
}

module servo_blocks() {
    // MG90S 서보 4개 — 베인 링에 장착, 각 베인 옆에 나란히
    ring_mid_z = (vane_ring_top_z + vane_ring_bot_z)/2;
    for (i=[0:n_vanes-1]) {
        a = i*360/n_vanes;
        translate([(vane_ring_od/2+servo_w/2)*cos(a), (vane_ring_od/2+servo_w/2)*sin(a), ring_mid_z])
            rotate([0,0,a])
                color("black") cube([servo_l, servo_w, servo_h], center=true);
    }
}

module foot_pads() {
    // D5 EVA/EPP 발 범퍼 (플레이스홀더 원통)
    for (i=[0:n_legs-1]) {
        a = i*360/n_legs + 90; // legs()와 동일 각도로 맞춤
        translate([leg_bot_r*cos(a), leg_bot_r*sin(a), foot_z - foot_pad_h/2])
            color("darkorange") cylinder(h=foot_pad_h, r=foot_pad_d/2, center=true);
    }
}

// ---------- 조립 ----------
// render_mode = "preview": 조립 미리보기 (기둥/다리를 실봉으로, 부품을 색블록으로 시각화 — 실제 프린트 대상 아님)
// render_mode = "print"  : 진짜 프린트해서 외주 넣을 대상만 (상판·베인링엔 D1/D2 탄소관용 소켓 구멍만 뚫려있음)
//                          커맨드라인에서 -D 'render_mode="print"' 로 오버라이드해서 별도 export
render_mode = "preview";

if (render_mode == "preview") {
    color("silver") translate([0,0,top_plate_bot_z]) top_plate();
    color("gold")   columns();          // ⚠️ 실제로는 프린트 안 함 — D1 탄소관(구매품) 자리 표시용
    color("silver") vane_ring();
    color("orangered") vanes();
    color("gold")   legs();             // ⚠️ 실제로는 프린트 안 함 — D2 탄소관(구매품) 자리 표시용
    color("gray")   bail();             // ⚠️ 실제로는 프린트 안 함 — 철사 벤딩으로 별도 제작
    color("crimson") edf_clamp();
    avionics_tray();                    // 트레이판 + Teensy/ESC 색블록(실물 아님, 자리 표시용)
    battery_tray();                     // 트레이판 + 배터리 색블록(실물 아님, 자리 표시용)
    servo_blocks();                     // ⚠️ 실제로는 프린트 안 함 — MG90S 서보 실물 자리 표시용
    foot_pads();
} else {
    // 진짜 프린트 파트만: 상판(소켓홀 포함) · 베인링(소켓홀 포함) · 베인 4개 · EDF 클램프 2조각 · 발범퍼 4개 · 트레이 평판 2개
    translate([0,0,top_plate_bot_z]) top_plate();
    vane_ring();
    vanes();
    edf_clamp();
    avionics_tray_plate();
    battery_tray_plate();
    foot_pads();
}

// ---------- 검증 출력 (콘솔에서 확인) ----------
echo(str("EDF 몸통 범위 = 0 ~ ", edf_body_top_z, " mm (배기면 기준) — 클램프 위치 z=", edf_clamp_z, "mm는 ", (edf_clamp_z>=0 && edf_clamp_z<=edf_body_top_z) ? "범위 안 (정상)" : "!! 범위 밖 — 몸통을 못 감쌈, 값 재조정 필요 !!"));
echo(str("배터리 트레이 z=", top_plate_bot_z - batt_gap_from_top, "mm, 아비오닉스 트레이 z=", top_plate_bot_z - tray_gap_from_top, "mm — 둘 다 몸통 상단(", edf_body_top_z, "mm) 위에 있어야 안 겹침"));
echo(str("상판 상단 z = ", top_plate_top_z, " mm"));
echo(str("베인 피벗 z = ", (vane_ring_top_z+vane_ring_bot_z)/2, " mm (EDF 배기면 기준 -", vane_gap_below_exit, "mm 근사)"));
echo(str("발 바닥 z = ", foot_z, " mm"));
echo(str("상판top~발bottom 실제 전고 = ", top_plate_top_z - foot_z, " mm  (설계 H_total 참고값 = ", H_total, " mm)"));

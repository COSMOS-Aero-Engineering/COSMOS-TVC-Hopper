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
// 2026-09-18 재측정(2차): 줄자 둘레 22.6cm(앞) / 21.9~22cm(뒤) → 지름 환산 71.9mm / 69.9mm.
//   1차 측정(22.7cm/22cm → 72mm/70mm)과 오차 0.5mm 이내로 일치 — 값 그대로 유지, 재확인만 기록.
edf_housing_od   = 72;   // EDF 하우징 외경 (mm) — 줄자 둘레 22.6~22.7cm ÷ π 환산값 (앞쪽 넓은 부분, 클램프 기준). 2회 측정 일치
edf_body_od_min  = 70;   // 참고: 뒤쪽(모터쪽) 둘레 21.9~22cm ÷ π 환산값 — 단차 작아 설계상 무시, 클램프가 오차 흡수. 2회 측정 일치
edf_has_bolt_flange = false;  // 이 제품엔 볼트 플랜지 없음 → 클램프 마운트로 전환
edf_clamp_gap      = 3;      // 클램프 내경 여유 (실측이 정확하지 않을 수 있어 1.5→3mm로 확대, 슬롯홀과 함께 오차 흡수)
edf_clamp_h        = 12;     // 클램프 밴드 폭(높이, mm)
edf_body_len        = 92;    // EDF 몸통 세로 길이(mm) — 배기면(z=0) ~ 흡입구 립 끝. 실측 9~9.3cm 평균
edf_clamp_z_from_exit = 70;  // 배기면(z=0) 기준 클램프 높이 — 립 근처(72mm 지름 구간)를 잡도록 흡입구 쪽에 가깝게 배치

// ---------- DESIGN — §4 표 값 그대로 (구조 결정 후 바뀌면 여기 수정) ----------
col_len              = 212;  // 기둥 길이(상판~베인링). 2026-10-16 200→212(#59): 4S 팩 두께(850 mAh 30.5 mm, 1300 mAh 28-35 mm)가 상판 아래 28 mm에 안 들어갔다
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

// ---------- 장비 선반(아비오닉스·배터리) · 서보 · 발 ----------
// rev C.1 (2026-09-17): 원점 중심 "트레이" 2개를 폐기하고 **기둥에 걸치는 장비 선반**으로 교체.
//   폐기 이유 3가지 — ①흡기 통로(상판 흡기홀 ~ EDF 립 사이) 한가운데를 막고 있었음
//   ②판 반길이(55.5) > 기둥 반경위치(33.9)라 기둥 4개를 관통 ③어디에도 고정되지 않는 떠 있는 판.
//   상세 근거·치수 출처: docs/design/01-avionics-integration-final.md §7
// ⚠️ 부품 공칭 치수는 실측 아님 — 실물 받으면 여기만 조정(규격품이라 거의 안 바뀜).
// 과거 2026-09-19 기록(cad/measurements.md):
//   - Teensy 35×17mm — 공식 스펙(36×18mm)과 거의 일치. 1차 "세로 10mm"는 측정 오류였던 걸로 확인.
//   - 배터리 63.5×32.5×15mm는 현재 4S 팩의 치수로 쓰지 않는다.
//     현재 배터리는 아래 2026-10-17 실측값을 쓴다(#221).
teensy_l = 35; teensy_w = 17;             // Teensy 4.0 실측(최종) — 미리보기 전용, 프린트 파츠엔 안 쓰임
esc_l    = 36; esc_w    = 24; esc_t = 8;  // ESC 보드 (브래킷 크기 산정용) — 아직 미측정, 공칭치수
batt_l = 73; batt_w = 34; batt_h = 31; // 실측 4S 1300 mAh(2026-10-17): 73+-3 x 33-34 x 31+-2 mm, 159.5 g
batt_h_max = 33;   // 실측 두께 최대(31 + 2)
batt_strap_t = 2;  // 벨크로 스트랩 두께
batt_l_max = 76;   // 실측 길이 73 +- 3 mm (2026-10-17)
batt_shelf_y_half = 42;   // 배터리 선반 반폭. 턱 두께 3이라 턱 사이 = 2*42 - 6 = 78 mm
// 옆 무게중심 트림용 무게추(#59). 배터리(+Y) 한쪽 배치라 CG가 +Y로 약 9 mm 치우친다(cad/cg 계산).
// 아비오닉스 선반(−Y) 아래 M5 구멍 2개에 트림 부품을 고정한다. 현재 72 g 강철 고리는 설계 후보이며 실측 전이다.
ballast_x = 89;    // 선반 로컬 x(반경 방향)
ballast_y = 10;    // 로컬 |y|
ballast_hole_d = 5.5;
// 설계 후보의 재료·형상·질량을 같은 식으로 묶는다. 구매·실측 완료값이 아니다.
ballast_target_g = 72;
ballast_density_g_cm3 = 7.85; // 강철 가정
ballast_od = 18;
ballast_h = ballast_target_g * 1000 / (2 * ballast_density_g_cm3 * PI * (pow(ballast_od/2,2) - pow(ballast_hole_d/2,2)));

shelf_top_z   = 150;   // 선반 윗면 z (배기면 기준). 상판 하면(178)까지 28mm, EDF 립(92)에서 58mm 위
shelf_t       = 3;     // 선반 판 두께
shelf_rib_h   = 5;     // 가장자리 리브 높이 (캔틸레버 처짐 방지)
shelf_r_inner = 42;    // 선반 안쪽 경계 반경 — 흡기 스트림튜브(Ø78=r39) + 여유 3mm. 이보다 안쪽엔 재료 없음
// 전자부 배치 후보(#222): 공칭 외형이며 실물 체결·배선 여유는 #219에서 확인한다.
avi_board_r = shelf_r_inner + 25;
avi_board_z = shelf_top_z + 12;
avi_stack_t = 4; // 만능기판+헤더+레벨시프터의 보수적 조립 높이. 실측 전 간섭 외피(#222).
avi_module_gap = 0.5; // 위 조립 외피와 수신기·Teensy·IMU 사이 설계 간격
avi_teensy_xy = [-10, -12];
avi_imu_xy = [-10, 22];
receiver_xy = [13, 0];
receiver_size = [26.2, 47, 15]; // FS-iA6B 제조사 공칭치수(https://www.flysky-cn.com/ia6b-canshu), 현재 구매품 일치 여부 확인 필요
receiver_bottom_gap = avi_module_gap; // 기판 조립 외피 위 설계 간격, 실물 스페이서/절연 고정 확인 필요
ubec_r = shelf_r_inner + 28; // 바깥면 r78.5; 무게추 안쪽 r80와 1.5 mm 간격
saddle_h      = 16;    // 기둥을 감싸는 새들 링 높이
saddle_wall   = 2.4;   // #224: 완전한 원주를 유지하며 흡기 파임과 0.3 mm 떨어지는 벽
saddle_tie_offset = 12; // #224: 기둥 중심에서 바깥쪽 타이 슬롯 중심까지 거리
tie_slot_w    = 3.2;   // 케이블타이 슬롯 폭 (2.5mm 타이 기준)
tie_slot_l    = 8;     // 케이블타이 슬롯 길이
wire_slot_x0 = 62; wire_slot_x1 = 74;      // 아비오닉스 선반 배선 통로(로컬 x, 반경 방향). ESC 플랜지(x ≤ 60) 바깥
wire_slot_y0 = 8;  wire_slot_y1 = 18;      // 로컬 |y|. 만능기판 인서트 보스(x 45.7-54.3, 83.8-92.4)와 겹치지 않는 자리

// 만능기판(5x7cm) 장착 — 01-avionics-integration-final.md §5.1 의 확공 좌표와 1:1
perf_hole_dx  = 53.34; // C2↔C23 = 21홀 × 2.54
perf_hole_dy  = 38.10; // R2↔R17 = 15홀 × 2.54
insert_d      = 4.2;   // M3 열융착 인서트 하부 구멍 (제품에 따라 4.0~4.6 — 실물 확인)
insert_h      = 4;     // M3 열융착 인서트 길이 4 mm 기준(BOM E1). 보스 높이 5.5 → 바닥 1.5 mm

// MG90S 서보 (베인 직결 구동).아래 일부 값은 2026-09-19 SG90 기록에서 온 설계 가정이다.
// SG90 기록만으로 MG90S 장착 호환을 보증하지 않는다. 실제 귀 홀·축·혼 치수는 #219에서 확인한다.
servo_body_l  = 22.8;  // 접선 방향 길이(몸통 긴변) — ⚠️ 아직 미측정, 조사자료 기반 플레이스홀더
servo_body_w  = 23;    // 수직 방향 폭(두께) — 과거 SG90 기록, MG90S 미확인
servo_body_h  = 28;    // 반경 방향 깊이 — 과거 SG90 기록, MG90S 미확인
servo_ear_pitch = 33;         // 과거 SG90 3.3cm 기록. 귀 끝-끝일 수 있어 홀 간격으로 쓰지 않음
servo_ear_to_shaft = 3;       // 과거 SG90 0.3cm 기록. MG90S 홀 위치 미확인
                              // → 이어 홀이 비대칭 배치가 돼서 servo_boss_solid()의 boss_y 계산을
                              //   아래에서 "양쪪 홀을 다 덮는 최소폭" 방식으로 고쳤음(2026-09-19)
servo_screw_d = 1.7;         // M2 셀프탭 하부 구멍 (커플러 혼 고정용)
// 2026-10-16(#59): 서보 귀 나사 구멍을 슬롯으로 바꿨다. TowerPro 공식 MG90S 치수는 귀 끝-끝 전체 길이 32.1 mm
// (https://towerpro.com.tw/product/mg90s-3/ 의 E)라서, 위 servo_ear_pitch 33(SG90 실측)은 구멍 간격일 수 없다
// (귀 끝-끝을 잰 것으로 보임). 실물 MG90S를 아직 재지 못했으므로, 가까운 구멍은 축에서 9.0-10.5 mm,
// 먼 구멍은 16.5-30.5 mm 범위를 덮는 슬롯으로 뚫는다(설계 홀 피치 25.5-41 mm; 실제 서보 적합성은 미확정).
// 슬롯 폭 2.2 mm = M2 볼트 관통, 너트는 캐비티 안쪽에서 조인다.
servo_slot_w    = 2.2;
servo_slot_near = [9.0, 10.5];   // 혼 통과 구멍과 와셔 지지면을 피하는 설계 수용 범위(mm)
servo_slot_far  = [16.5, 30.5];  // 먼 구멍까지 거리 범위(mm)
servo_horn_pass_d = 10.5;
servo_washer_od_max = 5;        // M2 체결 와셔의 허용 외경 상한(구매 전 확인)
servo_web_min = 1;              // 구멍과 와셔 지지면 사이 최소 재료 폭(mm)
servo_boss_t  = 4;           // 서보 장착판 두께(반경 방향)
servo_standoff = 16;         // 링 바깥면 ↔ 장착판 사이 캐비티 깊이 (혼 + 스파 커플러가 들어감)

coupler_len        = 14;     // 스파 커플러 길이(반경 방향)
coupler_d          = 14;     // 커플러 바깥 지름
coupler_horn_t     = 2.2;    // 혼 두께 설계 가정. 실측 전(#219)
coupler_horn_w     = 9.0;    // 혼 암 폭 설계 가정. 실측 전(#219)
coupler_horn_depth = 9;      // 혼이 커플러에 물리는 깊이

vane_spar_d       = 3.0;     // C2 Ø3 CF 스파
vane_spar_bore    = 3.2;     // 스파 관통 보어
vane_inner_r      = 4;       // 베인 안쪽 끝 반경 (모터 허브 후류 회피)
vane_stop_deg     = 15;      // ±기계 하드스톱 각도 (링 벽 슬롯이 스톱 역할)

foot_pad_d = 16; foot_pad_h = 8;             // D5 PETG 발 범퍼(R2 발주품, 실측 필요)

$fn = 48; // 렌더 품질 (렌더 느리면 24로 낮추기)

// ---------- 좌표계 ----------
// z = 0 : EDF 배기면 (§4 기준면). 위로 +z, 아래로 -z.
vane_ring_top_z = -vane_gap_below_exit;                 // 베인링 상단
vane_ring_bot_z = vane_ring_top_z - vane_ring_h;         // 베인링 하단
top_plate_bot_z = vane_ring_top_z + col_len;             // 상판 하단 (기둥이 여기서 베인링까지)
top_plate_top_z = top_plate_bot_z + top_plate_t;
kill_switch_size = [22, 14, 10]; // BOM B6 미선정 외형 가정
kill_switch_min = [0, 52, top_plate_top_z];
kill_switch_center = kill_switch_min + kill_switch_size / 2;
foot_z          = -foot_below_exit;                      // 발 바닥
bail_top_z      = foot_z + H_total;                      // 검증용: 베일 팁

vane_ring_od = edf_housing_od + 24;
vane_ring_id = edf_housing_od + 4;
leg_top_r    = vane_ring_od/2;        // 다리 상단 부착 반경 (베인링에서 시작)
leg_bot_r    = foot_circle/2;         // 다리 하단(발) 반경
// #59: 다리 뿌리. 다리는 수직에서 약 56° 기운 관이라 수직 소켓에 안 들어갔다. 링 바깥 보스(반경 leg_root_r)에서
// 다리 축 방향으로 소켓을 뚫는다. 소켓 끝은 링 안쪽 벽(제트 쪽)에서 2 mm 이상 떨어져야 한다(검증 echo).
leg_root_r   = vane_ring_od/2 + 8;
// ⚠️ 버그 수정(2026-09-13): col_mount_r가 예전엔 edf_housing_od/2+25로 따로 계산돼서
//    vane_ring_od/2(=leg_top_r)보다 13mm나 커버렸음 → 기둥이 베인링 바깥 허공에서 끝나
//    실제로 안 닿는 상태였음. 기둥도 다리와 같은 반경(링 바깥 표면)에서 시작하도록 통일.
col_mount_r  = leg_top_r;             // 상판 위 기둥 부착 반경 = 베인링 바깥 반경 (다리와 동일선상, 45도만 엇갈림)
// ---------- 베인 · 방위 규약 (rev C.1) ----------
// 방위: 베인/서보 = 0°/90°/180°/270° (FWD/LEFT/AFT/RIGHT),  기둥·다리 = 45°/135°/225°/315°
//   ⚠️ 버그 수정(2026-09-17): 예전 legs()는 다리를 +90 계열(=베인과 같은 방위)에 놨었다.
//      그 상태면 다리 뿌리와 베인 서보가 같은 자리를 차지해 물리적으로 충돌한다.
//      다리를 기둥과 같은 +45 계열로 옮겨 45° 엇갈리게 만들었다(하중 경로도 기둥-다리 일직선이 유리).
az_vane = 0;    // 베인·서보 방위 오프셋
az_col  = 45;   // 기둥·다리 방위 오프셋

// 베인 피벗 z: 링의 수직 중앙(= 스파가 링 벽 한가운데를 관통 → 부싱 지지가 제대로 됨).
//   마스터 §4 의 "배기면→베인 피벗 22mm"는 실제로는 "배기면→링 상단"에 해당한다(링 높이 28의 중앙이 피벗).
//   즉 실제 피벗은 배기면 아래 36mm. 제어 모멘트암 계산엔 이 값을 쓸 것.
vane_pivot_z = (vane_ring_top_z + vane_ring_bot_z)/2;
vane_outer_r = vane_ring_id/2 + 3;   // 베인 바깥 끝 — 링 벽 슬롯 안으로 3mm 물려서 하드스톱 역할
vane_span_r  = vane_outer_r - vane_inner_r;                       // 베인 반경 방향 길이
// ±vane_stop_deg 회전 시 베인이 쓸고 지나가는 폭/높이 → 링 벽 슬롯 크기(= 기계 하드스톱)
vane_slot_w  = 2*(vane_chord/2*sin(vane_stop_deg) + vane_thick/2*cos(vane_stop_deg));
vane_slot_h  = 2*(vane_chord/2*cos(vane_stop_deg) + vane_thick/2*sin(vane_stop_deg)) + 0.8;
servo_mount_r = vane_ring_od/2;                      // 보스 웹이 시작하는 반경(= 링 바깥면)
servo_plate_r = servo_mount_r + servo_standoff;      // 서보 장착판 안쪽면 반경
vane_spar_len = servo_plate_r - vane_inner_r;        // Ø3 CF 스파 재단 길이(= 베인 안쪽 끝 ~ 장착판)

edf_clamp_id = edf_housing_od + edf_clamp_gap;  // 클램프 내경 = 실측 외경 + 여유
edf_clamp_z  = edf_clamp_z_from_exit;  // 클램프 높이 — 배기면(z=0) 기준, 실측 몸통 길이(edf_body_len) 안에 들어오는 값
edf_body_top_z = edf_body_len;         // 참고용: EDF 몸통 상단(흡입구 립) z — 검증 echo에 사용
tube_clearance = 0.3;                  // 소켓 구멍 여유 (Ø6mm 탄소관 삽입용, mm)
socket_depth   = 12;                   // 베인링에 뚫는 소켓 구멍 깊이 (mm, 링 높이 28mm 중)
bail_r       = (edf_housing_od/2 + 3 + col_mount_r + 15) / 2;   // 흡기 구멍 반경과 상판 바깥 반경의 가운데 (#59)
leg_boss_r   = leg_od/2 + tube_clearance + 2.7;   // 소켓 둘레 벽 두께 2.7

// ---------- 모듈 ----------

module top_plate() {
    // #181 CI 게이트 시험: 윗면이 없는 상자를 넣어 열린 STL을 만든다. 다음 커밋에서 되돌린다.
    translate([col_mount_r + 20, 0, 0]) polyhedron(
        points=[[0,0,0], [4,0,0], [4,4,0], [0,4,0], [0,0,4], [4,0,4], [4,4,4], [0,4,4]],
        faces=[[0,1,2,3], [0,4,5,1], [1,5,6,2], [2,6,7,3], [3,7,4,0]]
    );
    // 볼트 플랜지 없는 EDF라 상판엔 흡기 공기 통로용 홀만 뚫음 (마운트는 edf_clamp()가 담당)
    // ⚠️ D1 탄소관(기둥)은 프린트하는 게 아니라 실제 구매품 — 상판엔 관통 소켓 구멍만 뚫고 여기에 접착
    difference() {
        cylinder(h=top_plate_t, r=col_mount_r + 15, center=false);
        // EDF 흡기 통로 홀 — 하우징보다 살짝 크게(공기 흐름 여유, 접촉 없음)
        translate([0,0,-1]) cylinder(h=top_plate_t+2, r=edf_housing_od/2 + 3, center=false);
        // 베일 다리 구멍 2개 (#59)
        for (sx = [-1, 1]) translate([sx * bail_r, 0, -1]) cylinder(h = top_plate_t + 2, r = bail_od/2 + 0.15, $fn = 16);
        // D1 탄소관(기둥) 삽입용 관통 소켓 4개
        for (i=[0:n_cols-1]) {
            a = i*360/n_cols + 45;
            translate([col_mount_r*cos(a), col_mount_r*sin(a), -1])
                cylinder(h=top_plate_t+2, r=col_od/2 + tube_clearance, center=false);
        }
    }
}

// ---------- 체결 규격 (#59, 2026-10-16) ----------
// 프린트 부품에는 나사산을 모델링하지 않는다. 볼트가 지나는 구멍(관통), 셀프탭 하부 구멍, 열융착 인서트 구멍으로 나눈다.
m3_clear   = 3.4;   // M3 볼트 관통 구멍
m3_nut_af  = 5.5;   // M3 너트 맞변 거리
m2_clear   = 2.2;   // M2 볼트 관통 구멍
m2_tap     = 1.7;   // M2 셀프탭 하부 구멍

module edf_clamp() {
    // 분할 클램프 — 볼트 플랜지 없는 EDF 하우징을 감싼다. #59에서 다시 짰다:
    //  - 예전 형상은 반쪽 두 개의 조임 탭이 0°에서만 맞고 반대쪽은 170°/190°로 16 mm 어긋나 볼트를 꿸 수 없었다.
    //  - 또 탭이 기둥(45° 계열)에 닿지 않아 EDF가 프레임에 연결되지 않았다. 추력(약 13 N)이 지나는 길이 없었다.
    //  지금: y>0 / y<0 반쪽 2개. 0°·180° 이음부 탭을 M3 볼트 2개로 조여 하우징을 문다(이음 틈 2 mm가 지름 오차 흡수).
    //  각 반쪽에 기둥 조임 고리 2개(45°·135° / 225°·315°). 고리는 바깥으로 쪼갠 C형이고 M3 볼트로 기둥(Ø6 CF)을 문다.
    band_t   = 2.5;
    seam_gap = 2;                                    // 이음부 틈(한쪽)
    tab_t    = 5;  tab_r1 = edf_clamp_id/2 + band_t + 9;
    col_wall = 2.4;
    for (side = [1, -1]) edf_clamp_half(side, band_t, seam_gap, tab_t, tab_r1, col_wall);
}

module edf_clamp_half(side, band_t, seam_gap, tab_t, tab_r1, col_wall) {
    r_in = edf_clamp_id / 2;
    col_r_in  = col_od / 2 + tube_clearance;
    col_r_out = col_r_in + col_wall;
    translate([0, 0, edf_clamp_z]) difference() {
        union() {
            // 반원 밴드: 이음부 틈만큼 양끝을 잘라 둔다
            intersection() {
                difference() {
                    cylinder(h = edf_clamp_h, r = r_in + band_t, $fn = 96);
                    translate([0, 0, -1]) cylinder(h = edf_clamp_h + 2, r = r_in, $fn = 96);
                }
                translate([-r_in - 20, side > 0 ? seam_gap / 2 : -(r_in + 20), -1])
                    cube([2 * (r_in + 20), r_in + 20 - seam_gap / 2, edf_clamp_h + 2]);
            }
            // 이음부 조임 탭 (0°, 180°): 반쪽마다 두께 tab_t
            for (sx = [1, -1])
                translate([sx > 0 ? r_in : -tab_r1, side > 0 ? seam_gap / 2 : -seam_gap / 2 - tab_t, 0])
                    cube([tab_r1 - r_in, tab_t, edf_clamp_h]);
            // 기둥 조임 고리 2개 + 밴드와 잇는 웹
            for (k = [0, 1]) {
                a = side > 0 ? 45 + 90 * k : 225 + 90 * k;
                rotate([0, 0, a]) {
                    translate([r_in + band_t - 1, -3, 0]) cube([col_mount_r - (r_in + band_t - 1), 6, edf_clamp_h]);
                    translate([col_mount_r, 0, 0]) cylinder(h = edf_clamp_h, r = col_r_out, $fn = 32);
                    // 조임 귀 (고리 바깥쪽, 쪼갠 틈 양옆)
                    translate([col_mount_r + col_r_in - 1, -4.5, 0]) cube([9, 9, edf_clamp_h]);
                }
            }
        }
        // 기둥 구멍 + 바깥쪽으로 쪼갠 틈 + 귀를 가로지르는 M3 조임 볼트 구멍
        for (k = [0, 1]) {
            a = side > 0 ? 45 + 90 * k : 225 + 90 * k;
            rotate([0, 0, a]) {
                translate([col_mount_r, 0, -1]) cylinder(h = edf_clamp_h + 2, r = col_r_in, $fn = 32);
                translate([col_mount_r, -0.75, -1]) cube([col_r_in + 12, 1.5, edf_clamp_h + 2]);
                translate([col_mount_r + col_r_in + 4.5, -6, edf_clamp_h / 2])
                    rotate([-90, 0, 0]) cylinder(h = 12, r = m3_clear / 2, $fn = 24);
            }
        }
        // 이음부 M3 볼트 구멍 (y 방향 관통)
        for (sx = [1, -1])
            translate([sx * (r_in + band_t + 4.5), -tab_t - seam_gap, edf_clamp_h / 2])
                rotate([-90, 0, 0]) cylinder(h = 2 * tab_t + 2 * seam_gap, r = m3_clear / 2, $fn = 24);
    }
}

module columns() {
    for (i=[0:n_cols-1]) {
        a = i*360/n_cols + 45; // 사각 배치
        translate([col_mount_r*cos(a), col_mount_r*sin(a), vane_ring_top_z])
            cylinder(h=col_len, r=col_od/2, center=false);
    }
}

// ---------- 서보 장착 보스 (로컬 좌표: +x = 반경 바깥, +y = 접선, z = 수직) ----------
// 구조: 링 바깥면(r=48)에서 웹 2장이 뻗어나가 r=servo_plate_r 에 장착판을 띄운다.
//   그 사이 빈 공간(= servo_standoff)이 **서보 혼 + 스파 커플러가 들어가는 캐비티**다.
//   서보는 장착판 바깥면에 이어 2개로 물리고, 출력축은 판을 뚫고 안쪽 캐비티로 들어와
//   커플러를 거쳐 베인 스파와 동축으로 연결된다(직결 = 링키지 유격 0).
module servo_boss_solid() {
    // ⚠️ 2026-09-19 수정: 이어 홀 2개가 출력축(y=0) 기준 대칭이 아닐 수 있다(실측 결과
    //   servo_ear_to_shaft=3, servo_ear_pitch=33 → 홀이 y=-3, y=+30 에 위치, 중심에서 안 대칭).
    //   장착판은 y=0을 중심으로 대칭 프린트되므로, 양쪽 홀 중 더 먼 쪽까지의 거리를 기준으로
    //   폭을 잡아야 짧은 쪽 홀이 판 밖으로 안 나간다.
    ear_reach = max(servo_slot_near[1], servo_slot_far[1], 7);   // 슬롯 끝까지 덮는다(#59)
    boss_y = max(servo_body_l, 2*ear_reach + 8) + 8;   // 이어·출력축 구멍을 전부 덮는 접선 폭
    boss_z = servo_body_w + 10;
    union() {
        // 장착판
        translate([servo_plate_r, -boss_y/2, vane_pivot_z - boss_z/2])
            cube([servo_boss_t, boss_y, boss_z]);
        // 지지 웹 2장 (링 바깥면 → 장착판)
        for (s = [-1, 1])
            translate([servo_mount_r - 1, s*(boss_y/2 - 3.2) - 1.6, vane_pivot_z - boss_z/2])
                cube([servo_standoff + 1, 3.2, boss_z]);
        // 아래쪽 보강 립(= 캐비티 바닥). 위쪽은 일부러 열어둔다 —
        // 조립 때 커플러+혼을 위에서 떨궈 넣고, 조립 후에도 눈으로 확인·재조정이 가능해야 한다.
        translate([servo_mount_r - 1, -boss_y/2, vane_pivot_z - boss_z/2])
            cube([servo_standoff + 1, boss_y, 3]);
    }
}

module servo_boss_cuts() {
    // 이어 슬롯 2개 (출력축 기준 가까운 쪽은 −y, 먼 쪽은 +y). 위 servo_slot_* 설명 참고(#59)
    for (rng = [[-servo_slot_near[1], -servo_slot_near[0]], [servo_slot_far[0], servo_slot_far[1]]])
        hull() for (dy = rng)
            translate([servo_plate_r - 2, dy, vane_pivot_z])
                rotate([0,90,0])
                    cylinder(h = servo_boss_t + 6, r = servo_slot_w/2, center=false, $fn=20);
    // 혼 단면(9 x 2.2 mm, 각 변 +0.4 mm 여유)의 대각선보다 큰 통과 구멍.
    translate([servo_plate_r - 2, 0, vane_pivot_z])
        rotate([0,90,0])
            cylinder(h = servo_boss_t + 6, r = servo_horn_pass_d/2, center=false, $fn=40);
}

// 스파 관통 보어 + 베인 하드스톱 슬롯 (링 벽을 반경 방향으로 뚫는다)
module vane_wall_cuts() {
    // 스파: 링 안쪽(r=20)에서 커플러 캐비티 끝(장착판 안쪽면)까지 관통
    translate([20, 0, vane_pivot_z])
        rotate([0,90,0])
            cylinder(h = servo_plate_r - 20, r = vane_spar_bore/2, center=false, $fn=32);
    // 하드스톱 슬롯: 베인 바깥 끝이 ±vane_stop_deg 안에서만 움직이도록 링 벽에 낸 창.
    //   ⚠️ 링 벽(r=38~48)에서만 끝나야 한다 — 더 파면 서보 보스 웹까지 잘라먹는다.
    translate([vane_ring_id/2 - 2, -vane_slot_w/2, vane_pivot_z - vane_slot_h/2])
        cube([(vane_ring_od - vane_ring_id)/2 + 2, vane_slot_w, vane_slot_h]);
}

// 스파 커플러 — 서보 혼(알루미늄 싱글암, BOM C5)과 Ø3 CF 스파를 잇는 프린트 파트 ×4
// ⚠️ 혼 슬롯 치수(두께·폭)는 실물 혼을 재서 coupler_horn_t / coupler_horn_w 를 고칠 것.
// slack: 혼 슬롯 두께·폭에 더하는 여유(mm). 혼 실측 전 발주용으로 0.4 mm 세트를 같이 뽑는다(#59).
module vane_coupler(slack = 0) {
    difference() {
        rotate([0,90,0]) cylinder(h = coupler_len, r = coupler_d/2, center=false, $fn=40);
        // 스파 보어 (반경 방향 관통)
        translate([-1,0,0]) rotate([0,90,0])
            cylinder(h = coupler_len + 2, r = vane_spar_bore/2, center=false, $fn=32);
        // 혼 암이 들어가는 슬롯 (바깥쪽 절반까지)
        translate([coupler_len - coupler_horn_depth, -(coupler_horn_w + slack)/2, -(coupler_horn_t + slack)/2])
            cube([coupler_horn_depth + 1, coupler_horn_w + slack, coupler_horn_t + slack]);
        // 혼 고정 나사 길 (슬롯을 가로지름). 혼 구멍 간격을 아직 모르므로 원형 구멍 2개 대신
        // 혼 물림 구간 전체에 M2 셀프탭 폭의 긴 홈을 낸다(#59). 나사는 혼 구멍을 지나 홈 벽을 물고,
        // 헐거우면 에폭시(BOM E3)로 보강한다.
        hull() for (dx = [coupler_len - coupler_horn_depth + 1.5, coupler_len - 1.5])
            translate([dx, 0, -coupler_d])
                cylinder(h = 2*coupler_d, r = m2_tap/2, center=false, $fn=20);
    }
}

function leg_axis(a) = let(p1 = [leg_root_r*cos(a), leg_root_r*sin(a), vane_ring_bot_z],
                            p2 = [leg_bot_r*cos(a), leg_bot_r*sin(a), foot_z]) (p1 - p2) / norm(p1 - p2);
module leg_root_boss(a, rb) {   // 링 바깥 다리 뿌리 덩어리 (조립 좌표)
    p1 = [leg_root_r*cos(a), leg_root_r*sin(a), vane_ring_bot_z];
    hull() {
        translate(p1 - leg_axis(a) * 2) sphere(r = rb, $fn = 32);
        translate(p1 + leg_axis(a) * socket_depth) sphere(r = rb, $fn = 32);
        translate([vane_ring_od/2*cos(a) - 1*cos(a), vane_ring_od/2*sin(a) - 1*sin(a), vane_ring_bot_z])
            cylinder(h = vane_ring_h * 0.6, r = rb, $fn = 32);
    }
}
module leg_root_socket(a) {
    p1 = [leg_root_r*cos(a), leg_root_r*sin(a), vane_ring_bot_z];
    hull() {
        translate(p1 - leg_axis(a) * 10) sphere(r = leg_od/2 + tube_clearance, $fn = 24);
        translate(p1 + leg_axis(a) * socket_depth) sphere(r = leg_od/2 + tube_clearance, $fn = 24);
    }
}

module vane_ring() {
    // D1(기둥)·D2(다리) 탄소관은 구매품 — 링 위/아래 면에 소켓 구멍만 뚫어 꽂고 접착한다.
    // rev C.1 추가: 서보 보스 4개 · 스파 보어 4개 · 하드스톱 슬롯 4개 · 다리 방위 수정
    translate([0,0,vane_ring_bot_z])
        difference() {
            union() {
                cylinder(h=vane_ring_h, r=vane_ring_od/2, center=false);
                // 서보 보스는 링 로컬 z(0~vane_ring_h) 기준으로 다시 올려야 하므로 보정 이동
                for (i=[0:n_vanes-1])
                    rotate([0,0,i*360/n_vanes + az_vane])
                        translate([0,0,-vane_ring_bot_z]) servo_boss_solid();
                // 다리 뿌리 보스 4개 (#59)
                translate([0,0,-vane_ring_bot_z]) for (i=[0:n_legs-1]) leg_root_boss(i*360/n_legs + az_col, leg_boss_r);
            }
            translate([0,0,-1]) cylinder(h=vane_ring_h+2, r=vane_ring_id/2, center=false);
            // 기둥(위쪽) 소켓 — 링 윗면에서 아래로
            for (i=[0:n_cols-1]) {
                a = i*360/n_cols + az_col;
                translate([col_mount_r*cos(a), col_mount_r*sin(a), vane_ring_h - socket_depth])
                    cylinder(h=socket_depth+1, r=col_od/2 + tube_clearance, center=false);
            }
            // 다리 소켓 — 다리 축 방향으로 기울여 뚫는다(#59). 기둥과 같은 방위(45° 계열)
            translate([0,0,-vane_ring_bot_z]) for (i=[0:n_legs-1]) leg_root_socket(i*360/n_legs + az_col);
            // 베인 스파 보어 · 하드스톱 슬롯 · 서보 이어 홀
            for (i=[0:n_vanes-1])
                rotate([0,0,i*360/n_vanes + az_vane])
                    translate([0,0,-vane_ring_bot_z]) {
                        vane_wall_cuts();
                        servo_boss_cuts();
                    }
        }
}

// 베인 1개 — 로컬 좌표: +x = 반경(스팬), +y = 접선(두께), z = 유동 방향(시위)
// ⚠️ 버그 수정(2026-09-17): 예전 vanes()는 베인을 r=48(링 바깥면)에 놓고 스팬을 z방향으로 세웠다.
//    배기 제트는 반경 36mm 안쪽이라 그 위치의 베인은 **기류에 아예 닿지 않는다**(= 제어력 0).
//    제트베인은 "반경 방향으로 뻗고, 시위가 유동(z)을 따라가는 평판"이 맞다 —
//    반경축(스파) 회전 → 제트를 접선 방향으로 꺾음 → 두 쌍이 롤/피치, 4개 동시 캔트가 요.
module vane_one(deflect = 0) {
    // 스파(반경축, z = vane_pivot_z) 둘레 회전 = 베인 편향각. #59 정정: 예전엔 원점(z = 0) 둘레로 돌려
    // 꺾인 베인이 엉뚱한 곳에 그려졌다(출력물 형상은 deflect = 0이라 영향 없음).
    translate([0, 0, vane_pivot_z]) rotate([deflect, 0, 0]) translate([0, 0, -vane_pivot_z])
        difference() {
            union() {
                translate([vane_inner_r, -vane_thick/2, vane_pivot_z - vane_chord/2])
                    cube([vane_span_r, vane_thick, vane_chord]);
                // 스파 허브 — 판이 2.5mm라 Ø3.2 보어를 그냥 뚫으면 판이 두 동강 난다.
                // 피벗선을 따라 Ø6.6 두께로 부풀려서 스파를 감싸게 한다(= 두꺼운 중앙 스파인).
                translate([vane_inner_r, 0, vane_pivot_z])
                    rotate([0,90,0])
                        cylinder(h = vane_span_r, r = (vane_spar_bore + 3.4)/2, center=false, $fn=32);
            }
            // 스파 보어 (반경 방향 관통)
            translate([vane_inner_r - 1, 0, vane_pivot_z])
                rotate([0,90,0])
                    cylinder(h = vane_span_r + 2, r = vane_spar_bore/2, center=false, $fn=32);
        }
}

module vanes(deflect = 0) {
    for (i=[0:n_vanes-1])
        rotate([0,0,i*360/n_vanes + az_vane])
            vane_one(deflect);
}

module legs() {
    for (i=[0:n_legs-1]) {
        a = i*360/n_legs + az_col; // 기둥과 같은 방위 = 베인·서보(0/90/180/270)와 45° 엇갈림
        p1 = [leg_root_r*cos(a), leg_root_r*sin(a), vane_ring_bot_z];
        p2 = [leg_bot_r*cos(a), leg_bot_r*sin(a), foot_z];
        hull() {
            translate(p1) sphere(r=leg_od/2);
            translate(p2) sphere(r=leg_od/2);
        }
    }
}

module bail() {
    // 상판 위 손잡이(베일) — 세로로 선 아치형 Ø3 스틸봉. #59 정정: 예전 반경(0.6 x 48 = 29 mm)은
    // 상판 흡기 구멍(반경 39) 안쪽이라 꽂을 데가 없었다. 상판 몸체 가운데(반경 bail_r)로 옮기고 다리를 상판에 꽂는다.
    translate([0,0,top_plate_top_z])
        rotate([90,0,0])
            rotate_extrude(angle=180, $fn=64)
                translate([bail_r,0,0]) circle(r=bail_od/2);
    for (sx = [-1, 1]) translate([sx * bail_r, 0, top_plate_bot_z]) cylinder(h = top_plate_t, r = bail_od/2, $fn = 16);
}

// ---------- 장비 선반 (rev C.1 신규) ----------
// 로컬 좌표(선반을 az 방향으로 rotate 하기 전): +x = 반경 바깥, +y = 접선, z = 절대 z.
// 판의 안쪽 경계는 반경 shelf_r_inner 원호로 잘라낸다 → 흡기 스트림튜브를 절대 침범하지 않는다.
// 양 끝(접선 ±col_mount_r·sin45) 위치에 기둥을 통과시키는 새들 링이 있어 기둥에 끼워 고정한다.

module tie_slot(x, y, z) {   // 케이블타이 슬롯 (수직 관통)
    translate([x - tie_slot_l/2, y - tie_slot_w/2, z - 1])
        cube([tie_slot_l, tie_slot_w, shelf_t + 2]);
}

module shelf_blank(x_out, y_half) {
    // 판 + 가장자리 리브 + 새들 링 2개 (기둥 위치는 로컬 (±) 45° → x=y=col_mount_r/√2)
    cy = col_mount_r * sin(45);
    cx = col_mount_r * cos(45);
    difference() {
        union() {
            // 판
            translate([shelf_r_inner - 20, -y_half, shelf_top_z - shelf_t])
                cube([x_out - (shelf_r_inner - 20), 2*y_half, shelf_t]);
            // 바깥 가장자리 리브
            translate([x_out - 3, -y_half, shelf_top_z - shelf_t])
                cube([3, 2*y_half, shelf_t + shelf_rib_h]);
            // 접선 양끝 리브
            for (s = [-1, 1])
                translate([shelf_r_inner, s*y_half - (s>0?3:0), shelf_top_z - shelf_t])
                    cube([x_out - shelf_r_inner, 3, shelf_t + shelf_rib_h]);
            // 새들 링 2개
            for (s = [-1, 1])
                translate([cx, s*cy, shelf_top_z - shelf_t])
                    cylinder(h = saddle_h, r = col_od/2 + tube_clearance + saddle_wall, $fn=36);
        }
        // 안쪽 흡기 통로 — 반경 shelf_r_inner 원기둥으로 도려냄
        translate([0,0,shelf_top_z - shelf_t - 10])
            cylinder(h = saddle_h + 20, r = shelf_r_inner, $fn=96);
        // 새들 보어 (기둥 관통)
        for (s = [-1, 1])
            translate([cx, s*cy, shelf_top_z - shelf_t - 2])
                cylinder(h = saddle_h + 6, r = col_od/2 + tube_clearance, $fn=36);
        // #224: 안쪽 슬롯은 흡기 원호 옆에 얇은 조각을 남겨 제거했다.
        // 바깥 슬롯 1개/기둥. 타이는 슬롯과 선반 바깥 가장자리를 통해 고정부를 감싼다.
        for (s = [-1, 1]) {
            tie_slot(cx + saddle_tie_offset, s*cy, shelf_top_z - shelf_t);
        }
    }
}

module equip_shelf_battery() {
    // +Y(배터리) 선반: 판 위에 팩을 눕히고 벨크로 스트랩 2개로 X자 고정
    // #59: 실측 배터리 길이 73+-3 mm(최대 76)가 양끝 턱 사이 74 mm에 안 들어갔다. y_half 40 -> 42 (턱 사이 78 mm)
    y_half = batt_shelf_y_half;
    x_out  = shelf_r_inner + 50;    // 반경 42 → 92
    difference() {
        shelf_blank(x_out, y_half);
        // 스트랩 슬롯 4개 (2쌍)
        for (sx = [shelf_r_inner + 12, shelf_r_inner + 38])
            for (sy = [-26, 26])
                translate([sx - 3, sy - 8, shelf_top_z - shelf_t - 1])
                    cube([3.5, 16, shelf_t + 2]);
        // 배터리 반경 위치 트림용 장공 2개 (±8mm 슬라이드)
        for (sy = [-14, 14])
            translate([shelf_r_inner + 20, sy - 2.5, shelf_top_z - shelf_t - 1])
                cube([16, 5, shelf_t + 2]);
    }
}

module equip_shelf_avionics() {
    // −Y(아비오닉스) 선반: 만능기판을 M3 스탠드오프 4개로 수평 장착 + 수신기/UBEC 타이 슬롯
    y_half = 40;
    x_out  = shelf_r_inner + 54;    // 반경 42 → 96
    px0    = shelf_r_inner + (54 - perf_hole_dy)/2;   // 보드 장착홀 안쪽 열 x
    difference() {
        union() {
            shelf_blank(x_out, y_half);
            // 인서트 보스 4개 (판 위로 살짝 솟게 해서 인서트 깊이 확보)
            for (hx = [px0, px0 + perf_hole_dy])
                for (hy = [-perf_hole_dx/2, perf_hole_dx/2])
                    translate([hx, hy, shelf_top_z - shelf_t])
                        cylinder(h = shelf_t + 2.5, r = insert_d/2 + 2.2, $fn=28);
        }
        // M3 열융착 인서트 구멍
        for (hx = [px0, px0 + perf_hole_dy])
            for (hy = [-perf_hole_dx/2, perf_hole_dx/2])
                translate([hx, hy, shelf_top_z + 2.5 - insert_h])   // 막힌 구멍: 바닥 1.5 mm 남김(#59)
                    cylinder(h = insert_h + 1, r = insert_d/2, $fn=28);
        // 무게추 볼트 구멍 2개 (#59)
        for (sy = [-ballast_y, ballast_y])
            translate([ballast_x, sy, shelf_top_z - shelf_t - 1]) cylinder(h = shelf_t + 5, r = ballast_hole_d/2, $fn = 24);
        // ESC 브래킷 플랜지 타이 슬롯과 짝이 되는 선반 타이 슬롯 2개(#59). 예전엔 선반 쪽 짝이 없어
        // 브래킷을 선반에 묶을 길이 없었다.
        for (sy = [-(esc_l + 8)/2 + 6, (esc_l + 8)/2 - 6])
            tie_slot(shelf_r_inner + 6 + tie_slot_l/2, sy, shelf_top_z - shelf_t);
        // 수신기·UBEC 타이 슬롯
        for (sy = [-34, 34]) {
            tie_slot(shelf_r_inner + 14, sy, shelf_top_z - shelf_t);
            tie_slot(shelf_r_inner + 34, sy, shelf_top_z - shelf_t);
        }
        // 배선 통로 슬롯 2개 (서보선·3상선이 아래로 빠지는 길)
        // 2026-10-16(#59): 예전 슬롯(x 43-49, y ±12.5-27.5)은 바로 아래 ESC 브래킷 플랜지(x 44-60, |y| ≤ 22)에
        // 절반 넘게 가려졌다. 플랜지 바깥이면서 만능기판 인서트 보스와 새들 타이 슬롯을 모두 피하는
        // x 62-74, |y| 8-18(12x10 mm)로 옮겼다. 선은 기판 밑(스탠드오프 높이)으로 나와 기판 가장자리로 간다.
        // 겹침은 아래 검증 echo가 확인한다.
        for (s = [-1, 1])
            translate([wire_slot_x0, s > 0 ? wire_slot_y0 : -wire_slot_y1, shelf_top_z - shelf_t - 1])
                cube([wire_slot_x1 - wire_slot_x0, wire_slot_y1 - wire_slot_y0, shelf_t + 2]);
    }
}

module esc_bracket() {
    // 270°(−Y) 방향, 아비오닉스 선반 안쪽 아래로 내려가는 ESC 브래킷.
    // 흡입구로 빨려드는 공기가 지나는 자리라 실제로 냉각된다(01-avionics…md §7.6).
    w = esc_l + 8;            // 접선 폭
    h = 44;                   // 수직 길이
    top_z = shelf_top_z - shelf_t;
    difference() {
        union() {
            // 선반 밑면에 붙는 플랜지
            translate([shelf_r_inner + 2, -w/2, top_z - 3])
                cube([16, w, 3]);
            // ESC가 붙는 수직판
            translate([shelf_r_inner + 2, -w/2, top_z - h])
                cube([3, w, h]);
        }
        // 플랜지 타이 슬롯 2개
        for (sy = [-w/2 + 6, w/2 - 6])
            translate([shelf_r_inner + 6, sy - tie_slot_w/2, top_z - 4])
                cube([tie_slot_l, tie_slot_w, 5]);
        // ESC 고정 타이 슬롯 4개 (수직판)
        for (sz = [top_z - h + 8, top_z - 12])
            for (sy = [-w/2 + 5, w/2 - 5])
                translate([shelf_r_inner + 1, sy - tie_slot_w/2, sz - tie_slot_l/2])
                    cube([5, tie_slot_w, tie_slot_l]);
    }
}

// ---------- 조립 미리보기용 목업 (프린트 대상 아님 — 자리·간섭 확인용) ----------
module mock_battery() {
    rotate([0,0,90])
        translate([shelf_r_inner + batt_w/2 + 4, 0, shelf_top_z + batt_h/2])
            color("dimgray") cube([batt_w, batt_l, batt_h], center=true);
}
module mock_avionics() {
    rotate([0,0,270])
        translate([avi_board_r, 0, avi_board_z]) {
            color("darkgreen") cube([50, 70, avi_stack_t], center=true); // 만능기판+헤더+레벨시프터 간섭 외피
            translate([avi_teensy_xy[0], avi_teensy_xy[1], avi_stack_t/2 + avi_module_gap + 2.5])
                color("darkslategray") cube([18, 36, 5], center=true); // Teensy
            translate([avi_imu_xy[0], avi_imu_xy[1], avi_stack_t/2 + avi_module_gap + 1.5])
                color("teal") cube([16, 18, 3], center=true); // BNO085
        }
}
module mock_esc() {
    // 브래킷 수직판(x shelf_r_inner+2 ~ +5)의 바깥면에 붙는다(#59 정정: 예전 모형은 판 안에 겹쳐 그렸다)
    rotate([0,0,270])
        translate([shelf_r_inner + 5 + esc_t/2, 0, shelf_top_z - shelf_t - 26])
            color("black") cube([esc_t, esc_l, esc_w], center=true);
}
module servo_blocks() {
    // MG90S 서보 4개 — 베인 링 바깥 보스에 직결(출력축 = 베인 스파와 동축, 반경 방향)
    for (i=[0:n_vanes-1])
        rotate([0,0,i*360/n_vanes + az_vane])
            translate([servo_plate_r + servo_boss_t + servo_body_h/2,
                       (servo_ear_pitch/2 - servo_ear_to_shaft), vane_pivot_z])
                color("black") cube([servo_body_h, servo_body_l, servo_body_w], center=true);
}

module foot_pads() {
    // 발 범퍼(프린트). #59 정정: 예전엔 꽉 찬 원통이라 다리 탄소관이 꽂힐 자리가 없었다.
    // 다리 축 방향으로 소켓(Ø leg_od + 여유)을 뚫는다.
    for (i=[0:n_legs-1]) {
        a = i*360/n_legs + az_col; // legs()와 동일 각도로 맞춤
        p1 = [leg_root_r*cos(a), leg_root_r*sin(a), vane_ring_bot_z];
        p2 = [leg_bot_r*cos(a), leg_bot_r*sin(a), foot_z];
        difference() {
            translate([p2[0], p2[1], foot_z - foot_pad_h/2])
                color("darkorange") cylinder(h=foot_pad_h, r=foot_pad_d/2, center=true, $fn=40);
            hull() {   // 다리 축 그대로 끝에서 3 mm 더 연장. 범퍼 바닥과 약 3 mm 벽이 남는다
                translate(p1) sphere(r=leg_od/2 + tube_clearance, $fn=24);
                translate(p2 + (p2 - p1) / norm(p2 - p1) * 3) sphere(r=leg_od/2 + tube_clearance, $fn=24);
            }
        }
    }
}


// ---------- 조립 ----------
// render_mode = "preview": 조립 미리보기 (기둥/다리를 실봉으로, 부품을 색블록으로 시각화 — 실제 프린트 대상 아님)
// render_mode = "print"  : 진짜 프린트해서 외주 넣을 대상만 (상판·베인링엔 D1/D2 탄소관용 소켓 구멍만 뚫려있음)
//                          커맨드라인에서 -D 'render_mode="print"' 로 오버라이드해서 별도 export
render_mode = "preview";

if (render_mode == "preview") {
    color("silver") translate([0,0,top_plate_bot_z]) top_plate();
    color("gold")   columns();          // ⚠️ 프린트 안 함 — D1 탄소관(구매품) 자리 표시용
    color("silver") vane_ring();
    color("orangered") vanes();         // 중립(0°). vanes(15) 로 렌더하면 하드스톱 간섭 확인 가능
    color("gold")   legs();             // ⚠️ 프린트 안 함 — D2 탄소관(구매품) 자리 표시용
    color("gray")   bail();             // ⚠️ 프린트 안 함 — 철사 벤딩으로 별도 제작
    color("crimson") edf_clamp();
    color("lightsteelblue") rotate([0,0,90])  equip_shelf_battery();    // +Y 배터리 선반
    color("lightsteelblue") rotate([0,0,270]) equip_shelf_avionics();   // −Y 아비오닉스 선반
    color("indianred")      rotate([0,0,270]) esc_bracket();
    color("dimgray") for (i=[0:n_vanes-1]) rotate([0,0,i*360/n_vanes + az_vane])
        translate([servo_mount_r + 1.5, 0, vane_pivot_z]) vane_coupler();
    mock_battery(); mock_avionics(); mock_esc();   // ⚠️ 프린트 안 함 — 실물 자리 표시용
    servo_blocks();                                 // ⚠️ 프린트 안 함 — MG90S 자리 표시용
    foot_pads();
} else if (render_mode == "print") {
    // 진짜 프린트 파트만 (개별 export 순서는 cad/print_parts/README.md):
    //   상판 · 베인링(서보보스·스파보어·스톱슬롯 포함) · 베인 4 · EDF 클램프 · 배터리선반 ·
    //   아비오닉스선반 · ESC 브래킷 · 발범퍼 4
    translate([0,0,top_plate_bot_z]) top_plate();
    vane_ring();
    vanes();
    edf_clamp();
    rotate([0,0,90])  equip_shelf_battery();
    rotate([0,0,270]) equip_shelf_avionics();
    rotate([0,0,270]) esc_bracket();
    for (i=[0:n_vanes-1]) rotate([0,0,i*360/n_vanes + az_vane])
        translate([servo_mount_r + 1.5, 0, vane_pivot_z]) vane_coupler();
    foot_pads();
}

// ---------- 검증 출력 (콘솔에서 확인) ----------
echo(str("EDF 몸통 범위 = 0 ~ ", edf_body_top_z, " mm (배기면 기준) — 클램프 위치 z=", edf_clamp_z, "mm는 ", (edf_clamp_z>=0 && edf_clamp_z<=edf_body_top_z) ? "범위 안 (정상)" : "!! 범위 밖 — 몸통을 못 감쌈, 값 재조정 필요 !!"));
echo(str("장비 선반 윗면 z=", shelf_top_z, "mm — EDF 립(", edf_body_top_z, "mm)보다 ",
         shelf_top_z - edf_body_top_z, "mm 위, 상판 하면(", top_plate_bot_z, "mm)보다 ",
         top_plate_bot_z - shelf_top_z, "mm 아래 → ",
         (shelf_top_z > edf_body_top_z && shelf_top_z + max(batt_h, batt_h_max) + batt_strap_t + 1 <= top_plate_bot_z)
           ? str("정상(최대 ", batt_h_max, "mm 팩 + 스트랩이 상판 밑에 들어감, 여유 ",
                 top_plate_bot_z - shelf_top_z - max(batt_h, batt_h_max) - batt_strap_t, "mm)")
           : "!! 겹침 — shelf_top_z 재조정 필요 !!"));
echo(str("선반 안쪽 경계 r=", shelf_r_inner, "mm vs 흡기홀 반경 ", edf_housing_od/2 + 3,
         "mm → ", (shelf_r_inner >= edf_housing_od/2 + 3)
           ? "정상(흡기 통로 안 막음)" : "!! 흡기 통로 침범 !!"));
echo(str("베인 스팬 r=", vane_inner_r, "~", vane_outer_r, "mm vs 제트 반경 ", edf_housing_od/2,
         "mm → ", (vane_outer_r >= edf_housing_od/2)
           ? "정상(제트 전단면을 가로지름)" : "!! 베인이 기류 밖 — 제어력 0 !!"));
echo(str("하드스톱 슬롯 폭=", vane_slot_w, "mm (±", vane_stop_deg, "° 기준), 높이=", vane_slot_h, "mm"));
echo(str("서보 장착판 r=", servo_plate_r, "~", servo_plate_r + servo_boss_t,
         "mm, 서보 몸통 바깥 끝 r≈", servo_plate_r + servo_boss_t + servo_body_h,
         "mm (다리는 z=", vane_ring_bot_z, " 아래에서 시작하므로 간섭 없음)"));
echo(str("혼/커플러 캐비티 깊이 = ", servo_standoff, "mm, 커플러 길이 ", coupler_len,
         "mm → ", (coupler_len <= servo_standoff) ? "정상(캐비티 안에 들어감)"
                                                  : "!! 커플러가 캐비티보다 김 !!"));
echo(str("Ø3 CF 스파 재단 길이 = ", vane_spar_len, " mm  (베인 안쪽 끝 r=", vane_inner_r,
         " ~ 장착판 r=", servo_plate_r, ")"));
echo(str("상판 상단 z = ", top_plate_top_z, " mm"));
echo(str("베인 피벗 z = ", vane_pivot_z, " mm — 마스터 §4 의 '배기면→피벗 ", vane_gap_below_exit,
         "mm'는 실제로는 '배기면→링 상단'. 제어 모멘트암은 |z_cg - ", vane_pivot_z, "| 로 계산할 것"));
// 배선 슬롯 겹침 검사: ESC 플랜지(x shelf_r_inner+2 ~ +18, |y| ≤ (esc_l+8)/2), 만능기판 인서트 보스, 새들 타이 슬롯
function rect_gap(ax0, ax1, ay0, ay1, bx0, bx1, by0, by1) =
    max(max(bx0 - ax1, ax0 - bx1), max(by0 - ay1, ay0 - by1));   // > 0 이면 떨어져 있음
function circ_gap(x0, x1, y0, y1, cx, cy, r) =
    norm([max(x0 - cx, 0, cx - x1), max(y0 - cy, 0, cy - y1)]) - r;
wire_slot_px0 = shelf_r_inner + (54 - perf_hole_dy)/2;
wire_slot_gaps = [
    rect_gap(wire_slot_x0, wire_slot_x1, wire_slot_y0, wire_slot_y1,
             shelf_r_inner + 2, shelf_r_inner + 18, -(esc_l + 8)/2, (esc_l + 8)/2),
    min([for (hx = [wire_slot_px0, wire_slot_px0 + perf_hole_dy])
         circ_gap(wire_slot_x0, wire_slot_x1, wire_slot_y0, wire_slot_y1, hx, perf_hole_dx/2, insert_d/2 + 2.2)]),
    rect_gap(wire_slot_x0, wire_slot_x1, wire_slot_y0, wire_slot_y1,
             col_mount_r*cos(45) + saddle_tie_offset - tie_slot_l/2, col_mount_r*cos(45) + saddle_tie_offset + tie_slot_l/2,
             col_mount_r*sin(45) - tie_slot_w/2, col_mount_r*sin(45) + tie_slot_w/2),
    rect_gap(wire_slot_x0, wire_slot_x1, wire_slot_y0, wire_slot_y1,
             shelf_r_inner + 6, shelf_r_inner + 6 + tie_slot_l,
             (esc_l + 8)/2 - 6 - tie_slot_w/2, (esc_l + 8)/2 - 6 + tie_slot_w/2)];
echo(str("배선 슬롯 간격(mm): ESC 플랜지 ", wire_slot_gaps[0], ", 인서트 보스 ", wire_slot_gaps[1],
         ", 새들 타이 슬롯 ", wire_slot_gaps[2], ", ESC 타이 슬롯 ", wire_slot_gaps[3], " → ",
         min(wire_slot_gaps) >= 1 ? "정상(모두 1 mm 이상 떨어짐)" : "!! 겹치거나 1 mm 미만 !!"));

// #224: 새들 링을 흡기 원호가 자르거나 타이 슬롯이 얇은 끝을 만들면 발주를 막는다.
saddle_outer_r = col_od/2 + tube_clearance + saddle_wall;
saddle_intake_gap = col_mount_r - saddle_outer_r - shelf_r_inner;
saddle_tie_gap = saddle_tie_offset - tie_slot_l/2 - saddle_outer_r;
echo(str("선반 새들: 벽 ", saddle_wall, " mm, 흡기 여유 ", saddle_intake_gap,
         " mm, 타이 슬롯 여유 ", saddle_tie_gap, " mm → ",
         saddle_wall >= 2.4 && saddle_intake_gap >= 0.25 && saddle_tie_gap >= 2
         ? "정상" : "!! 새들 벽 또는 여유 부족 !!"));
echo(str("서보 귀 슬롯: 가까운 쪽 ", servo_slot_near, "mm, 먼 쪽 ", servo_slot_far,
         "mm → 구멍 간격 ", servo_slot_near[0] + servo_slot_far[0], "-", servo_slot_near[1] + servo_slot_far[1],
         "mm 범위를 받음 (MG90S 실물 미측정, #59)"));
leg_sock_end = [leg_root_r*cos(45), leg_root_r*sin(45), vane_ring_bot_z] + leg_axis(45) * socket_depth;
echo(str("다리 소켓: 기울기 ", acos(leg_axis(45)[2]), "° (수직 기준), 소켓 끝과 링 안쪽 벽 사이 ",
         norm([leg_sock_end[0], leg_sock_end[1]]) - (leg_od/2 + tube_clearance) - vane_ring_id/2, " mm → ",
         norm([leg_sock_end[0], leg_sock_end[1]]) - (leg_od/2 + tube_clearance) - vane_ring_id/2 >= 2
           ? "정상(제트 쪽 벽을 뚫지 않음)" : "!! 소켓이 링 안쪽 벽에 너무 가깝다 !!"));
echo(str("베일 반경 ", bail_r, " mm: 흡기 구멍 ", edf_housing_od/2 + 3, " mm와 상판 바깥 ", col_mount_r + 15, " mm 사이 → ",
         (bail_r - bail_od/2 > edf_housing_od/2 + 3 + 2 && bail_r + bail_od/2 < col_mount_r + 15 - 2) ? "정상" : "!! 베일 구멍이 상판 가장자리에 걸림 !!"));
echo(str("배터리 선반 턱 사이 ", 2*batt_shelf_y_half - 6, " mm vs 배터리 최대 길이 ", batt_l_max, " mm → ",
         2*batt_shelf_y_half - 6 >= batt_l_max + 1 ? "정상" : "!! 배터리가 턱에 걸림 !!"));
ballast_gap = min([for (hx = [wire_slot_px0, wire_slot_px0 + perf_hole_dy]) for (sy = [-1, 1])
    norm([ballast_x - hx, ballast_y - sy * perf_hole_dx/2]) - ballast_hole_d/2 - (insert_d/2 + 2.2)]);
echo(str("무게추 구멍과 만능기판 인서트 보스 최소 간격 ", ballast_gap, " mm → ", ballast_gap >= 2 ? "정상" : "!! 너무 가까움 !!"));
echo(str("서보 와셔 지지면 여유 ", servo_slot_near[0] - servo_horn_pass_d/2 - servo_washer_od_max/2,
         " mm → ", servo_slot_near[0] - servo_horn_pass_d/2 - servo_washer_od_max/2 >= servo_web_min ? "정상" : "!! 지지면 부족 !!"));
echo(str("혼 통과 여유 → ", servo_horn_pass_d >= norm([coupler_horn_w + 0.4, coupler_horn_t + 0.4]) ? "정상" : "!! 통과 불가 !!"));
echo(str("무게추 후보: 강철 고리 2개 D", ballast_od, " x H", ballast_h, " mm, 구멍 ", ballast_hole_d,
         " mm, 합계 ", ballast_target_g, " g (가정, 실측 전)"));
echo(str("발 바닥 z = ", foot_z, " mm"));
echo(str("상판top~발bottom 실제 전고 = ", top_plate_top_z - foot_z, " mm  (설계 H_total 참고값 = ", H_total, " mm)"));

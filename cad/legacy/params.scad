// ============================================================================
//  COSMOS 착륙 호퍼 (rev B — 64mm/4S 오픈 스탠드오프 프레임)
//  단위: mm, 각도: deg.  이 파일이 모든 치수의 유일 정의.
//  docs/design/00-hopper-master-design.md §4 표와 짝을 이룬다.
//  실물을 구하면 MEASURED 블록 값만 바꾸고 다시 뽑는다.
// ============================================================================

/* ---------------- MEASURED — 실물 확보 후 이 칸만 갱신 ---------------- */
// [ ] 64mm EDF (Freewing V2 4S / FMS 64 4S 등)
edf_housing_od     = 67;     // 팬 하우징 바깥지름 (64 팬 + 립) — 버니어 실측!
edf_housing_len    = 62;     // 팬+모터 스택 길이
edf_exit_od        = 64;     // 배기측 안지름 (제트 지름)
edf_mount_n        = 4;
edf_mount_pcd      = 76;     // 마운트 볼트 피치원 — 실측!
edf_mount_screw_d  = 3.2;    // M3 클리어런스

// [ ] 서보 (MG90S)
servo_body_l       = 22.8;
servo_body_w       = 12.2;
servo_body_h       = 22.5;
servo_lug_span     = 32.2;
servo_lug_screw_d  = 2.2;
servo_shaft_from_end = 6.0;

// [ ] 로드류
col_rod_d          = 6.1;    // 기둥 CF 튜브 Ø6 (+여유)
leg_rod_d          = 6.1;    // 착륙다리 CF 튜브 (Ø8 알루면 8.1)
vane_spar_d        = 3.1;
vane_pivot_d       = 3.0;

/* ---------------- DESIGN — 형상 확정값 (팀 합의 없이 바꾸지 말 것) ------- */
// 상판
top_plate_d        = 120;
top_plate_t        = 4;
$fn_plate           = 160;

// 기둥
col_n              = 4;
col_len            = 200;    // 상판 아랫면 ~ 베인링 윗면
col_pcd            = 88;     // 기둥 중심 피치원
col_socket_depth   = 14;

// 베인 링
vane_ring_od       = 96;
vane_ring_h        = 28;
vane_gap_below_exit= 22;     // EDF 배기면 아래로 베인 피벗축

// 베인
vane_n             = 4;
vane_chord         = 25;
vane_span          = 45;
vane_thick         = 2.5;
vane_deflect_max   = 15;     // ± 기계 하드스톱
vane_root_from_axis= 7;      // 기체 축에서 베인 안쪽 끝

// 링키지
horn_len           = 8;
pushrod_d          = 1.6;

// 착륙 다리
leg_n              = 4;
leg_splay          = 33;     // 수직 기준
leg_len            = 210;
leg_foot_below_exit= 140;
foot_pad_d         = 40;

// 중앙 트레이
tray_h             = 60;     // 스택 높이(배터리+FC+ESC)
tray_slot_len      = 40;     // CG 트림 세로 슬롯 (±20)

// 상단 베일
bail_rod_d         = 3.2;    // Ø3 스틸봉
bail_width         = 70;
bail_height        = 55;

// 구속 하드포인트 (베인링 중앙 언더슬렁 소켓)
uslung_screw_d     = 6.5;    // M6
uslung_holes_n     = 3;
uslung_hole_pitch  = 15;

/* ---------------- 파생 / 검증 ---------------- */
echo(str("EDF 배기 지름 ", edf_exit_od, " / 베인 링 내경 여유 확인",
         " / 기둥 PCD ", col_pcd, " vs 상판 Ø ", top_plate_d));
if (edf_housing_od + 8 > top_plate_d)
    echo("*** 경고: 상판이 EDF 대비 좁음 — top_plate_d 재검토 ***");
if (col_pcd + col_rod_d + 6 > top_plate_d)
    echo("*** 경고: 기둥이 상판 밖으로 나감 — col_pcd 또는 top_plate_d 조정 ***");

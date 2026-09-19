# cad/print_parts/ — 외주 프린트용 STL

**2026-09-18: 실제로 export 완료.** 예전엔 이 폴더가 계속 비어 있었다(OpenSCAD 로컬 미설치로 알고
있었는데, 실제로는 `Program Files\OpenSCAD\`의 설치가 깨져 있었을 뿐이고 — 진짜 실행파일은
`C:\Users\mimin\Desktop\openscad.exe`(2021.01)에 있었다). 그 실행파일로 9개 파츠를 전부 렌더·export했다.

| 파일 | 내용 |
|---|---|
| `top_plate.stl` | 상판 |
| `vane_ring.stl` | 베인링(서보 보스·스파 보어·하드스톱 슬롯 포함) |
| `vanes_x4.stl` | 베인 4개(한 시트) |
| `edf_clamp.stl` | EDF 분할 클램프(2조각) |
| `battery_shelf.stl` | 배터리 선반(+Y) |
| `avionics_shelf.stl` | 아비오닉스 선반(−Y, 만능기판 인서트 포함) |
| `esc_bracket.stl` | ESC 브래킷 |
| `vane_couplers_x4.stl` | 서보혼↔스파 커플러 4개 |
| `foot_pads_x4.stl` | 발 범퍼 4개 |

## 재현 방법 (수치가 바뀌었을 때 다시 export하려면)

`hopper_params.scad`는 `render_mode`(preview/print) 하나로만 나뉘어 있어서, "print"로 렌더해도 9개
파츠가 한 덩어리로 합쳐져 나온다 — **개별 STL을 얻으려면 파일 맨 아래 조립 섹션을 부품 하나 호출로
바꾼 임시 사본을 만들어 export해야 한다** (진짜 소스 파일은 건드리지 않는다 — 다른 세션이 계속
`hopper_params.scad`를 고치고 있어서 충돌 위험이 있다).

1. `hopper_params.scad`의 1~516행(변수·모듈 정의부, `// ---------- 조립 ----------` 주석 앞까지)을
   임시 파일로 복사.
2. 그 뒤에 원하는 파츠 호출 한 줄만 추가(아래 표 — 이건 소스 파일의 "print" 분기에 있는 호출을 그대로
   옮긴 것):

   | 파츠 | 추가할 줄 |
   |---|---|
   | top_plate | `translate([0,0,top_plate_bot_z]) top_plate();` |
   | vane_ring | `vane_ring();` |
   | vanes_x4 | `vanes();` |
   | edf_clamp | `edf_clamp();` |
   | battery_shelf | `rotate([0,0,90]) equip_shelf_battery();` |
   | avionics_shelf | `rotate([0,0,270]) equip_shelf_avionics();` |
   | esc_bracket | `rotate([0,0,270]) esc_bracket();` |
   | vane_couplers_x4 | `for (i=[0:n_vanes-1]) rotate([0,0,i*360/n_vanes + az_vane]) translate([servo_mount_r + 1.5, 0, vane_pivot_z]) vane_coupler();` |
   | foot_pads_x4 | `foot_pads();` |

3. `openscad.exe --render -o <파츠이름>.stl <임시파일>.scad`
4. 임시 파일 삭제(커밋 대상 아님).

GUI로 하고 싶으면 원래 방식(모듈 하나만 남기고 나머지 주석 처리 → F6 → Export as STL)도 그대로 유효 —
위 방법은 그걸 커맨드라인으로 자동화한 것뿐이다.

## 다음 단계

- 슬라이서(Cura/PrusaSlicer)에서 치수·인필 확인 — 재료는 PETG(모터 폐열 대응, PLA 금지), 벽 4라인,
  인필 40%(`docs/design/00-hopper-master-design.md` §10-4).
- 외주 발주 전 §5.1(만능기판 실제 홀수)·§2.4(BNO085 SPI 지원 패드)·§7.4(MG90S 이어 홀 간격) 등
  `docs/design/01-avionics-integration-final.md`의 "확인 포인트"를 실물로 재확인.
- 실제로 발주 넣을 때 그 시점 STL을 `cad/print-orders/<날짜>/`로 복사해서 커밋(`.gitignore` 예외).

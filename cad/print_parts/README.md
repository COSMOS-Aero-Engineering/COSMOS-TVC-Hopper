# cad/print_parts/ — 외주 프린트용 STL (아직 비어 있음)

`AGENTS.md`·이전 상태 로그에 "print-ready 7종 완성"이라 적혀 있었지만, 실제로는 **STL 파일 자체가
어디에도 저장되어 있지 않았다** (2026-09-17 확인 — Codex 세션 안에서만 렌더됐고 export가 안 된 것으로
추정). `cad/hopper_params.scad`는 실물(레포에 있음)이니, 아래 순서로 다시 export하면 된다.

## Export 순서

1. [OpenSCAD](https://openscad.org/downloads.html) 설치 (로컬에 없음 확인됨).
2. `cad/hopper_params.scad` 열기.
3. 맨 아래 `render_mode = "preview";` → 부품별로 아래처럼 바꿔가며 **7번 개별 export**
   (`render_mode="print"`로 한 번에 렌더하면 7개 부품이 다 합쳐진 하나의 형상이 나와서 프린트 발주용으론 못 씀 —
   반드시 모듈 하나씩만 남기고 나머지는 주석 처리 후 export):

   | # | 남길 모듈 | 파일명 |
   |---|---|---|
   | 1 | `translate([0,0,top_plate_bot_z]) top_plate();` | `top_plate.stl` |
   | 2 | `vane_ring();` | `vane_ring.stl` |
   | 3 | `vanes();` | `vanes_x4.stl` (베인 4개 한 판) |
   | 4 | `edf_clamp();` | `edf_clamp.stl` (분할 클램프 2조각 포함) |
   | 5 | `avionics_tray_plate();` | `avionics_tray_plate.stl` |
   | 6 | `battery_tray_plate();` | `battery_tray_plate.stl` |
   | 7 | `foot_pads();` | `foot_pads_x4.stl` |

4. 각각 `F6`(Render) → `Export as STL` → 이 폴더에 저장.
5. 외주 발주 전 슬라이서(Cura/PrusaSlicer)에서 치수·인필 확인 — 재료는 PETG(모터 폐열 대응, PLA 금지).

이 폴더(`cad/print_parts/`)의 STL은 `.gitignore`로 커밋 제외됨(재생성 가능한 산출물이라). **실제로
외주에 발주 넣을 때**는 그 시점의 STL을 `cad/print-orders/<날짜 또는 발주명>/`으로 복사해둘 것 —
거긴 `.gitignore` 예외로 커밋되게 해놔서, 나중에 "우리가 보낸 파일이 이거였나" 확인하는 유일한 근거가 된다.

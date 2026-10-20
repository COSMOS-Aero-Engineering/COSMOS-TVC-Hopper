# cad/print_parts/ — 외주 프린트용 STL

**2026-09-18: 실제로 export 완료.** 예전에는 OpenSCAD 기본 설치가 깨져 이 폴더가 비어 있었다.
별도 OpenSCAD 2021.01 실행파일로 당시 파츠 9개를 렌더·export했다. 현재는 아래 스크립트가
환경변수 `OPENSCAD`, PATH, Windows 기본 설치 경로에서 실행 가능한 OpenSCAD를 찾는다.

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
| `vane_couplers_x4_slack0.4.stl` | 같은 커플러, 혼 슬롯 두께·폭 +0.4 mm (혼 실측 전 발주용, #59) |
| `foot_pads_x4.stl` | 발 범퍼 4개 |

## 다시 뽑기 (2026-10-16부터 스크립트, #59)

```bash
python cad/tools/export_print_parts.py                          # cad/print_parts/ 에 전부
python cad/tools/export_print_parts.py --out cad/print-orders/20261017   # 발주 기록 폴더에
```

스크립트는 `hopper_params.scad`의 정의부만 임시 파일로 복사해 부품마다 STL을 뽑는다(원본은 고치지 않는다). 다 뽑은 뒤 부품마다 크기, 부피, 열린 모서리 수를 표로 출력하고, 열린 모서리가 있으면 실패한다. OpenSCAD 위치는 환경변수 `OPENSCAD`, PATH, Windows 기본 경로 순서로 찾는다.

**주의:** 9/18에 뽑은 `vane_ring.stl`은 9/19의 서보 장착판 수정 전 형상이었다. 현재 형상은 높이 37 mm, 부피 140.89 cm³다. CAD를 고친 뒤에는 반드시 다시 뽑는다.

### 커플러 두 크기

서보 혼 슬롯(`coupler_horn_t` 2.2, `coupler_horn_w` 9.0 mm)은 실측값이 아니다. 재발주를 피하려고 슬롯을 0.4 mm 키운 `vane_couplers_x4_slack0.4.stl`을 같이 뽑는다. 두 세트를 함께 주문하고 실물 혼에 맞는 쪽을 쓴다. 두 세트를 합쳐도 약 15 cm³다.

### 발주 메모 (한 번에 주문할 때)

- 재료 PETG, 벽 4라인, 인필 40 %(마스터 설계 §10-4).
- `vanes_x4`, `vane_couplers_x4*`, `foot_pads_x4`는 한 파일에 4개가 조립 위치대로 떨어져 있다. 업체에 "개별 부품 4개"라고 알린다.
- 베인과 커플러는 작고 부러지기 쉬우니 예비 1세트씩 같이 주문하는 것을 권한다(재발주 비용이 더 크다).

## 다음 단계

- 슬라이서(Cura/PrusaSlicer)에서 치수·인필 확인 — 재료는 PETG(모터 폐열 대응, PLA 금지), 벽 4라인,
  인필 40%(`docs/design/00-hopper-master-design.md` §10-4).
- 외주 발주 전 §5.1(만능기판 실제 홀수)·§2.4(BNO085 SPI 지원 패드)·§7.4(MG90S 이어 홀 간격) 등
  `docs/design/01-avionics-integration-final.md`의 "확인 포인트"를 실물로 재확인.
- 실제로 발주 넣을 때 그 시점 STL을 `cad/print-orders/<날짜>/`로 복사해서 커밋(`.gitignore` 예외).

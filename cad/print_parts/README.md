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
| `vane_couplers_x4_slack0.4.stl` | 같은 커플러, 혼 슬롯 두께·폭 +0.4 mm (혼 실측 전 발주용, #59) |
| `upper_fairing_half_pos_y.stl`, `upper_fairing_half_neg_y.stl` | 선택: 상부 페어링 반쪽 2개 (외형, #59) |
| `foot_pads_x4.stl` | 발 범퍼 4개 |

## 다시 뽑기 (2026-10-16부터 스크립트, #59)

```bash
python cad/tools/export_print_parts.py                          # cad/print_parts/ 에 전부
python cad/tools/export_print_parts.py --out cad/print-orders/20261017   # 발주 기록 폴더에
```

스크립트는 `hopper_params.scad`의 정의부만 임시 파일로 복사해 부품마다 STL을 뽑는다(원본은 고치지 않는다). 다 뽑은 뒤 부품마다 크기, 부피, 열린 모서리 수를 표로 출력하고, 열린 모서리가 있으면 실패한다. OpenSCAD 위치는 환경변수 `OPENSCAD`, PATH, Windows 기본 경로 순서로 찾는다.

**주의:** 9/18에 뽑은 `vane_ring.stl`은 9/19의 서보 장착판 수정 전 형상이었다. 링 자체 높이(`vane_ring_h` 28 mm)는 같지만 서보 장착판까지 포함한 부품 높이가 28 → 33 mm, 부피가 98 → 131 cm³로 달라졌다. CAD를 고친 뒤에는 반드시 다시 뽑는다.

### 커플러 두 크기

서보 혼 슬롯(`coupler_horn_t` 2.2, `coupler_horn_w` 9.0 mm)은 실측값이 아니다. 재발주를 피하려고 슬롯을 0.4 mm 키운 `vane_couplers_x4_slack0.4.stl`을 같이 뽑는다. 두 세트를 함께 주문하고 실물 혼에 맞는 쪽을 쓴다. 두 세트를 합쳐도 약 15 cm³다.

### 선택 부품: 상부 페어링

`upper_fairing_half_pos_y.stl`, `upper_fairing_half_neg_y.stl`은 외형용 외피 반쪽 2개다(합쳐 약 41 cm³, 약 52 g). 구조에는 필요 없다. 850 mAh 배터리를 쓰면 TWR 약 1.73, 1300 mAh면 약 1.62가 된다. 지름 214 mm라 베드 220 mm 이상 프린터가 필요하다. 기둥에 C클립으로 옆에서 끼운다.

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

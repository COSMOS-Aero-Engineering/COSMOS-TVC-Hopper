# docs/design/ — 설계 문서 색인

| 파일 | 내용 | 상태 |
|---|---|---|
| [`00-hopper-master-design.md`](00-hopper-master-design.md) | **마스터 설계도 (rev C).** 확정사항·아키텍처·치수·질량/추력 예산·서브시스템 상세·전자계통·펌웨어·RL 인터페이스·제작 순서·시험 카드·리스크 | rev C — 비행 컴퓨터를 Teensy 4.0(SolidGeek 오픈소스 포크)으로 교체, 기구/추진은 rev B 계승 |
| [`research-open-source-references.md`](research-open-source-references.md) | rev C 근거 리서치 — SolidGeek/SingleRotorUAV·Bresciani(PX4)·기타 검토 사례 비교, 채택 근거 | 완료 |
| [`general-arrangement.svg`](general-arrangement.svg) | 개략 배치도 (측면도 + 저면도, 치수) | rev B 형상 기준(기구 불변) |
| [`BOM-revC-teensy.md`](BOM-revC-teensy.md) | **구매 리스트(현행).** Teensy/BNO085/양방향DShot ESC 기준 | rev C |
| [`BOM.md`](BOM.md) | 구매 리스트(rev B) — 추진·베인·구조·구속·안전 항목은 **여전히 유효**, 비행컴퓨터 섹션만 rev C 문서로 대체됨 | 부분 supersede |
| [`modelling-notes-ch3.md`](modelling-notes-ch3.md) | 논문 3장(Modelling) 정리 — 운동방정식·베인 공력식, `sim/sim_stage1/hopper_aviary.py`와의 코드 대응표 | 2026-09-17 (재)작성 |
| `references/` | 원문 PDF(SolidGeek/Jacobsen 논문) | — |
| `../../firmware/reference/SingleRotorUAV/` | SolidGeek 펌웨어 vendor-copy(원본 그대로, 출처·라이선스는 `ORIGIN.md`) | — |
| `../../firmware/cosmos/` | 우리 팀이 실제로 고쳐 쓰는 펌웨어(위 vendor-copy 기반) | 착수 전 |
| `../../firmware/singlecopter.param.md` | ArduPilot SingleCopter 파라미터 — **rev C의 대안 경로**(§8.4) | 보존 |
| `../../cad/hopper_params.scad` | **CAD 정본.** EDF 실측(클램프 마운트) 반영, 구조버그 수정 완료. 자세한 워크플로는 `cad/README.md` | rev C, 2026-09-13 |
| [`01-avionics-integration-final.md`](01-avionics-integration-final.md) | **아비오닉스·배선·기계통합 확정판 (rev C.1).** Teensy 핀맵·전원계통·빵판/만능기판 배치·기계 통합·CG 재계산·조립순서·브링업절차 | rev C.1, 2026-09-17 |
| [`02-web-dashboard-design.md`](02-web-dashboard-design.md) | **웹 대시보드·3D 인터페이스 설계도(신규).** 소프트웨어팀 웹 산출물의 목표·아키텍처·CSV 데이터 계약·기술스택 | 신규, 2026-09-18 |
| [`03-control-pipeline-design.md`](03-control-pipeline-design.md) | **제어 파이프라인 심화 설계(신규).** PID/RL 아키텍처(직접비교 vs Residual RL)·3D 물리엔진 전환 로드맵(Stage 1 PoC→Stage 2)·State/Action Space·Domain Randomization 갭 분석·온보드 배포(ONNX/TFLite Micro)·참고 오픈소스 검증 | 신규, 2026-09-18 |
| [`avionics-breadboard.svg`](avionics-breadboard.svg) | **빵판 배치도** (Week 1 벤치 브링업용) — 홀 좌표·점퍼선까지 | rev C.1 |
| [`avionics-perfboard.svg`](avionics-perfboard.svg) | **만능기판 배치도 · 납땜 도면** (비행용) — 홀 좌표·장착홀 53.34×38.10 | rev C.1 |
| [`system-wiring-final.svg`](system-wiring-final.svg) | **전체 결선도**(비행 형상) — 전원 트리·핀맵·하네스 ID | rev C.1 |
| [`mechanical-integration.svg`](mechanical-integration.svg) | **기계 통합도** — 입면(z좌표)·평면(방위), 전자부품이 프린트 구조 어디에 붙는지 | rev C.1 |
| `tools/gen_board_svgs.py` · `tools/gen_system_svgs.py` | 위 도면 4장의 **생성기**. 치수가 바뀌면 스크립트만 고치고 재실행 (`python docs/design/tools/gen_*.py`) | — |
| `../../kicad/` | 아비오닉스 배선 스키매틱 캡처(신규 — 아직 비어있음, `kicad/README.md` 참고) | 착수 전, `semester-roadmap.md` Week 4 |
| `../../data/` | 실험 로그(CSV) | 착수 전 |

## 리비전

- **rev A** (70 mm EDF · 6S · Pixhawk · PVC 동체): 폐기.
- **rev B** (64 mm EDF · 4S · F405/ArduPilot · 오픈 스탠드오프 프레임): 기구·추진·질량예산·시험카드는 **rev C로 계승**.
- **rev C** (rev B 기구 + Teensy 4.0/SolidGeek 포크 + BNO085 + 양방향DShot + ESP32 + 자이로 정차 보정): **현행.**

## 읽는 순서

1. `research-open-source-references.md` — 왜 이 방향인지
2. 마스터 설계도 §0(확정)·§1(근거 요약)·§3(아키텍처)
3. 담당 서브시스템 §6, 특히 §6.5·§6.7·§8(rev C 변경 지점)
4. 구매: `BOM-revC-teensy.md` → 구매 순서대로
5. 제작: §10 → §14(아직 안 정한 것)
6. 시험: §11 — CLAUDE.md 안전 순서와 1:1

## 변경 규칙

- **형상 변경** = 팀 합의 + 마스터 설계도 개정(rev D…).
- **실측값 갱신** = `cad/params.scad`(또는 Onshape) `MEASURED` + 설계도 §4·§5. rev C.1, C.2…

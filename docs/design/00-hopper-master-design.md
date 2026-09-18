# 착륙 호퍼 — 마스터 설계도 (rev C, 2026-09-05)

COSMOS PRJ-01. 이 문서가 기체의 **단일 진실 소스(single source of truth)**다.

## 리비전 이력

| rev | 골격 | 상태 |
|---|---|---|
| A | 70 mm EDF · 6S · Pixhawk · PVC 플리넘 동체 · AUW ~1.6 kg · ₩620k–1.36M | **폐기** — 제작 전, 비용·엔지니어링 부담으로 스케일 다운 |
| B | 64 mm EDF · 4S · F405(ArduPilot) · 오픈 스탠드오프 프레임 · AUW ~0.65 kg · ₩260–420k | **부분 계승** — 추진·구조·치수·질량예산·시험카드는 그대로 rev C로 이어짐. **FC/센서/펌웨어 베이스만 교체됨** |
| **C** | **rev B와 동일한 기체 + 추진, 단 비행 컴퓨터를 Teensy 4.0(SolidGeek/SingleRotorUAV 오픈소스 포크) + BNO085 + 양방향 DShot ESC + ESP32로 교체. 자이로스코픽 정차 보정(Bresciani/PX4) 포함** | **현행** |

> **rev C의 의도**: 딥 리서치([`research-open-source-references.md`](research-open-source-references.md)) 결과,
> 우리와 **거의 동일한 목적·구조**를 가진 기체가 이미 완전한 CAD + 펌웨어 + 89쪽 이론 문서로 공개돼 있다는
> 걸 확인했다(Aalborg University 석사논문, Emil Jacobsen, MIT 라이선스). 이걸 기구·펌웨어의 새 출발점으로
> 삼아 **엔지니어링(기구·전자·저수준 제어) 시간을 최소화**하고, 남는 시간을 소프트웨어(시뮬레이션·RL)에 쓴다.
> 여기에 PX4 코어 개발자 Mathieu Bresciani가 단일 EDF 드론에서 실제로 겪고 해결한 **자이로스코픽 정차
> 커플링** 문제의 해법(로터 RPM 기반 보정)도 같이 이식한다.
> CLAUDE.md 상위 골격(EDF·핀 방식·RL 2단계 로드맵)은 그대로. CLAUDE.md가 처음부터 "저예산 대안"으로
> 열어둔 **Arduino/Teensy 경로**를, 처음부터 직접 짜는 대신 검증된 오픈소스로 실현하는 것 — **이탈이 아니다.**

**부록 자료**: 이 문서 + 관련 리서치·논문 PDF·CAD 링크·펌웨어 원본을 [§16](#16-첨부-자료-모음)에 전부 모아뒀다.

---

## 0. 확정 사항 (Locked)

| # | 항목 | 확정 | 근거 |
|---|---|---|---|
| L1 | 추진 | **64 mm EDF, 4S, 11~12블레이드**, 하향 배기. 정적 추력 1.3~1.45 kgf | rev B 그대로. SolidGeek 논문도 "실전엔 단일 EDF가 더 나은 선택"이라 사후 결론 — 교차검증됨 |
| L2 | 자세제어 | 배기류 속 **제어핀(베인) 4개**, 서보 구동, 짐벌 없음 | CLAUDE.md 핀 방식. SolidGeek·Bresciani 둘 다 동일 방식 |
| L3 | **비행 컴퓨터** | **Teensy 4.0** + **BNO085** IMU + **양방향 DShot(RPM 텔레메트리) 지원 ESC** + **ESP32**(WiFi 텔레메트리). [SolidGeek/SingleRotorUAV](https://github.com/SolidGeek/SingleRotorUAV) 펌웨어를 포크해 프로펄전만 단일 EDF로 수정 | **rev C 핵심 변경.** CLAUDE.md의 "Teensy 대안"을 처음부터 안 짜고 검증된 오픈소스로 실현. ArduPilot/F405 경로는 §8.4에 대안으로 보존 |
| L4 | 구조 | **오픈 스탠드오프 프레임** — 상판(EDF) + 4개 기둥(CF/알루) + 하부 베인 링(베인·다리). 동체 튜브 없음 | rev B 그대로. CAD는 §3.4 참고(SolidGeek Onshape 포크 권장, 자체 `cad/*.scad`는 대안으로 유지) |
| L5 | 아비오닉스·배터리 | 중앙부 기둥에 트레이/스트랩으로 장착, 기류 밖. CG 트림용 세로 이동 | rev B 그대로 |
| L6 | 착륙장치 | **고정형** 다리 4개(전개 서보 없음). 보조 MCU 없음 | CLAUDE.md 단순화 |
| L7 | 스코프 | 1차: 구속 자세 안정화 비교(주력) / 2차: 저고도 홉 반복 (TWR ~2.0로 여유) | rev B 그대로 |
| L8 | 제작 | 3D프린터·전동공구·납땜·CNC 가능. 레이저 커터 없음 | 부장 확정 |
| L9 | 구속 스탠드 | 카메라 삼각대/모노포드 + **저마찰 자유회전 조인트**(십자축 만능조인트+스러스트 베어링 — 사진용 볼헤드 아님) | rev B 확정, 구매 전 정정 반영됨 |
| L10 | **자이로스코픽 정차 보정** | ESC RPM 텔레메트리 + 각속도로 정차 토크를 상쇄하는 피드포워드 항을 레이트 루프에 추가 | Bresciani/PX4 PR #21489 이식. §6.7 |

**아직 안 정한 것 → §14.**

---

## 1. 이 rev의 근거 요약 (전체 논증은 리서치 문서)

`research-open-source-references.md`에 리서치 전체가 있다. 여기선 설계 결정에 직결되는 것만 요약.

### 1.1 SolidGeek/SingleRotorUAV — 왜 이걸 베이스로 삼나

- Aalborg University 석사논문(2021), 문제정의가 우리 프로젝트와 사실상 동일: *"reusable rocket 기술은
  대부분 학교가 접근 불가 → 안전한 축소 플랫폼으로 그 역학을 재현"*.
- **완전한 CAD**(Onshape, 55개 파트, 브라우저에서 즉시 포크 가능) + **완전한 펌웨어**(Teensy 4.0, C++
  전체) + **89쪽 논문**(뉴턴-오일러 동역학 유도, 베인 공력 모델, LQR 제어 설계, 실측 검증 데이터) + 실비행
  영상. **MIT 라이선스.**
- 원본은 추진계가 우리와 다르다(동축 반대회전 오픈프롭 2개, EDF 아님) — 그런데 저자가 논문 토의(8.2절)에서
  본인 입으로 *"실전에서는 단일 모터 덕티드팬(EDF)이 더 나은 선택이었을 것"*이라 결론 냈다. 우리는 처음부터
  단일 EDF를 골랐으니(CLAUDE.md), **CAD·센서·통신·제어 구조는 가져오고 추진계만 원래 계획대로 유지**하면
  저자의 실패를 자동으로 피해간다.
- 부가 소득: 논문의 동역학·베인 공력 방정식을 `sim/hopper_aviary.py`에 그대로 이식 가능 — 시뮬레이션(=RL
  준비) 착수 시간도 앞당겨진다. 이건 "엔지니어링 시간을 깎는" 게 아니라 **정확히 우리가 쓰고 싶은 소프트웨어
  작업의 기반을 앞당기는 것.**

### 1.2 Bresciani(PX4 코어 개발자) — 왜 자이로스코픽 정차 보정을 추가하나

- 90 mm 단일 EDF + 베인4 드론을 직접 만들어 날렸고, [PX4 PR #21489](https://github.com/PX4/PX4-Autopilot/pull/21489)에서:
  > *"빠르게 도는 단일 로터의 자이로스코픽 토크가 롤-피치를 강하게 커플링시켜서 튜닝을 거의 불가능하게
  > 만든다."*
- 해법: 로터 RPM(ESC 텔레메트리) × 각속도로 정차 토크를 실시간 상쇄하는 피드포워드 항. PX4 전체를 채택하지
  않아도 **이 수식만 Teensy 코드에 이식 가능** — SolidGeek 코드가 이미 DShot으로 RPM을 읽고 있어 인프라가
  갖춰져 있다.
- 우리 64mm EDF도 "빠르게 도는 강체 로터"라 같은 문제를 겪을 수 있다 — rev B엔 없던 리스크였는데 이번에
  발견해서 지금 대응을 박아둔다(§6.7, §12).
- 독립적 교차검증: Bresciani 본인이 같은 포럼에서 *"CG를 더 높였더니 안정성이 좋아졌다"*고 언급 — 우리가
  이미 §5.3에서 채택한 "CG를 최대한 높인다" 원칙과 정확히 일치.

### 1.3 왜 이게 "설계 이탈"이 아닌가

CLAUDE.md는 처음부터 "저예산 대안: Arduino/Teensy + 자체 PID"를 명시해뒀다. rev C는 그 대안을 **직접
짜지 않고, 검증되고 문서화되고 실비행까지 끝난 오픈소스로 실현**하는 것 — 골격(EDF·베인·RL 2단계 비교)은
전혀 안 바뀌었다.

---

## 2. 참고한 선행 사례

| 사례 | 링크 | 우리가 가져온 것 |
|---|---|---|
| **SolidGeek/SingleRotorUAV** (Emil Jacobsen, Aalborg Univ. 석사논문) | [GitHub](https://github.com/SolidGeek/SingleRotorUAV) · [Onshape CAD](https://cad.onshape.com/documents/e833cc23e7ea826c94a116f3/w/362fc8aca947f44850932dcd/e/4721094f67251fa796bbdcbc) · [영상](https://youtu.be/jJKNR2vzTVY) · 논문 PDF(`docs/design/references/`) | **Teensy 4.0 펌웨어 전체(센서·통신·제어), CAD 골격, 동역학·베인 공력 방정식, LQR 제어 구조.** 추진계(동축 오픈프롭)는 안 가져옴 — 단일 EDF 유지 |
| **Mathieu Bresciani (PX4 코어 개발자)** | [Printables](https://www.printables.com/model/722967-ducted-fan-thrust-vectoring-drone) · [PX4 PR #21489](https://github.com/PX4/PX4-Autopilot/pull/21489) · [영상](https://www.youtube.com/watch?v=u2cETOyuJ20) | **자이로스코픽 정차 보정 로직**(로터 RPM 피드포워드), "CG는 높을수록" 교차검증 |
| **bribro12 — SpaceX-inspired EDF rocket** | hackster.io/bribro12 | 추진계 실측 근거(70mm급 EDF 스펙), "내부 배선이 기류 방해" 교훈 — 오픈프레임 채택 근거 |
| **cjhagemeyer — 64mm EDF용 3축 TVC** | printables.com/model/803977 | 64mm 스케일 베인 하우징 기하 참고 |
| **K-9 TVC Hopper Test Vehicle** | printables.com/model/164897 | 4다리 배치 기하 참고 |
| **fdiwth/tvc-drone** (검토 후 기각) | github.com/fdiwth/tvc-drone | 참고 안 함 — 코액시얼+짐벌 방식(우리와 다른 액추에이션), 커스텀 PCB 필요(엔지니어링 시간 증가), 비행 성공 미검증, 제작자 본인이 "따라하지 말라"고 명시 |
| Carholt et al. 2016 (MED 컨퍼런스) | [전문 PDF](http://kth.diva-portal.org/smash/get/diva2:1672182/FULLTEXT01) | SolidGeek 논문의 선행연구 — "SR-UAV"라는 학술 하위분야가 실재한다는 근거(발표용) |

---

## 3. 시스템 아키텍처

### 3.1 전체 배치 — 오픈 스탠드오프 프레임 (rev B와 동일 형상)

```
              ╭───────────╮   상단 베일(3 mm 스틸봉) = 손잡이 + M3 텐서 걸이
             ╱             ╲
        ┌───┴───────────────┴───┐  상판 (프린트/합판 3~4 mm)
        │   [ 64 mm EDF, 하향 ]  │  흡기 ▲ 위(상판 위 개방) / 배기 ▼ 아래
        └──┬──┬───────────┬──┬──┘
           │  │           │  │       ← 기둥 4개 (M4 CF튜브/알루, 길이 ~200 mm)
           │ ┌┴───────────┴┐ │
           │ │ 배터리 4S    │ │       ← 중앙 트레이: 배터리 / Teensy4.0 / BNO085 /
       ○───┼─┤ Teensy·ESC   ├─┼───○     ESP32 / DShot ESC. 기류 밖. ±20mm CG 트림
           │ └┬───────────┬┘ │
           │  │           │  │
        ┌──┴──┴───────────┴──┴──┐  하부 베인 링 (프린트)
      ╱ │  ✚   ✚   ✚   ✚        │ ╲     베인 4개 @90°, EDF 배기면 −20~30 mm
    다리 │  서보4 (방사, 기류밖)  │ 다리   ±15° 하드스톱
      ╲ └───────────┬───────────┘ ╱
                  ▼▼▼▼                배기(하향)
       ▂▂▂         제트         ▂▂▂    발 4개, 배기면 −140 mm, 발원 ~360 mm
```

기구 형상(치수·질량·TWR)은 **rev B와 동일** — 바뀐 건 상판/트레이 안에 들어가는 전자부품 구성뿐이다.
따라서 §4~5(치수·질량예산)는 그대로 유효하고, 아래 §6.5·§6.7·§7·§8만 이번 rev의 실제 변경 지점이다.

### 3.2 CAD 소스 — 어디서 시작하나

| 경로 | 방법 | 권장 |
|---|---|---|
| **A. SolidGeek Onshape 포크** | [원본 문서](https://cad.onshape.com/documents/e833cc23e7ea826c94a116f3/w/362fc8aca947f44850932dcd/e/4721094f67251fa796bbdcbc)를 COSMOS Onshape 계정으로 "Copy" → 모터마운트를 F40 오픈모터용에서 우리 EDF 마운트로 교체 → 나머지(Vector Fin=베인, Leg/Leg Piston, Top, PCBS 마운트)는 치수만 조정 | **1순위** — 브라우저 기반이라 진입장벽 낮고, "Test Bench Assembly" 파트 스튜디오도 있어 구속 스탠드 설계도 참고 가능 |
| B. 자체 파라메트릭(`cad/params.scad` 등) | rev B에서 이미 작성한 OpenSCAD 스케치 계속 사용 | 대안 — Onshape 포크가 안 풀리거나 팀이 OpenSCAD에 더 익숙하면 |

두 경로 다 **최종 결과물의 물리 사양(치수·질량·TWR·베인 크기)은 §4~6.3에 이미 고정된 값을 따라야 한다** —
CAD 툴만 다를 뿐, 형상 스펙은 동일.

---

## 4. 좌표계 · 전체 치수 (rev B와 동일 — 그대로 유효)

| 치수 | 기호 | 값 (DESIGN) | MEASURED | 비고 |
|---|---|---|---|---|
| EDF 하우징 외경 | `edf_housing_od` | 67 mm (가정) | ___ | 64 mm 팬 + 립. 실측 필수 |
| EDF 마운트 볼트 PCD | `edf_mount_pcd` | 76 mm (가정) | ___ | 제품마다 다름 |
| 기둥 길이(상판~베인링) | `col_len` | 200 mm | ___ | 아비오닉스 스택 높이로 조정 |
| 상판 두께 | `top_plate_t` | 4 mm | ___ | |
| 베인 링 높이 | `vane_ring_h` | 28 mm | ___ | |
| EDF 배기면 → 베인 피벗축 | `vane_gap_below_exit` | 22 mm | ___ | |
| EDF 배기면 → 발 바닥 | `foot_below_exit` | 140 mm | ___ | |
| 전체 높이(베일 팁~발) | `H_total` | ≈ 350 mm | ___ | |
| 발 원 지름 | `foot_circle` | 360 mm | ___ | |
| 다리 길이(로드) | `leg_len` | 210 mm | ___ | |
| 다리 스플레이 | `leg_splay` | 33° | ___ | |
| 베인 시위/스팬/두께 | — | 25 / 45 / 2.5 mm | ___ | §6.3 |
| 베인 최대 편향(기계) | `vane_deflect_max` | ±15° | ___ | |
| CG 위치(배기면 기준) | `x_cg` | 140~180 mm 목표 | ___ | |

정본: SolidGeek Onshape 포크 사용 시 그 모델, 자체 CAD 사용 시 `cad/params.scad`. 이 표는 양쪽 다 지켜야
할 목표 스펙.

---

## 5. 질량 · CG · 추력 예산 (rev B 수치 유지, 아비오닉스만 소폭 재계산)

### 5.1 질량 예산 (rev C)

| 항목 | 질량 (g) | rev B 대비 | 비고 |
|---|---:|---|---|
| 64 mm EDF 팬+모터 (4S) | 160 | 동일 | |
| 60 A ESC (4S, **양방향 DShot**) | 40 | 동일 | 텔레메트리 지원 여부는 무게에 안 영향 |
| 4S 1300 mAh 65C LiPo | 150 | 동일 | |
| **Teensy 4.0** | 5 | F405(12g) 대비 **-7** | 보드가 훨씬 작음 |
| **BNO085 브레이크아웃** | 3 | (신규) | |
| **ESP32 개발보드** | 10 | (신규) | |
| RC 수신기 | 6 | 동일 | |
| 서보 4× MG90S (9 g) | 55 | 동일 | |
| 베인 링 + 베인4 + 링키지 (프린트) | 70 | 동일 | |
| 상판 + 베일 + 기둥4 + 트레이 | 90 | 동일 | |
| 착륙 다리 4 | 70 | 동일 | |
| 배선·스트랩·타이·에폭시 | 50 | +5 (배선 부품 늘어남) | |
| **합계 (AUW)** | **≈ 660 g** | **+10 g** | 오차범위 내, TWR 영향 미미 |

### 5.2 TWR — rev B와 사실상 동일

- 64 mm/4S 정적 추력 1,300 gf 기준 → **TWR ≈ 1,300 / 660 ≈ 1.97.** (rev B: 2.0)
- 구속 시험(≥1.15)·저고도 홉(≥1.6) 기준 모두 여전히 여유 있게 충족.

### 5.3 CG · 관성 — rev B와 동일 원칙, Bresciani 교차검증 추가

- 목표 CG: 배기면 위 140~180 mm. 트리밍: 중앙 트레이 ±20 mm 슬라이드.
- **Bresciani가 독립적으로 검증**: "CG를 높였더니 안정성이 좋아졌다" — 같은 원칙, 다른 팀, 같은 결론.
- 관성 텐서 측정 방법(2선/비틀림 진자)은 rev B와 동일. 논문 3장의 관성 추정 방법론도 참고 가능.

---

## 6. 서브시스템 상세 설계

§6.1(프레임)·§6.2(EDF)·§6.3(베인)·§6.4(다리)·§6.6(구속 인터페이스)는 **rev B와 완전히 동일** — 아키텍처가
안 바뀌었으므로 재수록하지 않는다(BOM.md·이전 rev 참고). 아래는 **rev C에서 바뀌거나 새로 생긴 것만.**

### 6.5 아비오닉스 · 배선 (rev C — 교체)

- **비행 컴퓨터**: Teensy 4.0. SolidGeek 코드(`firmware/reference/SingleRotorUAV/`에 원본 vendor-copy
  있음)를 포크해서 사용.
- **IMU**: BNO085 (BNO080 핀호환 후속, SPI 버그 수정판). I2C 또는 SPI로 Teensy에 연결. 센서퓨전이 칩
  내장이라 Teensy는 쿼터니언을 바로 받는다 — 별도 상보/칼만 필터를 자세추정에 안 짜도 됨(그 대신 위치추정용
  칼만필터는 논문 5장 구조를 따름).
- **고도/위치 센서 (STAGE 3+ 전용, STAGE 1엔 불필요)**: VL53L1X ToF 라이다(고도), PMW3901 광류(수평
  위치) — SolidGeek 코드에 드라이버 이미 포함. 구속 시험 단계에선 배선만 해두고 안 써도 무방.
- **통신**: ESP32를 Teensy와 UART로 연결, WiFi로 노트북(지상국)과 텔레메트리·로깅. RC 수신기는 별도로
  Teensy에 직결(페일세이프/수동 오버라이드).
- **배선 원칙**: rev B와 동일 — 전부 기류 밖. 트레이 안에서 Teensy-BNO085-ESP32-ESC 간 배선 완결.
- **질량 대칭**: rev B와 동일 원칙.

### 6.7 자이로스코픽 정차 보정 (rev C — 신규)

- **문제**: 64 mm EDF 팬은 강체 로터가 고속 회전 — 각운동량이 커서, 기체가 롤/피치로 회전할 때 자이로스코픽
  토크가 발생해 두 축을 서로 커플링시킨다. Bresciani(PX4)에 따르면 이게 "튜닝을 거의 불가능하게" 만들 수
  있음.
- **해법(이식 대상)**: PX4 PR #21489의 피드포워드 항 —
  ```
  τ_precession ≈ H_rotor × ω_body   (H_rotor = 로터 각운동량 = I_rotor·Ω, ESC RPM 텔레메트리로 Ω 획득)
  ```
  레이트 컨트롤러 출력에 `-τ_precession`를 더해 상쇄. Teensy 쪽엔 `src/dshot.cpp`가 이미 양방향 DShot로
  RPM을 읽는 구조라 큰 개조 없이 추가 가능.
- **대안/병행**: SolidGeek의 LQR(전상태 궤환)은 이 커플링을 명시적으로 모델링하진 않지만, 게인행렬이 암묵적
  으로 어느 정도 흡수한다(논문 8.1.1절 참고, 실측에서 큰 문제 없이 비행 성공). **정차 보정 없이 LQR만으로도
  일단 시도해보고, TC-3에서 롤-피치 커플링이 실제로 문제되면 그때 보정 항을 추가하는 순서를 권장** — 처음부터
  두 개를 다 구현하려 하지 않는다.
- **필요 조건**: ESC가 RPM을 리턴해야 하므로 §BOM A2(양방향 DShot 필수)와 직결.

---

## 7. 전자 계통 · 배선도 (rev C — 교체)

```
        4S LiPo (14.8 V)  XT60
            │
     ┌──────┴──────┐  물리 킬스위치 (인라인)
     └──────┬──────┘
     ┌──────┴──────────────────┐
  60A ESC(양방향DShot) ──3φ──▶ 64mm EDF 모터   (메인 전류, 40~52 A)
     │   └─ BEC 5~6V ──┐        RPM 텔레메트리 ─┐
     │                 │                        │
  Teensy 4.0 ◀─────────┴────────────────────────┘  (DShot 신호선 1개로 제어+RPM 왕복)
     │  ├─ I2C/SPI ── BNO085 (IMU, 쿼터니언)
     │  ├─ PWM ×4 ── 베인 서보 (Fwd/Right/Back/Left)
     │  ├─ UART ── ESP32 (WiFi 텔레메트리 → 노트북 지상국)
     │  ├─ RC 입력 ── 수신기 (SBUS 또는 Spektrum DSM 시리얼, 킬 채널 포함)
     │  └─ (STAGE3+) I2C ── VL53L1X / SPI ── PMW3901
```

- BEC 전원과 서보 전원 공통 레일 확인, 필요 시 UBEC(A5)로 이중화.
- BNO085는 모터·ESC 전류경로에서 최대한 띄워 장착(SolidGeek 논문이 지적한 자기간섭 회피 — 단, 우리는
  자력계 자체를 안 쓰므로(자이로 적분) 영향은 제한적이지만 진동원에서 거리는 확보).
- ESP32 로깅이 곧 PID/RL 비교 실험의 원자료가 된다 — 배선 우선순위 높게.

---

## 8. 비행 제어 설정

### 8.1 Teensy/SolidGeek 포크 (주 경로, rev C)

1. `firmware/reference/SingleRotorUAV/`(원본 vendor-copy)를 기준으로 실제 빌드용 포크 생성.
2. **프로펄전 믹서 단순화**: 원본은 `write_motor()`를 2회(듀얼 모터) 호출 — 우리는 1회(단일 EDF)로. 이 부분이
   가장 큰 코드 수정 지점이지만, 오히려 원본보다 **로직이 단순해진다**(모터 간 밸런싱 로직 삭제 가능).
3. 베인 믹서(`write_servo(0..3, ...)`)는 원본 그대로 사용 가능 — 우리와 동일한 4베인 구조.
4. IMU 드라이버(`BNO080.cpp`)는 BNO085도 핀/레지스터 호환이라 그대로 사용.
5. DShot 드라이버(`dshot.cpp`)에 §6.7의 정차 보정 항을 추가(선택, TC-3 결과 보고 판단).
6. 제어 구조는 원본의 `control_hover()`(LQR, `output = K * error`)를 그대로 시작점으로 — 우리 기체
   질량·관성으로 게인행렬만 재설계(§8.3).
7. **RL 이식 지점**: `control_hover()`의 `output = K * error;` 한 줄을 나중에 "정책망 추론 호출"로
   교체하는 구조를 처음부터 염두에 두고 리팩터링.

### 8.2 튜닝 절차 (구속 M1)

1. 논문 4장(Control) 방식대로 선형화 모델 → LQR 게인 1차 설계(가중행렬 Q, R은 논문 사례를 시작값으로).
2. 구속 상태에서 게인 낮게 시작 → 발산 없는지 확인 → 점진적으로 상향.
3. TC-3에서 롤-피치 커플링(자이로 정차) 관찰 → 문제되면 §6.7 보정 항 추가.
4. 모든 세션 ESP32로 로깅(§7) — RL 비교의 baseline 데이터.
5. **참고**: 논문 8.1.3절 — 적분기 anti-windup 한계를 너무 낮게 잡으면 정상상태오차가 남는다는 실측 교훈.
   우리도 적분 게인·리밋을 설계 초기부터 로깅하며 잡을 것.

### 8.3 게인 설계 시작값

- SolidGeek 논문 4.1.2절(LQR)·Appendix의 Q/R 가중치, K 게인행렬을 1차 참고. 우리 기체(660 g, rev B와
  다른 질량·관성)에 맞게 반드시 재설계 — 그대로 쓰면 안 됨(논문 8.1.1절도 "질량이 다르면 언더댐프"된다고
  명시).
- 순수 PID로 시작하고 싶으면 balancing-beam 시작값(Kp 1.3 / Ki 5e-4 / Kd 0.9)도 여전히 유효한 대안.

### 8.4 대안 경로 — ArduPilot SingleCopter (보존)

rev B에서 검증해둔 F405 WING + ArduPilot SingleCopter 경로는 **폐기하지 않고 대안으로 보존**한다.
Teensy/SolidGeek 포크가 예상보다 막히면(예: BNO085 드라이버 이식 실패, LQR 튜닝이 너무 오래 걸림)
언제든 전환 가능하도록 `firmware/singlecopter.param.md`를 그대로 유지한다. 두 경로 모두 같은 기구(§3~6)를
쓰므로 기구 작업은 낭비되지 않는다.

---

## 9. 시뮬레이션 · RL 인터페이스 요구사항

§9.1(측정 항목)·§9.2(입출력 스펙)·§9.3(도메인 랜덤화)·§9.4(시뮬레이터)는 **rev B와 동일** — 바뀐 건
동역학 모델의 출처뿐이다.

- **동역학 모델**: 논문 3장(뉴턴-오일러 강체 회전, 베인 양력/항력 방정식, 서보-베인 동특성)을 `sim/hopper_aviary.py`의
  물리 모델로 이식. 처음부터 유도할 필요 없음 — 계수(질량·관성·베인 면적 등)만 우리 기체 실측값으로 교체.
- **정책 입출력**은 rev B와 동일하게 고정:
  ```
  관측 obs (12): 자세[r,p,y] · 각속도[p,q,r] · (자유모드) [vz,z] · 이전행동[thr,δr,δp,δy]
  행동 act (4):  throttle∈[0,1] · δ_roll,δ_pitch,δ_yaw∈[-1,1]  → 믹서 → 4베인+모터
  ```
  Teensy 코드의 `control_hover()` 교체 지점(§8.1-7)이 이 인터페이스와 정확히 맞물리게 설계.
- 도메인 랜덤화 범위(질량 ±10%, CG ±12mm, 관성 ±20%, 추력 ±8%, 베인유효도 ±25%, 서보지연 20~60ms 등)는
  rev B 표 그대로 유효.

---

## 10. 제작 순서 (rev C)

1. **핵심 부품 먼저 구매** — EDF, Teensy 4.0, BNO085, 양방향 DShot ESC (BOM-revC-teensy.md §구매순서).
2. **CAD 착수** — SolidGeek Onshape 문서 Copy(포크) → 모터마운트 교체 → 실측값 반영(§3.2, §4).
3. **펌웨어 포크** — `firmware/reference/SingleRotorUAV/` 원본을 베이스로 실 빌드용 리포/브랜치 생성,
   Teensy 4.0 대상 컴파일 확인(하드웨어 없이도 가능).
4. **프린트 (PETG)** — 상판 → 베인링+베인4 → 기둥 소켓 → 트레이 → 다리 발.
5. **베인링 조립** — CF 스파, 부싱, 서보, 링키지, ±15° 스톱 확인.
6. **기둥 결합** — 상판↔베인링, 직각·비틀림 확인.
7. **다리** — 재단·접착·볼트.
8. **전자 조립** — Teensy·BNO085·ESP32·DShot ESC·RX. 배선 전부 기류 밖.
9. **질량·CG·관성 측정** → `sim/params.yaml`.
10. **밸런스** — CG 트림.
11. **소프트웨어 셋업** — 펌웨어 플래시, RC/DShot/BNO085 개별 검증(TC-1 전 단계).
12. **M1 삼각대 마운트** 준비, 킬 2중 확인.
13. **시험 카드** (§11).

---

## 11. 시험 카드 (CLAUDE.md 안전 순서와 1:1, rev B와 동일 — 도구만 Mission Planner→Teensy 시리얼/ESP32 지상국으로 교체)

| TC | 이름 | 구속 | 합격 기준 | 중단 |
|---|---|---|---|---|
| **TC-0** | 스로틀 온리 | M1 | 20~60% 스로틀에서 진동 RMS < X, 이상음/열 없음, EDF 마운트 유격 0 | 이상진동·연기·유격 |
| **TC-1** | 베인 방향 검증 | M1 | 수동 입력 → 롤=Fwd/Back, 피치=L/R, 요=4캔트. 부호 일치 | 반대부호 → 믹서 부호 수정 |
| **TC-2** | 베인 힌지모멘트·제어효과 실측 | 베인링만 스탠드 | 15° 유지 시 서보 온도 <45°C, ∂M/∂δ 기록 | 서보 스톨·과열 |
| **TC-2.5** *(신규)* | **자이로 정차 커플링 관찰** | M1 | 스로틀 고정 후 롤 스텝 입력 → 피치 응답 크기 기록. 크면 §6.7 보정 필요 판단 | — |
| **TC-3** | 자세 안정화(LQR/PID) | M1 | ±10° 초기오프셋 복원시간 τ, 오버슈트, 정상오차 기록. 발산 없음 | 리미트사이클 발산 |
| **TC-4** | 외란 강인성 | M1 | 임펄스 외란·배터리 새그 복원. baseline 확정 | — |
| **TC-5** | RL 정책 비교 | M1 | TC-3·4와 동일 조건 반복, 비교표 (발표 핵심) | 정책 이상 → 즉시 킬 |
| **TC-6** | 추력·지면효과 | M2 | 호버 스로틀 %, 지면효과 특성 | — |
| **TC-7** | 저고도 홉 (반복) | M3 → 점차 완화 | STAGE 3 데이터 확보 + 추력 실측 전제 | 자세 발산·하드랜딩 |

---

## 12. 리스크 레지스터

| 리스크 | 출처 | 대응 |
|---|---|---|
| **자이로스코픽 정차 커플링 — 튜닝을 거의 불가능하게 만들 수 있음** *(rev C 신규)* | Bresciani, PX4 PR #21489 | TC-2.5로 조기 관찰, §6.7 보정 항 이식 경로 확보(ESC RPM 텔레메트리 필수 — BOM에 반영됨) |
| 동축/듀얼모터로 토크 상쇄 시도는 실전에서 실패 | SolidGeek 논문 8.2절 | 우리는 단일 EDF라 해당 없음 — "우리가 옳았다"는 근거로만 기록 |
| IMU-모터 자기간섭으로 요 드리프트 | SolidGeek 논문 8.1.1절 | 자력계 미사용(자이로 적분)으로 이미 회피 |
| 착륙 단계는 호버 게인으로 부족 | SolidGeek 논문 8.1.2절 | TC-7 설계 시 착륙 전용 게인 스케줄 고려 |
| 조립 후 베인·다리 간섭 | BPS.Space | CAD 스윕 볼륨 확인(Onshape/`cad/` 양쪽 다) |
| 서보 피로·핀조인트 응력 | arXiv 2509.00061 | 금속기어, CF 스파, TC-2 실측 |
| **Teensy 포크가 예상보다 막힘** *(rev C 신규)* | — | §8.4 ArduPilot/F405 대안 경로 보존 — 기구는 공유되므로 전환 비용 낮음 |
| sim 낙관 편향 | ROBOMECH | DR 범위 넓게, STAGE 3에서 실측 |
| 요 축 권한 약함 | SingleCopter/모노콥터 공통 | 저게인/구속, 발표에 한계 명시 |
| LiPo 화재 / EDF 흡입 | 안전 일반 | rev B 안전 원칙 그대로(세이프백·1C·물리킬·그릴·보안경) |
| 오픈프레임 = 부품 노출 | rev B 고유 | 시험구역 스크린, 예비 기체, 배선 절연 |

---

## 13. BOM

**상세 구매 리스트 → [`BOM-revC-teensy.md`](BOM-revC-teensy.md)** (rev C 현행, 총계 ≈ ₩350k–620k).

`BOM.md`(rev B)는 추진·베인·구조·구속·안전 항목은 여전히 유효하나, **비행컴퓨터/센서/통신 섹션(B)은
BOM-revC-teensy.md로 대체됨** — 그쪽 문서에 상단에 명시해둠.

---

## 14. 아직 안 정한 것

| 항목 | 필요 정보 | 언제 |
|---|---|---|
| 64 mm EDF 정확 모델·실측 추력·하우징 치수 | 구매·실측 + 추력 스탠드 | 제작 1 / STAGE 1 |
| CAD 경로 — SolidGeek Onshape 포크 vs 자체 `cad/*.scad` | 팀 CAD 숙련도·선호 | 제작 2 전 |
| 수신기 — 기존 Spektrum 재사용 vs 신규 SBUS 구매 | 재고 확인 | 구매 전 |
| 정차 보정을 처음부터 넣을지, TC-2.5 보고 판단할지 | TC-2.5 결과 | STAGE 1 |
| LQR vs PID 중 어느 걸 "baseline"으로 삼을지(혹은 둘 다 비교) | 팀 논의 | STAGE 1 착수 전 |
| 최종 CG·관성 | 조립 후 측정 | 제작 9 |
| 홉 고도 상한·시점 | STAGE 3 결과 | STAGE 4 |
| 쉬라우드(외피) 부착 여부 | 발표 외형 선호 | STAGE 4 전(선택) |

---

## 15. 참고문헌

- Jacobsen, E.B. *Modelling and Control of Thrust Vectoring Mono-copter*, Aalborg University 석사논문, 2021 — 전문: `docs/design/references/`, 코드: `firmware/reference/SingleRotorUAV/`, [GitHub](https://github.com/SolidGeek/SingleRotorUAV), [Onshape](https://cad.onshape.com/documents/e833cc23e7ea826c94a116f3/w/362fc8aca947f44850932dcd/e/4721094f67251fa796bbdcbc)
- Bresciani, M. — [단일 EDF TVC 드론(Printables)](https://www.printables.com/model/722967-ducted-fan-thrust-vectoring-drone) · [PX4 PR #21489](https://github.com/PX4/PX4-Autopilot/pull/21489) · [영상](https://www.youtube.com/watch?v=u2cETOyuJ20)
- Carholt, O.C. et al. *Design, modelling and control of a Single Rotor UAV*, MED 2016 — [전문 PDF](http://kth.diva-portal.org/smash/get/diva2:1672182/FULLTEXT01)
- bribro12, *SpaceX inspired EDF rocket* — hackster.io/bribro12
- cjhagemeyer, *3-axis thrust vectoring for 64mm EDF* — printables.com/model/803977
- K-9 TVC Hopper Test Vehicle — printables.com/model/164897
- *Design and Testing of a Low-Cost 3D-Printed Servo Gimbal for TVC* — arXiv:2509.00061
- ArduPilot, *SingleCopter and CoaxCopter*(§8.4 대안 경로용) — ardupilot.org/copter/docs/singlecopter-and-coaxcopter.html
- utiasDSL, *gym-pybullet-drones* — github.com/utiasDSL/gym-pybullet-drones
- 전체 리서치 근거: [`research-open-source-references.md`](research-open-source-references.md)

---

## 16. 첨부 자료 모음

| 자료 | 위치/링크 |
|---|---|
| 이 마스터 설계도 | `docs/design/00-hopper-master-design.md` (이 파일) |
| 리서치 전체(비교표·리스크·의사결정 근거) | `docs/design/research-open-source-references.md` |
| 구매 리스트(rev C) | `docs/design/BOM-revC-teensy.md` |
| 구매 리스트(rev B, 기구 파트는 유효) | `docs/design/BOM.md` |
| 개략 배치도 | `docs/design/general-arrangement.svg` |
| **SolidGeek 논문 전문(PDF, 89쪽)** | `docs/design/references/Jacobsen2021_Modelling-and-Control-of-Thrust-Vectoring-Mono-copter.pdf` |
| **SolidGeek 펌웨어 원본(vendor copy)** | `firmware/reference/SingleRotorUAV/` (`ORIGIN.md`에 출처·라이선스·수정계획 명시) |
| SolidGeek CAD(Onshape, 라이브) | https://cad.onshape.com/documents/e833cc23e7ea826c94a116f3/w/362fc8aca947f44850932dcd/e/4721094f67251fa796bbdcbc |
| ArduPilot 대안 경로 파라미터 | `firmware/singlecopter.param.md` |
| 자체 CAD 스케치(대안) | `cad/params.scad`, `cad/top_plate.scad`, `cad/vane_ring.scad` |

---
*rev C — 비행 컴퓨터/펌웨어 베이스 교체 확정. 기구·추진·질량·시험절차는 rev B에서 계승.
다음 갱신은 실측값 반영(rev C.1) 또는 CAD 경로 확정 후.*

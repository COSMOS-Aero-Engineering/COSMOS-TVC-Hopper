# TVC-Hopper 구매와 통합 시험

2026-11-08 기준. 부장은 10월 31일 이후 추가 확보한 물품이 없다고 확인했다. [구매 대장](hopper-procurement-20261108.csv)은 수량·호환 조건과 검색어를 한 줄에 모은다. 가격 칸의 미확인은 견적에 합산하지 않는다.

## 첫 구매

1. **D1/D2 탄소관**. 외경 6, 내경 4, 길이 1000 mm 튜브 2본. 기둥 212 mm ×4, 다리 중심선 약 153 mm ×4다. 소켓에 맞춰 다리의 절단 길이를 확정한다. R2 선반 소켓은 Ø6.6 mm다. [판매 상세](http://www.easycomposites.cn/products/carbon-fiber-tube/glossy-3k-woven-finish-6mm-4mm-1m.aspx)는 단가 ¥64.40과 즉시 발송 문구를 표시했다. 2본 표시가 합은 **¥128.80**이다. [카테고리](http://www.easycomposites.cn/Categories/Carbon-Fibre-Tubes/1m-Woven-Finish-3k-Glossy-Carbon-Fibre-Tube.aspx)는 ¥99.45로 달랐다. 주문 전 단가, 세금, 칭다오 운임·도착일을 판매자에게 확인한다. 직조관의 표기 질량은 24.3 g/m다. 기존 BOM 추정 질량은 조립 후 실측으로 교체한다.
2. **대체 후보**. 같은 규격의 [인발 탄소관](http://www.easycomposites.cn/products/carbon-fiber-tube/pultruded-carbon-fibre-tube-6mm-4mm-1m.aspx)은 상세 페이지에 ¥51.50, 품절로 표시됐다. Taobao 다중 옵션의 최저 표시가는 6×4×1000 mm 옵션의 견적으로 확인할 수 없었다.
3. **베인 축**. Ø3 mm 속 찬 봉은 60 mm ×4가 필요하다. 보유 여부를 확인한다. [1 m 봉](http://www.easycomposites.cn/products/carbon-fibre-rod/3mm-carbon-fibre-rod-1m.aspx)은 ¥25.00, 품절로 표시됐다. 대장의 중국어 검색으로 다른 판매처를 찾을 때 원형 단면·길이·수량을 확인한다.
4. **서보**. SG90 2개로 무추력 시험을 진행한다. 완성 기체는 동일 모델 4개가 필요하다. [MG90S](https://towerpro.com.tw/product/mg90s-3/)로 확정하면 4개와 선택 예비 2개가 기준이다. 모델 확정 전 구매를 보류한다. 다른 서보의 보정값을 적용하지 않는다.
5. **UBEC와 수신기**. [UBEC 5A 후보](https://www.hobbywing.com/products/ubec-5a93)는 50×17×10 mm여서 기존 43×17 mm 배치 가정과 다르다. 바닥 실측·간섭·트림 검토가 필요하다. [FS-iA6B](https://www.flysky-cn.com/ia6b-canshu)는 [FS-i6X 송신기](https://www.flysky-cn.com/fsi6x) 호환성과 PWM 5채널을 함께 확인한다. 두 제조사 페이지에서 현지 도착일이나 실구매 가격은 확인하지 못했다.
6. **연장선·서보의 해외 가격 참고**. [Futaba 150 mm 10개 묶음](https://hobbyking.com/futaba-150mm-26awg-servo-extension-lead-10pcs.html)은 USD 3.99이며 조회 화면에서 배송 가능한 창고가 없었다. [Botland MG90S](https://botland.store/micro-servos/24408-towerpro-mg90s-micro-analogue-servo-with-metal-gear.html)는 개당 EUR 15.50을 표시했으나 사업자 계정이 필요하다. 학교의 중국 내 결제·배송 견적으로 쓰지 않는다. 표준 나사류는 [미스미 중국 M3 선택기](https://www.misumi.com.cn/vona2/result/?Keyword=%E8%9E%BA%E9%92%89M3) 또는 대장 검색 링크에서 실제 길이·나사산·묶음 수량을 선택한다.

[제품 사양과 수량](../design/BOM-revC-teensy.md), [체결 위치](../../cad/README.md), [배선·직결 구동](../design/01-avionics-integration-final.md), [실물 재고 기록](https://github.com/COSMOS-Aero-Engineering/COSMOS-TVC-Hopper/issues/242)을 대조했다. R2의 31개는 이미 입고됐다. C4 피아노선은 직결이 불가능할 때의 대안이다. 소모품·시험대는 실물 재고와 구조 확정 뒤 부족분만 산다.

## 팀 간 전달물

| 시험 순서 | HW 담당이 남길 자료 | SW 담당의 산출물 | 통과 근거 |
|---|---|---|---|
| 핀·전원 | 실제 IMU 패드, RC 출력 전압, UBEC 모델·전압 | 핀/타이머 사용표와 부팅 상태 | I2C 18/19와 기존 RC CH1/2 충돌 해소, 전원 경로 검토. [#245](https://github.com/COSMOS-Aero-Engineering/COSMOS-TVC-Hopper/issues/245) |
| 무추력 벤치 | 알려진 방향의 IMU 자세, 서보마다 명령 µs·실측 각도·부호, 수신기 킬·단절 로그 | 센서→제어→서보 보고 및 원시 데이터 보존 | 잘못된 부호·오래된 입력을 재현하고 출력 제한 확인. PHASE 1은 기울임에 반응하는 시험이다. [#286](https://github.com/COSMOS-Aero-Engineering/COSMOS-TVC-Hopper/pull/286) |
| 실험 A와 질량 | 시간·스로틀·추력 gf·전압 V·전류 A, 계측기·반복·영점, 조립 CG·질량·관성 | 곡선·잔차·입력 파일·파라미터 버전 | 합성 예제와 실측 로그를 따로 보존. 기존 스로틀 상한 밖으로 외삽하지 않는다. [#244](https://github.com/COSMOS-Aero-Engineering/COSMOS-TVC-Hopper/issues/244) |
| 베인·구속 제어 | 서보별 중립·지연·부하 속도, 베인 편향별 모멘트, 스탠드 자유도·마찰 | 축별 토크 믹서, 포화/정지 처리, 동일 초기 자세의 PID 로그 | 구속 복원·오버슈트·정상오차와 포화를 반복 비교. [#263](https://github.com/COSMOS-Aero-Engineering/COSMOS-TVC-Hopper/issues/263) |
| 3D 시뮬·RL | 실측 불확실성 범위, 실기에 없는 센서 구분 | 6DOF·접촉·서보 지연, 정책 학습·평가·온보드 수치 대조 | 같은 기체·외란·seed로 PD/PID와 순수 정책 비교. 실측 오차와 모델 해시 기록. [제어 설계](../design/03-control-pipeline-design.md) |
| 고도·궤적 | ToF·광류의 유효 거리, 바닥·조명·지연·실패 조건 | 상태 추정, 고도→수직속도→추력 및 위치→속도→기울기→자세 제어 | 모의·구속 시험에서 추종 오차, 착지 속도, 신호 상실 전이를 확인한 뒤 구속 범위를 변경 |

전원·회전 시험은 지도교사의 서명, 구속·방호·킬 경로 확인 뒤 부장 입회로 진행한다. 앞 표는 장비 구매 승인이나 자유비행 승인에 해당하지 않는다. [발표 범위와 축소 안](countdown-1122.md)은 부장·차장이 결정할 별도 일정이다.

## 구현 상태의 기준

원격 main 기준 커밋 c6ac0c6에는 독립 펌웨어 시험 5종, Stage 1 PD/PPO 진단과 200-seed 비교, CSV 자세 재생과 추력 차트가 있다. PHASE 1 PR은 별도 브랜치다. 추적할 증거는 코드 빌드, 호스트 재현 로그, 보드 실행시간, 구속 기체의 응답, 자유기체의 응답 순으로 범위가 넓어진다. 어느 단계에서든 실측 근거가 없으면 해당 단계는 미검증으로 둔다.

재고 실사에서는 구매 대장 ID별로 실제 모델·수량·확인 날짜와 근거 파일을 남긴다. `재고 확인` 행은 0개로 간주하지 않는다. 추력·배터리·고전류 배선의 정격은 실물 모델과 부하를 대조한 뒤 확정한다.

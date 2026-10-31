# web: CSV 재생 3D 뷰어

시뮬레이션과 실물 시험 로그를 같은 화면으로 재생하는 웹 앱이다. 설계는 [02 웹 대시보드 설계](../docs/design/02-web-dashboard-design.md), 지금 할 일은 PRD #29와 [착수 문서](../docs/tasks/29-web-viewer.md).

## 실행

```bash
cd web
npm install
npm run dev
```

터미널에 나온 주소를 브라우저로 연다. 배포용 빌드는 `npm run build`(결과는 `dist/`, Git에 안 올림).

좌표 변환이나 베인 코드를 고쳤으면 `npm run check`를 돌린다. 축 판정, 예제 CSV 모든 행의 자세, 베인 힌지 축과 부호를 숫자로 검사한다(`tools/check_pose.mjs`).

## 구조

- `src/frames.js`: 기체 좌표(+X FWD, +Y LEFT, +Z 위) → Three.js 좌표(+Y 위) 변환. **좌표 변환은 여기에만 둔다.**
- `src/csv.js`: CSV 계약(02 문서 §4)을 헤더 이름으로 읽는다.
- `src/hopper.js`: `cad/hopper_params.scad` 치수로 만든 프리미티브 호퍼.
- `src/main.js`: 장면과 재생.
- `thrust.html`, `src/thrust.js`, `src/thrust_csv.js`: 실험 A 추력 곡선 화면(#254). 헤더의 `추력 곡선 (실험 A)` 링크나 `/thrust.html`로 연다. CSV를 열면 스로틀(%) 대 추력(gf), 스로틀(%) 대 전류(A)를 Chart.js로 그린다. 컬럼이 없으면 이유를 보이고, 읽지 못한 줄은 줄 번호와 함께 경고로 보인다. `vite.config.js`가 두 화면을 같이 빌드한다.
- `examples/`: 추력 곡선 예제 CSV. 값은 합성이고 실측이 아니다. `npm run check`가 `tools/check_thrust.mjs`로 읽기와 경고 줄 번호를 검사한다.
- `public/samples/`: 예제 CSV. `axis-test.csv`는 `python tools/make_axis_test_csv.py`로 다시 만든다. 시뮬레이션 CSV는 `sim/sim_stage1/export_episode.py`로 만든다.

버전은 `package.json`에 정확히 고정하고 `package-lock.json`을 커밋한다. 버전을 바꾸려면 `npm install 패키지@버전 --save-exact`.

## 베인 확인 시점 (#93)

예제를 고른 뒤 `베인 아래에서 보기`를 누르면 재생 위치와 자세를 유지한 채 카메라만 옮긴다.
네 색과 번호·기체 방향(FWD/LEFT/AFT/RIGHT)은 오른쪽 범례와 같다. 서보값은 원본의 정규화 값이다.
`기본 시점`으로 돌아갈 수 있다. µs 변환은 #94의 실물 보정 전이라 추가하지 않았다.

두 버튼은 고정된 월드 좌표의 카메라 프리셋이다. bodyToThreeVec는 축 표기만 바꾸며 재생 중 기체 자세를 적용하지 않는다. 아래 시점은 베인 피벗 z=-36 mm를 바라보는 배치다. 기체가 기울어져도 카메라가 따라 회전하지 않으므로 원하는 로그 행에서 정지하고 비교한다. 기본 시점은 처음 화면과 같은 위치·주시점으로 돌아간다.

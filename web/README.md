# web: CSV 재생 3D 뷰어

시뮬레이션과 실물 시험 로그를 같은 화면으로 재생하는 웹 앱이다. 설계는 [02 웹 대시보드 설계](../docs/design/02-web-dashboard-design.md), 지금 할 일은 PRD #29와 [착수 문서](../docs/tasks/29-web-viewer.md).

## 실행

```bash
cd web
npm install
npm run dev
```

터미널에 나온 주소를 브라우저로 연다. 배포용 빌드는 `npm run build`(결과는 `dist/`, Git에 안 올림).

## 구조

- `src/frames.js`: 기체 좌표(+X FWD, +Y LEFT, +Z 위) → Three.js 좌표(+Y 위) 변환. **좌표 변환은 여기에만 둔다.**
- `src/csv.js`: CSV 계약(02 문서 §4)을 헤더 이름으로 읽는다.
- `src/hopper.js`: `cad/hopper_params.scad` 치수로 만든 프리미티브 호퍼.
- `src/main.js`: 장면과 재생.
- `public/samples/`: 예제 CSV. `axis-test.csv`는 `python tools/make_axis_test_csv.py`로 다시 만든다. 시뮬레이션 CSV는 `sim/sim_stage1/export_episode.py`로 만든다.

버전은 `package.json`에 정확히 고정하고 `package-lock.json`을 커밋한다. 버전을 바꾸려면 `npm install 패키지@버전 --save-exact`.

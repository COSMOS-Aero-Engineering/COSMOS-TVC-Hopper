# 추력 곡선 화면 증거 (#254)

값은 모두 합성이다(`web/examples/thrust-curve-synthetic*.csv`). 실측이 아니며 해석에 쓰지 않는다.

- `01-synthetic-curves.png`: `thrust-curve-synthetic.csv`를 열었을 때 스로틀 대 추력, 스로틀 대 전류 그래프 2개.
- `02-bad-lines-warnings.png`: `thrust-curve-synthetic-bad-lines.csv`를 열었을 때. 6, 11, 13, 14줄이 줄 번호와 이유로 경고에 나오고 나머지 7점만 그려진다.

재현 조건: Linux, Chromium 1280x1000, `web/`에서 `npm run dev`, `/thrust.html`에서 CSV 열기. 화면 캡처는 Playwright(playwright-core)로 CSV 파일 입력을 채워 찍었다.

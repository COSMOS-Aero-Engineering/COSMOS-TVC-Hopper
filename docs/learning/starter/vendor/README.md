# 동봉 Three.js

첫 실습의 CDN 의존성을 줄이기 위해 Three.js **0.180.0**의 공식 축소 빌드를 포함했다. [공식 npm 배포본](https://registry.npmjs.org/three/-/three-0.180.0.tgz)에서 가져왔다.

- `three.module.js`: 배포본의 `build/three.module.min.js`. 가져오는 core 파일명만 `./three.core.min.js`에서 `./three.core.js`로 바꿨다.
- `three.core.js`: 배포본의 `build/three.core.min.js`.
- [MIT 라이선스](THREE-LICENSE.txt): 배포본 LICENSE를 보존했다.

배포 아카이브 SHA-256: `ad66d724565ee29a2467277fa84daa5ed0211d6b8d446e9ef29f6bae0cd14144`.

축소 빌드이므로 코드를 읽는 입문 자료로 쓰지 않는다. 학생은 [starter의 index.html](../index.html)을 수정하고 Three.js 개념은 [공식 Fundamentals](https://threejs.org/manual/pages/fundamentals.html)를 읽는다. 버전 변경은 정식 웹 앱의 의존성 결정과 구분해 리뷰한다.

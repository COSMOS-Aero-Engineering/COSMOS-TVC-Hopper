// 뷰어의 자세와 베인 표시를 숫자로 검사한다. 브라우저 없이 Node로 돈다.
// 실행: npm run check   (web/ 폴더에서). 하나라도 실패하면 exit 1.
//
// 1. 축 판정 (PRD #29 판정 기준 3): axis-test.csv의 theta+20, phi+20, psi+20 행에서 FWD, LEFT 끝이 기대대로 움직인다.
// 2. 자세 전 구간: 예제 CSV 모든 행에서 뷰어가 쓰는 쿼터니언 회전이 같은 행의 phi, theta, psi로 따로 계산한
//    ZYX 회전 R = Rz(psi)·Ry(theta)·Rx(phi)와 같다. 화면 숫자(CSV 값 × 180/π)만 대조하면 3D 자세는 검사하지 못한다.
// 3. 베인: servo = ±1에서 판이 스파(반경 방향 축) 둘레로 10° 돌고, 아래 끝이 시뮬레이션 측력의 반대쪽으로 간다.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as THREE from 'three';
import { parseLog } from '../src/csv.js';
import { bodyToThreeQuat, bodyToThreeVec } from '../src/frames.js';
import { buildHopper, poseVanes, VANE_ALPHA_MAX_DEG } from '../src/hopper.js';

const samples = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'public', 'samples');
const toBody = (v) => new THREE.Vector3(v.x, -v.z, v.y);
let failed = 0;
function check(ok, msg) {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${msg}`);
  if (!ok) failed += 1;
}
function load(name) {
  const res = parseLog(fs.readFileSync(path.join(samples, name), 'utf8'));
  if (res.missing.length || res.skipped) throw new Error(`${name}: missing ${res.missing}, skipped ${res.skipped}`);
  return res.rows;
}
// 기체 좌표 벡터 b를 CSV 한 행의 쿼터니언으로 돌린 결과(기체 좌표)
const viewerRotate = (r, b) => toBody(bodyToThreeVec(...b).applyQuaternion(bodyToThreeQuat(r.qw, r.qx, r.qy, r.qz)));
// 같은 행의 오일러각으로 따로 계산한 결과
function eulerRotate(r, b) {
  const m = new THREE.Matrix4().makeRotationZ(r.psi)
    .multiply(new THREE.Matrix4().makeRotationY(r.theta))
    .multiply(new THREE.Matrix4().makeRotationX(r.phi));
  return new THREE.Vector3(...b).applyMatrix4(m);
}

// 1. 축 판정
const axis = load('axis-test.csv');
const at = (mode) => axis.find((r) => r.mode === mode);
const s20 = Math.sin(THREE.MathUtils.degToRad(20));
const fwdTheta = viewerRotate(at('theta+20'), [1, 0, 0]);
check(Math.abs(fwdTheta.z + s20) < 1e-5, `theta+20: FWD 끝 z = ${fwdTheta.z.toFixed(4)} (기대 -${s20.toFixed(4)}, 아래로)`);
const leftPhi = viewerRotate(at('phi+20'), [0, 1, 0]);
check(Math.abs(leftPhi.z - s20) < 1e-5, `phi+20: LEFT 끝 z = ${leftPhi.z.toFixed(4)} (기대 +${s20.toFixed(4)}, 위로)`);
const fwdPsi = viewerRotate(at('psi+20'), [1, 0, 0]);
check(Math.abs(fwdPsi.y - s20) < 1e-5 && Math.abs(fwdPsi.z) < 1e-5,
  `psi+20: FWD 끝 y = ${fwdPsi.y.toFixed(4)} (기대 +${s20.toFixed(4)}, 위에서 볼 때 반시계)`);

// 2. 자세 전 구간
for (const name of ['axis-test.csv', 'sim-pd-nodr-s0.csv']) {
  const rows = load(name);
  let worst = 0;
  for (const r of rows) {
    for (const b of [[1, 0, 0], [0, 1, 0], [0, 0, 1]]) {
      worst = Math.max(worst, viewerRotate(r, b).distanceTo(eulerRotate(r, b)));
    }
  }
  // CSV가 유효숫자 6자리라 1e-5 안에서 같으면 같은 회전이다
  check(worst < 1e-5, `${name}: ${rows.length}행 쿼터니언 회전 = ZYX 오일러 회전 (최대 차이 ${worst.toExponential(1)})`);
}

// 3. 베인
const { group, vanes } = buildHopper();
const NAMES = ['FWD', 'LEFT', 'AFT', 'RIGHT'];
const RADIAL = [[1, 0, 0], [0, 1, 0], [-1, 0, 0], [0, -1, 0]].map((v) => new THREE.Vector3(...v));
// hopper_aviary.py: tau_x = (F1+F3)·l, tau_y = -(F2+F4)·l → servo > 0이면 베인 1·3은 +Y, 2·4는 +X로 민다
const FORCE = [[0, 1, 0], [1, 0, 0], [0, 1, 0], [1, 0, 0]].map((v) => new THREE.Vector3(...v));
function edges(i) {
  group.updateMatrixWorld(true);
  const plate = vanes[i].children[0];
  plate.geometry.computeBoundingBox();
  const bb = plate.geometry.boundingBox;
  const p = (x, y) => toBody(new THREE.Vector3(x, y, 0).applyMatrix4(plate.matrixWorld));
  return { top: p(0, bb.max.y), bottom: p(0, bb.min.y), inner: p(bb.min.x, 0), outer: p(bb.max.x, 0) };
}
const alpha = THREE.MathUtils.degToRad(VANE_ALPHA_MAX_DEG);
poseVanes(vanes, [0, 0, 0, 0]);
const rest = vanes.map((_, i) => edges(i));
for (const s of [1, -1]) {
  for (let i = 0; i < 4; i += 1) {
    const servos = [0, 0, 0, 0];
    servos[i] = s;
    poseVanes(vanes, servos);
    const e = edges(i);
    const r0 = rest[i];
    // 스파 위의 점(안쪽·바깥 끝 중앙)은 움직이지 않는다 = 반경 방향 축 둘레 회전
    const sparFixed = e.inner.distanceTo(r0.inner) < 1e-9 && e.outer.distanceTo(r0.outer) < 1e-9;
    // 아래 끝(뒷전)은 측력 반대쪽으로 h·sin(alpha), 위로 h·(1 - cos(alpha)) 간다 (h = 시위/2)
    const h = (r0.top.z - r0.bottom.z) / 2;
    const move = e.bottom.clone().sub(r0.bottom);
    const want = FORCE[i].clone().multiplyScalar(-s * h * Math.sin(alpha))
      .add(new THREE.Vector3(0, 0, h * (1 - Math.cos(alpha))));
    const okMove = move.distanceTo(want) < 1e-3 * Math.max(1, want.length()) && Math.abs(move.dot(RADIAL[i])) < 1e-9;
    check(sparFixed && okMove,
      `베인 ${i + 1} ${NAMES[i]} servo=${s > 0 ? '+1' : '-1'}: 아래 끝 이동 (${move.toArray().map((n) => n.toFixed(2)).join(', ')}) mm`
      + `, 기대 (${want.toArray().map((n) => n.toFixed(2)).join(', ')}), 스파 고정 ${sparFixed}`);
  }
}

if (failed) {
  console.log(`\n${failed}개 실패`);
  process.exit(1);
}
console.log('\n모두 통과');

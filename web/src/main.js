// W-A 뼈대 (PRD #29): CSV를 읽어 프리미티브 호퍼를 시간에 맞춰 같은 자세로 재생한다.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { parseLog } from './csv.js';
import { bodyToThreeQuat, bodyToThreeVec } from './frames.js';
import { buildHopper, poseVanes, VANE_COLORS } from './hopper.js';

const $ = (id) => document.getElementById(id);
// 반올림해서 0이 되는 작은 음수(-1e-12 등)는 "-0.0" 대신 "0.0"으로 쓴다
const deg = (r) => {
  if (r === null) return '-';
  const s = (r * 180 / Math.PI).toFixed(1);
  return s === '-0.0' ? '0.0' : s;
};

// ---------- 장면 ----------
const view = $('view');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
view.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xdfe4ea);
const camera = new THREE.PerspectiveCamera(45, 1, 1, 5000);
// 카메라: 기체 기준 앞-오른쪽-위에서 내려다본다
camera.position.copy(bodyToThreeVec(420, -380, 300));
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 30, 0);
controls.update();

// 카메라만 옮긴다. 기체 자세와 재생 위치를 유지해 같은 로그 행을 비교한다.
function setCamera(below) {
  camera.position.copy(below ? bodyToThreeVec(35, -25, -210) : bodyToThreeVec(420, -380, 300));
  controls.target.copy(below ? bodyToThreeVec(0, 0, -36) : new THREE.Vector3(0, 30, 0));
  controls.update();
  $('camera-default').setAttribute('aria-pressed', String(!below));
  $('camera-below').setAttribute('aria-pressed', String(below));
}
$('camera-default').addEventListener('click', () => setCamera(false));
$('camera-below').addEventListener('click', () => setCamera(true));
VANE_COLORS.forEach((color, i) => {
  $(`vane-color-${i + 1}`).style.backgroundColor = `#${color.toString(16).padStart(6, '0')}`;
});

scene.add(new THREE.HemisphereLight(0xffffff, 0x666666, 2.2));
const sun = new THREE.DirectionalLight(0xffffff, 1.5);
sun.position.set(300, 600, 200);
scene.add(sun);
const grid = new THREE.GridHelper(800, 16, 0x888888, 0xbbbbbb);
grid.position.y = -140;
scene.add(grid);
scene.add(new THREE.AxesHelper(60)); // 빨강 = three X, 초록 = three Y(위), 파랑 = three Z

const { group: hopper, vanes } = buildHopper();
scene.add(hopper);

function resize() {
  const w = view.clientWidth, h = view.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / Math.max(h, 1);
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
resize();

// ---------- 재생 ----------
let rows = [];
let idx = 0;
let playing = false;
let playStartWall = 0;
let playStartT = 0;
// select에서 읽는다. Firefox는 새로고침할 때 select 값을 되살리므로 1로 고정하면 표시와 실제 배속이 다를 수 있다.
let speed = Number($('speed').value);
let vanesValid = true; // servo1..4가 모두 -1~1 안이면 true (02 문서 §4는 µs도 허용한다)
$('speed').addEventListener('change', (e) => {
  // 지금까지 재생한 시간을 이전 배속으로 계산해 기준점으로 삼는다. rows[idx].t_ms로 되돌리면 행 사이 시간이 사라진다.
  const now = performance.now();
  if (playing) { playStartT += (now - playStartWall) * speed; playStartWall = now; }
  speed = Number(e.target.value);
});

function show(i) {
  idx = Math.max(0, Math.min(i, rows.length - 1));
  const r = rows[idx];
  if (!r) return;
  hopper.quaternion.copy(bodyToThreeQuat(r.qw, r.qx, r.qy, r.qz));
  poseVanes(vanes, vanesValid ? [r.servo1, r.servo2, r.servo3, r.servo4] : [null, null, null, null]);
  $('t').textContent = r.t_ms;
  $('mode').textContent = r.mode ?? '-';
  $('phi').textContent = deg(r.phi);
  $('theta').textContent = deg(r.theta);
  $('psi').textContent = deg(r.psi);
  $('throttle').textContent = r.throttle === null ? '-' : r.throttle.toFixed(2);
  [r.servo1, r.servo2, r.servo3, r.servo4].forEach((s, j) => {
    $(`servo${j + 1}`).textContent = s === null ? '-' : s.toFixed(3) + (vanesValid ? '' : ' (단위 미확인)');
  });
  $('seek').value = idx;
}

function load(text, name) {
  const res = parseLog(text);
  if (res.missing.length) {
    $('status').textContent = `${name}: 필요한 컬럼 없음 (${res.missing.join(', ')})`;
    return;
  }
  rows = res.rows;
  playing = false;
  $('play').textContent = '재생';
  $('play').disabled = $('seek').disabled = rows.length === 0;
  $('seek').max = Math.max(rows.length - 1, 0);
  vanesValid = !rows.some((r) => [r.servo1, r.servo2, r.servo3, r.servo4].some((s) => s !== null && Math.abs(s) > 1));
  $('status').textContent = `${name}: ${rows.length}행` + (res.skipped ? `, 건너뛴 행 ${res.skipped}` : '')
    + (vanesValid ? '' : ', servo 값이 -1~1 밖이라(µs로 보임) 베인을 중립에 둔다');
  show(0);
}

$('file').addEventListener('change', async (e) => {
  const f = e.target.files[0];
  if (f) load(await f.text(), f.name);
});
$('sample').addEventListener('change', async (e) => {
  if (!e.target.value) return;
  const res = await fetch(import.meta.env.BASE_URL + e.target.value);
  load(await res.text(), e.target.value);
});
$('seek').addEventListener('input', (e) => { playing = false; $('play').textContent = '재생'; show(Number(e.target.value)); });
$('play').addEventListener('click', () => {
  if (!rows.length) return;
  if (idx >= rows.length - 1) show(0);
  playing = !playing;
  $('play').textContent = playing ? '정지' : '재생';
  playStartWall = performance.now();
  playStartT = rows[idx].t_ms;
});

renderer.setAnimationLoop(() => {
  if (playing && rows.length) {
    // 벽시계 경과시간 × 배속으로 t_ms를 따라간다 (#29 작업 5: 1×, 0.25×)
    const target = playStartT + (performance.now() - playStartWall) * speed;
    let i = idx;
    while (i < rows.length - 1 && rows[i + 1].t_ms <= target) i += 1;
    if (i !== idx) show(i); // 0.25×에서는 여러 프레임 동안 같은 행이다
    if (i >= rows.length - 1) { playing = false; $('play').textContent = '재생'; }
  }
  controls.update();
  renderer.render(scene, camera);
});
const = webCiSyntaxFailure;

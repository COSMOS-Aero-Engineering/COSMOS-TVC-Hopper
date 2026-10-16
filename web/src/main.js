// W-A 뼈대 (PRD #29): CSV를 읽어 프리미티브 호퍼를 시간에 맞춰 같은 자세로 재생한다.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { parseLog } from './csv.js';
import { bodyToThreeQuat, bodyToThreeVec } from './frames.js';
import { buildHopper, poseVanes } from './hopper.js';

const $ = (id) => document.getElementById(id);
const deg = (r) => (r === null ? '-' : (r * 180 / Math.PI).toFixed(1));

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
let speed = 1;
$('speed').addEventListener('change', (e) => {
  speed = Number(e.target.value);
  if (playing && rows.length) { playStartWall = performance.now(); playStartT = rows[idx].t_ms; }
});

function show(i) {
  idx = Math.max(0, Math.min(i, rows.length - 1));
  const r = rows[idx];
  if (!r) return;
  hopper.quaternion.copy(bodyToThreeQuat(r.qw, r.qx, r.qy, r.qz));
  poseVanes(vanes, [r.servo1, r.servo2, r.servo3, r.servo4]);
  $('t').textContent = r.t_ms;
  $('mode').textContent = r.mode ?? '-';
  $('phi').textContent = deg(r.phi);
  $('theta').textContent = deg(r.theta);
  $('psi').textContent = deg(r.psi);
  $('throttle').textContent = r.throttle === null ? '-' : r.throttle.toFixed(2);
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
  $('status').textContent = `${name}: ${rows.length}행` + (res.skipped ? `, 건너뛴 행 ${res.skipped}` : '');
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
    show(i);
    if (i >= rows.length - 1) { playing = false; $('play').textContent = '재생'; }
  }
  controls.update();
  renderer.render(scene, camera);
});

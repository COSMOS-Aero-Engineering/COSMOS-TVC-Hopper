// 프리미티브 호퍼 (02 문서 §5.1). 치수는 cad/hopper_params.scad 값을 mm 그대로 옮기고 1 단위 = 1 mm로 둔다.
// 모든 위치는 기체 좌표(body, mm)로 적고 bodyToThreeVec로 바꿔서 놓는다.
import * as THREE from 'three';
import { bodyToThreeVec } from './frames.js';

const CAD = {
  edf_housing_od: 72,   // EDF 하우징 외경
  edf_body_len: 92,     // 배기면(z=0) ~ 흡입구 립
  vane_ring_od: 96,     // edf_housing_od + 24
  vane_ring_id: 76,     // edf_housing_od + 4
  vane_ring_top_z: -22,
  vane_ring_bot_z: -50,
  vane_pivot_z: -36,
  vane_inner_r: 4,
  vane_outer_r: 41,     // vane_ring_id/2 + 3
  vane_chord: 25,
  vane_thick: 2.5,
  foot_circle: 360,
  foot_z: -140,
  top_plate_z: 180,     // 01-avionics §7.7 상판 178~182
};

// 베인 1~4 = FWD / LEFT / AFT / RIGHT (01-avionics §1)
const VANE_AZ_DEG = [0, 90, 180, 270];
const VANE_COLORS = [0xe4572e, 0x29a3a3, 0x7a7a7a, 0x7a7a7a];

// servo = ±1일 때 베인 편향각. sim/sim_stage1/params.yaml의 alpha_max_deg와 같은 값이다(alpha = servo × alpha_max).
export const VANE_ALPHA_MAX_DEG = 10;

// servo > 0일 때 힌지(스파, 반경 방향 축) 회전 부호. 시뮬레이션의 힘 방향에서 정했다.
// hopper_aviary.py step(): tau_x = (F1+F3)·l, tau_y = -(F2+F4)·l, 베인은 무게중심 아래 l에 있다.
// 그래서 servo > 0이면 베인 1·3의 측력은 +Y, 베인 2·4의 측력은 +X다.
// 베인은 배기를 측력의 반대쪽으로 꺾는다. 그래서 판의 아래 끝(뒷전)이 측력의 반대쪽으로 가야 한다.
// 반경축 둘레 +회전은 아래 끝을 접선 +방향(위에서 볼 때 반시계)으로 보낸다. 이 두 조건에서 아래 부호가 나온다.
// 실물 서보의 회전 방향은 TC-1에서 펌웨어 write_servo() 부호로 이 정의에 맞춘다(01-avionics §1).
const VANE_HINGE_SIGN = [-1, 1, 1, -1];

function place(mesh, x, y, z) {
  mesh.position.copy(bodyToThreeVec(x, y, z));
  return mesh;
}

export function buildHopper() {
  const g = new THREE.Group();
  const grey = new THREE.MeshStandardMaterial({ color: 0x9aa3b2, metalness: 0.2, roughness: 0.6 });

  // EDF 하우징: 원통 축이 body Z = three Y라서 CylinderGeometry 기본 방향 그대로 쓴다
  const edf = new THREE.Mesh(
    new THREE.CylinderGeometry(CAD.edf_housing_od / 2, CAD.edf_housing_od / 2, CAD.edf_body_len, 32), grey);
  g.add(place(edf, 0, 0, CAD.edf_body_len / 2));

  // 베인링 (속 빈 원통)
  const ringH = CAD.vane_ring_top_z - CAD.vane_ring_bot_z;
  const ringShape = new THREE.Shape();
  ringShape.absarc(0, 0, CAD.vane_ring_od / 2, 0, Math.PI * 2, false);
  const hole = new THREE.Path();
  hole.absarc(0, 0, CAD.vane_ring_id / 2, 0, Math.PI * 2, true);
  ringShape.holes.push(hole);
  const ringGeo = new THREE.ExtrudeGeometry(ringShape, { depth: ringH, bevelEnabled: false, curveSegments: 48 });
  ringGeo.rotateX(-Math.PI / 2); // 압출 방향(+Z)을 three +Y(= body 위)로
  const ring = new THREE.Mesh(ringGeo, grey);
  g.add(place(ring, 0, 0, CAD.vane_ring_bot_z));

  // 베인 4개: 반경 방향 평판, 시위는 세로(body Z). CAD vane_one()처럼 스파(반경 방향 축) 둘레로 돈다.
  // pivot: 베인 방위만 맞춘다(로컬 X = 반경 바깥, 로컬 Y = body Z). hinge: 로컬 X 둘레 편향각만 바꾼다.
  const span = CAD.vane_outer_r - CAD.vane_inner_r;
  const vanes = VANE_AZ_DEG.map((az, i) => {
    const pivot = new THREE.Group();
    const a = THREE.MathUtils.degToRad(az);
    const rMid = CAD.vane_inner_r + span / 2;
    pivot.position.copy(bodyToThreeVec(rMid * Math.cos(a), rMid * Math.sin(a), CAD.vane_pivot_z));
    pivot.rotation.y = a; // 반경 방향으로 돌려 놓는다 (three Y = body Z 축 회전)
    const hinge = new THREE.Group();
    const plate = new THREE.Mesh(
      new THREE.BoxGeometry(span, CAD.vane_chord, CAD.vane_thick),
      new THREE.MeshStandardMaterial({ color: VANE_COLORS[i] }));
    hinge.add(plate);
    pivot.add(hinge);
    g.add(pivot);
    return hinge;
  });

  // 다리 4개: 45° 계열 (01-avionics §1), 베인링 하단에서 발까지
  const legMat = new THREE.MeshStandardMaterial({ color: 0x3b4252 });
  for (const az of [45, 135, 225, 315]) {
    const a = THREE.MathUtils.degToRad(az);
    const top = bodyToThreeVec((CAD.vane_ring_od / 2) * Math.cos(a), (CAD.vane_ring_od / 2) * Math.sin(a), CAD.vane_ring_bot_z);
    const bot = bodyToThreeVec((CAD.foot_circle / 2) * Math.cos(a), (CAD.foot_circle / 2) * Math.sin(a), CAD.foot_z);
    const len = top.distanceTo(bot);
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(3, 3, len, 8), legMat);
    leg.position.copy(top).add(bot).multiplyScalar(0.5);
    leg.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), bot.clone().sub(top).normalize());
    g.add(leg);
  }

  // 상판 (원판으로 단순화)
  const plate = new THREE.Mesh(new THREE.CylinderGeometry(CAD.vane_ring_od / 2 + 10, CAD.vane_ring_od / 2 + 10, 4, 32), grey);
  g.add(place(plate, 0, 0, CAD.top_plate_z));

  // FWD 표시 화살표 (+X 방향)
  const fwd = new THREE.ArrowHelper(bodyToThreeVec(1, 0, 0), bodyToThreeVec(0, 0, CAD.top_plate_z + 4), 110, 0xe4572e, 18, 10);
  g.add(fwd);

  return { group: g, vanes };
}

// 베인 애니메이션 (02 문서 §5.3, PRD #29 작업 6).
// servos: servo1..4, -1~1 정규화 값. null이면 중립(0°)으로 둔다.
// µs 값은 받지 않는다. µs → 각도 변환은 서보 보정(TC-1) 전이라 정할 수 없다. 범위 검사는 main.js가 한다.
export function poseVanes(vanes, servos) {
  const max = THREE.MathUtils.degToRad(VANE_ALPHA_MAX_DEG);
  vanes.forEach((hinge, i) => {
    const s = servos[i];
    hinge.rotation.x = s === null ? 0 : VANE_HINGE_SIGN[i] * s * max;
  });
}

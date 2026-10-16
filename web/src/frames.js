// 좌표 변환은 이 파일 한 곳에만 둔다 (02 문서 §5.2).
//
// 기체(body) 좌표계, 01-avionics §1: +X = FWD(베인1), +Y = LEFT(베인2), +Z = 위. 오른손 좌표계.
// Three.js 좌표계: +Y가 위, 오른손 좌표계.
// 초안 매핑: body (x, y, z) -> three (x, z, -y). 회전이 아닌 축 이름 바꾸기라서 쿼터니언의 벡터 부분도
// 같은 규칙으로 옮긴다: (qw, qx, qy, qz) -> (qw, qx, qz, -qy).
//
// 확인 필요(PRD #29 판정 기준): samples/axis-test.csv의 theta+20 구간에서 FWD 쪽이 내려가는지,
// phi+20에서 LEFT 쪽이 올라가는지, psi+20에서 위에서 볼 때 반시계로 도는지 눈으로 확인하고 PR에 남긴다.
// 틀리면 이 두 함수만 고친다.
import * as THREE from 'three';

export function bodyToThreeVec(x, y, z) {
  return new THREE.Vector3(x, z, -y);
}

export function bodyToThreeQuat(qw, qx, qy, qz) {
  return new THREE.Quaternion(qx, qz, -qy, qw).normalize();
}

// 좌표 변환은 이 파일 한 곳에만 둔다 (02 문서 §5.2).
//
// 기체(body) 좌표계, 01-avionics §1: +X = FWD(베인1), +Y = LEFT(베인2), +Z = 위. 오른손 좌표계.
// Three.js 좌표계: +Y가 위, 오른손 좌표계.
// 초안 매핑: body (x, y, z) -> three (x, z, -y). 회전이 아닌 축 이름 바꾸기라서 쿼터니언의 벡터 부분도
// 같은 규칙으로 옮긴다: (qw, qx, qy, qz) -> (qw, qx, qz, -qy).
//
// 2026-10-17 판정 완료(PRD #29 판정 기준): samples/axis-test.csv로 눈과 숫자로 확인했다.
// theta+20에서 FWD가 아래로(-0.342), phi+20에서 LEFT가 위로(+0.342), psi+20에서 위에서 볼 때 반시계로 돌았다.
// 세 축 모두 기대와 같아서 이 매핑을 그대로 쓴다.
import * as THREE from 'three';

export function bodyToThreeVec(x, y, z) {
  return new THREE.Vector3(x, z, -y);
}

export function bodyToThreeQuat(qw, qx, qy, qz) {
  return new THREE.Quaternion(qx, qz, -qy, qw).normalize();
}

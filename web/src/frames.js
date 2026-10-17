// 좌표 변환은 이 파일 한 곳에만 둔다 (02 문서 §5.2).
//
// 기체(body) 좌표계, 01-avionics §1: +X = FWD(베인1), +Y = LEFT(베인2), +Z = 위. 오른손 좌표계.
// Three.js 좌표계: +Y가 위, 오른손 좌표계.
// 매핑: body (x, y, z) -> three (x, z, -y). 이 매핑은 X축 둘레 -90° 회전이다(행렬식 +1, 반사가 아니다).
// 회전이라서 쿼터니언의 벡터 부분(회전축)도 같은 규칙으로 옮기면 된다: (qw, qx, qy, qz) -> (qw, qx, qz, -qy).
// 축 하나만 부호를 뒤집으면 반사가 되어 이 규칙이 깨진다. 고칠 때는 세 축을 함께 다시 판정한다.
//
// 2026-10-17 판정(PRD #29 판정 기준 3): samples/axis-test.csv로 눈과 숫자로 확인했다.
// theta+20에서 FWD가 아래로(-0.342), phi+20에서 LEFT가 위로(+0.342), psi+20에서 위에서 볼 때 반시계로 돌았다.
// sim의 ZYX 오일러 정의(hopper_aviary.py 운동학, export_episode.py euler_zyx_to_quat)와 같다.
// 숫자 검사는 `npm run check`(tools/check_pose.mjs)가 다시 한다.
import * as THREE from 'three';

export function bodyToThreeVec(x, y, z) {
  return new THREE.Vector3(x, z, -y);
}

export function bodyToThreeQuat(qw, qx, qy, qz) {
  return new THREE.Quaternion(qx, qz, -qy, qw).normalize();
}

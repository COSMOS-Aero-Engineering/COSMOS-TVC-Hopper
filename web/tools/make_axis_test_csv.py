"""
축 변환 확인용 CSV(public/samples/axis-test.csv)를 만든다. PRD #29 판정 기준 3번째 항목용.

각 구간은 한 축만 20도 기울인 자세를 1초씩 유지한다. 시뮬레이션과 같은 ZYX 오일러 -> 쿼터니언 식을 쓴다
(sim/sim_stage1/export_episode.py의 euler_zyx_to_quat와 같은 식).

기대 모습 (01-avionics 1절 좌표계, +X=FWD, +Y=LEFT, +Z=위, 오른손 법칙 기준. 부호 정의는 #27에서 준원 확인 필요):
  theta = +20도  -> FWD(베인1) 쪽이 아래로
  phi   = +20도  -> LEFT(베인2) 쪽이 위로 (= RIGHT 쪽이 아래로)
  psi   = +20도  -> 위에서 볼 때 반시계로 돎

실행: python web/tools/make_axis_test_csv.py   (표준 라이브러리만 씀)
"""
import csv
import math
import os

COLUMNS = ["t_ms", "source", "mode", "phi", "theta", "psi", "qw", "qx", "qy", "qz",
           "wx", "wy", "wz", "servo1", "servo2", "servo3", "servo4", "throttle", "batt_v", "rpm", "reward"]
SEGMENTS = [("level", 0, 0, 0), ("theta+20", 0, 20, 0), ("level", 0, 0, 0),
            ("phi+20", 20, 0, 0), ("level", 0, 0, 0), ("psi+20", 0, 0, 20), ("level", 0, 0, 0)]


def quat(phi, theta, psi):
    cr, sr = math.cos(phi / 2), math.sin(phi / 2)
    cp, sp = math.cos(theta / 2), math.sin(theta / 2)
    cy, sy = math.cos(psi / 2), math.sin(psi / 2)
    return (cr * cp * cy + sr * sp * sy, sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy)


def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public", "samples", "axis-test.csv")
    t = 0
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for name, p, th, ps in SEGMENTS:
            phi, theta, psi = (math.radians(v) for v in (p, th, ps))
            q = quat(phi, theta, psi)
            for _ in range(100):  # 10 ms x 100 = 1초
                w.writerow([t, "TEST", name, f"{phi:.6f}", f"{theta:.6f}", f"{psi:.6f}",
                            *(f"{v:.6f}" for v in q), 0, 0, 0, 0, 0, 0, 0, 0.5, "", "", ""])
                t += 10
    print(f"wrote {os.path.normpath(out)} ({t // 10} rows)")


if __name__ == "__main__":
    main()

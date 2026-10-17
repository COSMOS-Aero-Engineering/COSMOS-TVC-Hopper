"""
질량 특성 추정: 무게중심(x, y, z), 베인 토크 팔, 관성 모멘트 (PRD #26, #59).

parts.csv의 부품마다 질량(g)과 모양·위치(mm, 배기면 z=0, +X=FWD, +Y=LEFT)를 읽어
부품을 점들로 나눠 합한다. 출처 칸(mass_source)에 "ESTIMATE"가 있는 행은 근거가 약하다.

모양(shape)과 열 의미:
  box    x,y,z = 중심, p1,p2,p3 = 크기(x,y,z)
  ring   z = 중심, p1 = 안 반경, p2 = 바깥 반경, p3 = 높이 (x, y는 0)
  servo4 z = 높이, p1 = 반경. 0°/90°/180°/270° 네 곳에 질량을 1/4씩 둔다(서보, 커플러, 스파)
  rods4  z = 시작 높이, p1 = 시작 반경, p2 = 끝 반경, p3 = 끝 높이. 45° 계열 막대 4개(기둥, 다리)

출력: 총질량, CG, l = z_cg - vane_pivot_z, CG 기준 Jxx/Jyy/Jzz(kg m^2),
      질량 +-10 %·위치 +-5 mm 무작위 흔들기의 95 % 구간(z_cg, 옆 치우침).
표준 라이브러리만 쓴다. 실행: python cad/cg/cg_estimate.py [parts.csv]
"""
import csv
import math
import os
import random
import sys

VANE_PIVOT_Z_MM = -36.0       # cad/hopper_params.scad vane_pivot_z
TARGET_ZCG_MM = (60.0, 75.0)  # 01-avionics 8.4
LATERAL_LIMIT_MM = 6.5        # 베인 최대 토크의 등가 오프셋(PR #35 기준). 이보다 치우치면 버티지 못한다
N = 6                         # 축당 분할 수


def points(row):
    s, m = row["shape"], row["mass_g"] / 1000.0
    x, y, z, p1, p2, p3 = (row[k] for k in ("x", "y", "z", "p1", "p2", "p3"))
    pts = []
    if s == "box":
        for i in range(N):
            for j in range(N):
                for k in range(N):
                    pts.append((x + p1 * ((i + 0.5) / N - 0.5), y + p2 * ((j + 0.5) / N - 0.5),
                                z + p3 * ((k + 0.5) / N - 0.5)))
    elif s == "ring":
        for i in range(24):
            a = 2 * math.pi * i / 24
            for j in range(N):
                r = math.sqrt(p1 ** 2 + (p2 ** 2 - p1 ** 2) * (j + 0.5) / N)
                for k in range(N):
                    pts.append((r * math.cos(a), r * math.sin(a), z + p3 * ((k + 0.5) / N - 0.5)))
    elif s == "servo4":
        pts = [(p1 * math.cos(math.radians(a)), p1 * math.sin(math.radians(a)), z) for a in (0, 90, 180, 270)]
    elif s == "rods4":
        for a in (45, 135, 225, 315):
            for t in range(N * 2):
                f = (t + 0.5) / (N * 2)
                r, zz = p1 + (p2 - p1) * f, z + (p3 - z) * f
                pts.append((r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), zz))
    else:
        raise SystemExit(f"모르는 shape: {s} ({row['part']})")
    w = m / len(pts)
    return [(w, p[0] / 1000, p[1] / 1000, p[2] / 1000) for p in pts]


def props(rows, jitter=None):
    allp = []
    for r in rows:
        r2 = dict(r)
        if jitter:
            r2["mass_g"] *= 1 + jitter.uniform(-0.1, 0.1)
            for k in ("x", "y", "z"):
                r2[k] += jitter.uniform(-5, 5)
        allp += points(r2)
    M = sum(p[0] for p in allp)
    c = [sum(p[0] * p[i + 1] for p in allp) / M for i in range(3)]
    J = [sum(p[0] * ((p[2] - c[1]) ** 2 + (p[3] - c[2]) ** 2) for p in allp),
         sum(p[0] * ((p[1] - c[0]) ** 2 + (p[3] - c[2]) ** 2) for p in allp),
         sum(p[0] * ((p[1] - c[0]) ** 2 + (p[2] - c[1]) ** 2) for p in allp)]
    return M, c, J


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "parts.csv")
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("mass_g", "x", "y", "z", "p1", "p2", "p3"):
            r[k] = float(r[k])

    M, c, J = props(rows)
    zcg, lat = c[2] * 1000, math.hypot(c[0], c[1]) * 1000
    est = sum(r["mass_g"] for r in rows if "ESTIMATE" in r["mass_source"])
    print(f"총질량 {M * 1000:.0f} g (그중 ESTIMATE 행 {est:.0f} g)")
    print(f"CG x {c[0] * 1000:+.1f}  y {c[1] * 1000:+.1f}  z {zcg:.1f} mm (배기면 위)")
    print(f"  z_cg 목표 {TARGET_ZCG_MM[0]:.0f}-{TARGET_ZCG_MM[1]:.0f} mm → "
          f"{'범위 안' if TARGET_ZCG_MM[0] <= zcg <= TARGET_ZCG_MM[1] else '범위 밖'}")
    print(f"  옆 치우침 {lat:.1f} mm, 베인 한계 {LATERAL_LIMIT_MM} mm → "
          f"{'여유 있음' if lat < LATERAL_LIMIT_MM / 2 else ('한계 안' if lat < LATERAL_LIMIT_MM else '한계 밖')}")
    print(f"l = z_cg - ({VANE_PIVOT_Z_MM:.0f}) = {zcg - VANE_PIVOT_Z_MM:.1f} mm")
    print(f"J (CG 기준) Jxx {J[0]:.5f}  Jyy {J[1]:.5f}  Jzz {J[2]:.5f} kg m^2")
    print(f"무게 {M * 9.81:.2f} N, 정적 추력 사양 12.75 N(1300 gf) 기준 TWR {12.75 / (M * 9.81):.2f}")

    rng = random.Random(0)
    zs, lats = [], []
    for _ in range(300):
        _, cc, _ = props(rows, rng)
        zs.append(cc[2] * 1000)
        lats.append(math.hypot(cc[0], cc[1]) * 1000)
    zs.sort(); lats.sort()
    print(f"민감도(질량 +-10 %, 위치 +-5 mm, 300회 95 % 구간): z_cg {zs[7]:.1f}-{zs[292]:.1f} mm, "
          f"옆 치우침 {lats[7]:.1f}-{lats[292]:.1f} mm")


if __name__ == "__main__":
    main()

"""
무게중심(CG) 높이와 베인 토크 팔 추정 (PRD #26, 이슈 #21의 vane_arm_l 근거).

parts.csv의 부품별 질량(g)과 세로 위치 z(mm, EDF 배기면 = 0, 위가 +)로
  z_cg = sum(m*z) / sum(m)
  l    = z_cg - vane_pivot_z      (vane_pivot_z = -36 mm, cad/hopper_params.scad)
를 계산하고, 질량 +-10 %와 각 부품의 z 불확실성(z_uncertainty_mm)을 무작위로 흔들어 범위를 낸다.

파이썬 표준 라이브러리만 쓴다. 실행: python cad/cg/cg_estimate.py
실측으로 바꾼 값은 parts.csv의 mass_source / z_source를 "measured ..."로 고친다.
"""
import csv
import os
import random
import statistics

VANE_PIVOT_Z_MM = -36.0      # cad/hopper_params.scad vane_pivot_z, 01-avionics 7.7
TARGET_ZCG_MM = (60.0, 75.0)  # 01-avionics 8.4 (마스터 5.3의 140~180은 도달 불가로 정정됨)
MASS_REL = 0.10               # 질량 +-10 %
N_SAMPLES = 20000


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["mass_g"] = float(r["mass_g"])
        r["z_mm"] = float(r["z_mm"])
        r["z_uncertainty_mm"] = float(r["z_uncertainty_mm"])
    return rows


def zcg(rows, masses=None, zs=None):
    masses = masses or [r["mass_g"] for r in rows]
    zs = zs or [r["z_mm"] for r in rows]
    return sum(m * z for m, z in zip(masses, zs)) / sum(masses)


def main():
    rows = load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "parts.csv"))
    total = sum(r["mass_g"] for r in rows)
    z0 = zcg(rows)

    print(f"| 부품 | 질량 (g) | z (mm) | m*z (g*mm) | 질량 출처 | z 출처 |")
    print(f"|---|---:|---:|---:|---|---|")
    for r in rows:
        print(f"| {r['part']} | {r['mass_g']:.0f} | {r['z_mm']:.0f} | {r['mass_g'] * r['z_mm']:.0f} | "
              f"{r['mass_source']} | {r['z_source']} |")
    print()
    print(f"총질량 {total:.0f} g")
    print(f"z_cg = {z0:.1f} mm (배기면 위)   목표 {TARGET_ZCG_MM[0]:.0f}~{TARGET_ZCG_MM[1]:.0f} mm "
          f"-> {'범위 안' if TARGET_ZCG_MM[0] <= z0 <= TARGET_ZCG_MM[1] else '범위 밖'}")
    print(f"l = z_cg - ({VANE_PIVOT_Z_MM:.0f}) = {z0 - VANE_PIVOT_Z_MM:.1f} mm   (params.yaml vane_arm_l 단위는 m)")

    rng = random.Random(0)
    samples = []
    for _ in range(N_SAMPLES):
        ms = [r["mass_g"] * (1 + rng.uniform(-MASS_REL, MASS_REL)) for r in rows]
        zs = [r["z_mm"] + rng.uniform(-r["z_uncertainty_mm"], r["z_uncertainty_mm"]) for r in rows]
        samples.append(zcg(rows, ms, zs))
    samples.sort()
    lo, hi = samples[int(0.025 * N_SAMPLES)], samples[int(0.975 * N_SAMPLES)]
    print()
    print(f"민감도 (질량 +-{MASS_REL * 100:.0f} %, z +-불확실성, 균등분포 {N_SAMPLES}회, 95 % 구간)")
    print(f"  z_cg {lo:.1f} ~ {hi:.1f} mm (표준편차 {statistics.pstdev(samples):.1f})")
    print(f"  l    {lo - VANE_PIVOT_Z_MM:.1f} ~ {hi - VANE_PIVOT_Z_MM:.1f} mm")

    print()
    print("z_cg에 가장 크게 기여하는 부품 (|m*z| 순)")
    for r in sorted(rows, key=lambda r: -abs(r["mass_g"] * r["z_mm"]))[:5]:
        print(f"  {r['part']}: {r['mass_g'] * r['z_mm'] / total:+.1f} mm")


if __name__ == "__main__":
    main()

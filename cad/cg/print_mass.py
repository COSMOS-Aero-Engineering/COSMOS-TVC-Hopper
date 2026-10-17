"""
프린트·구조 부품 질량 추정 (PRD #26, docs/tasks/26-cad-cg.md 작업 1).

`parts.csv`의 "상판+베일+기둥4+트레이 90 g" 묶음을 CAD 부품별로 나누기 위해 쓴다.
이 환경에는 OpenSCAD가 없어서, `cad/hopper_params.scad`의 형상 변수로 부피를 해석적으로 계산한다.

가정:
- 프린트(PETG): 부피 x 1.27 g/cm3 x 인필 40 % (master-design §10-4 / 01 문서 §7.1).
  얇은 판은 상·하면 스킨 때문에 실제로는 40 %보다 무겁다 -> 이 값은 하한이다. OpenSCAD 부피로 재확인할 것.
- 탄소관(D1/D2 구매품): OD 6 / ID 4 mm 가정, 밀도 1.5 g/cm3.
- 스틸봉(D4 베일): 밀도 7.85 g/cm3.

실행: python cad/cg/print_mass.py
"""
import math

PETG_DENSITY = 1.27      # g/cm3
INFILL = 0.40            # master-design §10-4
CF_DENSITY = 1.5         # g/cm3 (CF/에폭시 튜브)
STEEL_DENSITY = 7.85     # g/cm3

# cad/hopper_params.scad 에서 (2026-10-17 기준)
EDF_HOUSING_OD = 72
TOP_PLATE_R_EXTRA = 15   # top_plate() : r = col_mount_r + 15
INTAKE_CLEARANCE = 3     # 흡기홀 r = edf_housing_od/2 + 3
TOP_PLATE_T = 4
COL_OD = 6
TUBE_CLEARANCE = 0.3
COL_LEN = 200
N_COLS = 4
CF_ID = 4.0              # 탄소관 내경 가정 (외경 6 - 벽 2 x 1)
BAIL_OD = 3
BAIL_R_FACTOR = 0.6      # bail() : bail_r = col_mount_r * 0.6

VANE_RING_OD = EDF_HOUSING_OD + 24     # = 96
COL_MOUNT_R = VANE_RING_OD / 2         # = 48 = leg_top_r


def top_plate_vol_cm3():
    r_out = COL_MOUNT_R + TOP_PLATE_R_EXTRA
    v = math.pi * (r_out**2 - (EDF_HOUSING_OD / 2 + INTAKE_CLEARANCE) ** 2) * TOP_PLATE_T
    v -= N_COLS * math.pi * (COL_OD / 2 + TUBE_CLEARANCE) ** 2 * TOP_PLATE_T
    return v / 1000.0


def columns_vol_cm3():
    v = math.pi * ((COL_OD / 2) ** 2 - (CF_ID / 2) ** 2) * COL_LEN
    return N_COLS * v / 1000.0


def bail_vol_cm3():
    r = COL_MOUNT_R * BAIL_R_FACTOR
    arc_len = math.pi * r           # 180도 호
    return math.pi * (BAIL_OD / 2) ** 2 * arc_len / 1000.0


def main():
    parts = [
        ("top plate (PETG)", top_plate_vol_cm3(), PETG_DENSITY * INFILL),
        ("4x column (CF tube)", columns_vol_cm3(), CF_DENSITY),
        ("bail (steel rod)", bail_vol_cm3(), STEEL_DENSITY),
    ]
    total = 0.0
    for name, vol, dens in parts:
        m = vol * dens
        total += m
        print(f"{name:20s} vol {vol:6.2f} cm3  x {dens:.3f} g/cm3  = {m:5.1f} g")
    print(f"{'합계 (트레이 제외)':20s} {total:5.1f} g   "
          f"(기존 묶음 예산 90 g, 01 문서 §7.0에서 트레이 제거)")


if __name__ == "__main__":
    main()

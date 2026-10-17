"""
프린트·구조 부품 질량 (PRD #26, docs/tasks/26-cad-cg.md).

프린트 파츠 부피는 OpenSCAD 2026.10.15 로 `cad/hopper_params.scad` 를 파츠별로 렌더해
STL 에서 구했다 (`cad/print_parts/README.md` 의 개별 export 방법과 동일 — 라인 1~(조립 앞) +
파츠 호출 1줄). 질량 = 부피 x 밀도 x 인필(프린트만 40 %).

밀도 (g/cm3): PETG 1.27, CF 튜브/로드 1.5, 스틸 7.85, EVA 폼 0.07.

실행: python cad/cg/print_mass.py
"""
import math

PETG_DENSITY = 1.27
INFILL = 0.40          # master-design §10-4, 01 문서 §7.1
CF_DENSITY = 1.5       # CF/에폭시 튜브·로드
STEEL_DENSITY = 7.85
EVA_DENSITY = 0.07

# OpenSCAD 2026.10.15 render -> STL 부피 (cm3)
OPENSCAD_VOL_CM3 = {
    "top plate": 30.129,
    "vane ring": 130.944,
    "vanes x4": 10.724,
    "EDF clamp": 12.199,
    "battery shelf": 16.951,
    "avionics shelf": 18.603,
    "ESC bracket": 7.063,
    "vane couplers x4": 7.462,
    "foot pads x4": 6.416,
}

# hopper_params.scad 형상 변수 (2026-10-17)
EDF_HOUSING_OD = 72
RING_OD = EDF_HOUSING_OD + 24          # 96
LEG_TOP_R = RING_OD / 2                # 48
FOOT_CIRCLE = 360
LEG_BOT_R = FOOT_CIRCLE / 2            # 180
VANE_RING_BOT_Z = -50
FOOT_Z = -140
COL_OD = 6
COL_LEN = 200
N_COLS = 4
CF_ID = 4.0                            # 탄소관 내경 가정 (외경 6 - 벽 2x1)
LEG_OD = 6
N_LEGS = 4
SPAR_D = 3.0                           # Ø3 CF 로드(솔리드)
SPAR_LEN = 60                         # vane_spar_len
N_SPARS = 4
BAIL_OD = 3.0
BAIL_R = LEG_TOP_R * 0.6               # col_mount_r * 0.6


def tube_cm3(od, id_, length):
    return math.pi * ((od / 2) ** 2 - (id_ / 2) ** 2) * length / 1000.0


def rod_cm3(d, length):
    return math.pi * (d / 2) ** 2 * length / 1000.0


def main():
    petg = lambda v: v * PETG_DENSITY * INFILL
    rows = []
    for name, v in OPENSCAD_VOL_CM3.items():
        dens = EVA_DENSITY if "foot pads" in name else PETG_DENSITY * INFILL
        rows.append((name + (" (EVA)" if "foot pads" in name else " (PETG)"),
                     v, v * dens))
    rows.append(("column x4 (CF tube)", N_COLS * tube_cm3(COL_OD, CF_ID, COL_LEN),
                 N_COLS * tube_cm3(COL_OD, CF_ID, COL_LEN) * CF_DENSITY))
    leg_len = math.hypot(LEG_BOT_R - LEG_TOP_R, FOOT_Z - VANE_RING_BOT_Z)
    rows.append(("leg x4 (CF tube)", N_LEGS * tube_cm3(LEG_OD, CF_ID, leg_len),
                 N_LEGS * tube_cm3(LEG_OD, CF_ID, leg_len) * CF_DENSITY))
    rows.append(("vane spar x4 (CF rod)", N_SPARS * rod_cm3(SPAR_D, SPAR_LEN),
                 N_SPARS * rod_cm3(SPAR_D, SPAR_LEN) * CF_DENSITY))
    arc = math.pi * BAIL_R
    rows.append(("bail (steel rod OD3)", rod_cm3(BAIL_OD, arc),
                 rod_cm3(BAIL_OD, arc) * STEEL_DENSITY))

    total = 0.0
    print(f"{'part':28s} {'vol cm3':>9s} {'mass g':>8s}")
    for name, v, m in rows:
        total += m
        print(f"{name:28s} {v:9.3f} {m:8.2f}")
    print(f"{'합계 (프린트+구조, 배선/구매 제외)':28s} {'':>9s} {total:8.2f}")
    print(f"\nleg 길이 = {leg_len:.1f} mm (ring r48 z-50 -> foot r180 z-140)")


if __name__ == "__main__":
    main()

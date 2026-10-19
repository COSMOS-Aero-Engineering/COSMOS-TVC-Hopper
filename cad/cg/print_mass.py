"""
프린트·구조 부품 질량 (PRD #26, docs/tasks/26-cad-cg.md).

프린트 파츠 부피는 OpenSCAD 2021.01 로 `cad/hopper_params.scad` 를 파츠별로 렌더해
STL 에서 구했다 (`cad/print_parts/README.md` 의 개별 export 방법과 동일 — 라인 1~(조립 앞) +
파츠 호출 1줄). 인필만 계산한 하한과 형상을 100 % 채운 값의 범위를 출력한다. 실제 슬라이서 질량이 아니다.

밀도 (g/cm3): PETG 1.27, CF 튜브/로드 1.5, 스틸 7.85, EVA 폼 0.07.

실행: python cad/cg/print_mass.py
"""
import math

PETG_DENSITY = 1.27
INFILL = 0.40          # master-design §10-4, 01 문서 §7.1
CF_DENSITY = 1.5       # CF/에폭시 튜브·로드
STEEL_DENSITY = 7.85
EVA_DENSITY = 0.07

# STL 부피 (cm3). 2026-10-19 #59 형상(export_print_parts.py, OpenSCAD 2021.01)으로 갱신
OPENSCAD_VOL_CM3 = {
    "top plate": 30.06217,
    "vane ring": 140.89477,
    "vanes x4": 10.72410,
    "EDF clamp": 15.07240,
    "battery shelf": 17.85008,
    "avionics shelf": 18.21783,
    "ESC bracket": 7.06320,
    "vane couplers x4": 7.11376,
    "foot pads x4": 5.70809,
}

# hopper_params.scad 형상 변수 (2026-10-17)
EDF_HOUSING_OD = 72
RING_OD = EDF_HOUSING_OD + 24          # 96
LEG_TOP_R = RING_OD / 2 + 8            # 56 = leg_root_r (#59: 기울인 소켓 보스)
FOOT_CIRCLE = 360
LEG_BOT_R = FOOT_CIRCLE / 2            # 180
VANE_RING_BOT_Z = -50
FOOT_Z = -140
COL_OD = 6
COL_LEN = 212                          # #59: 4S 팩 높이 때문에 200 -> 212
N_COLS = 4
CF_ID = 4.0                            # 탄소관 내경 가정 (외경 6 - 벽 2x1)
LEG_OD = 6
N_LEGS = 4
SPAR_D = 3.0                           # Ø3 CF 로드(솔리드)
SPAR_LEN = 60                         # vane_spar_len
N_SPARS = 4
BAIL_OD = 3.0
BAIL_R = 51                            # #59: 흡기 구멍과 상판 바깥 사이 (hopper_params.scad bail_r)


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

    print("주의: 아래 mass g는 인필만 계산한 하한이다. 외벽·상하면 질량이 빠져 있다.")
    print("PETG 출력물 범위(g, 밀도 1.27 가정):")
    for name, volume in OPENSCAD_VOL_CM3.items():
        if "foot pads" not in name:
            print(f"  {name}: {volume * PETG_DENSITY * INFILL:.2f}-{volume * PETG_DENSITY:.2f}")
    print("슬라이서 프로파일과 출력 후 실측으로 확정하기 전에는 아래 합계를 비행 질량으로 쓰지 않는다.")
    total = 0.0
    print(f"{'part':28s} {'vol cm3':>9s} {'mass g':>8s}")
    for name, v, m in rows:
        total += m
        print(f"{name:28s} {v:9.3f} {m:8.2f}")
    print(f"{'합계 (프린트+구조, 배선/구매 제외)':28s} {'':>9s} {total:8.2f}")
    print(f"\nleg 길이 = {leg_len:.1f} mm (leg root r{LEG_TOP_R:.0f} z{VANE_RING_BOT_Z} -> foot r{LEG_BOT_R:.0f} z{FOOT_Z})")


if __name__ == "__main__":
    main()

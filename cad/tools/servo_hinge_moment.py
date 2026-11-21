"""
베인 힌지모멘트 대 SG90 스톨 토크 비교 (이슈 #382). 책상 계산이다. 실측은 TC-2(#263)가 한다.

입력은 두 파일에서 읽는다(바뀌면 결과도 따라 바뀐다).
  - sim/sim_stage1/params.yaml : vane_geometry(inner_r_mm, outer_r_mm, chord_mm), CLalpha, mass, Kf, omega_t_per_throttle
  - cad/hopper_params.scad     : vane_chord, vane_inner_r, vane_stop_deg (베인 스파는 시위 중앙, 아래 PIVOT 주석)
나머지 입력은 이 파일 맨 위의 상수다. 각 상수에 출처 또는 "가정"을 적었다. 가정을 실측처럼 쓰지 않는다.

모델 (docs/design/sg90-hinge-moment.md 에 근거와 한계)
  q     = k_q · Ft / (2·A_eff)            제트 동압. 운동량: Ft = ρ·A·v², q = ½ρv² = Ft/(2A). 밀도는 약분된다.
  A_eff = π(R² − r_hub²)                   배기 단면적. r_hub(꼬리 원뿔 반경)는 #118 실측 전이라 가정 범위를 돈다.
  F     = q · S · CN(α)                    베인 1장의 법선력. S = (R − r_in)·chord
  M     = F · d                            힌지모멘트 = 서보가 내야 하는 토크(직결 구동, 기어비 1)
  d     = 피벗과 압력중심의 거리. 피벗이 시위 중앙이라 |d| ≤ chord/2 가 기하 한계다(힘이 판 위에 걸리므로).

표준 라이브러리만 쓴다. 실행: python3 cad/tools/servo_hinge_moment.py
"""
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARAMS = ROOT / "sim" / "sim_stage1" / "params.yaml"
SCAD = ROOT / "cad" / "hopper_params.scad"

G = 9.80665                  # m/s², 1 kgf = 9.80665 N (정의값)
KGFCM_TO_NM = G / 100.0      # 1 kgf·cm = 0.0980665 N·m

# --- 서보 스톨 토크 (kgf·cm) ----------------------------------------------------------------
# 제조사 TowerPro 제품 페이지(2026-11-21 직접 받아 확인):
#   SG90 Digital https://towerpro.com.tw/product/sg90-7/      "Stall torque: 1.8kg/cm(4.8v)", 0.1 s/60°(4.8 V)
#   SG90 Analog  https://towerpro.com.tw/product/sg90-analog/ "Stall torque: 1.8kg/cm(4.8v)", 0.12 s/60°(4.8 V)
#   Rapid Online 37-1330 PDF(2013-10판)도 1.8 kg/cm(4.8 V)다. SG90 페이지에 6 V 토크는 없다(전압 4.8 V만 적혀 있다).
# 단위 "kg/cm"는 kgf·cm로 읽는다(제조사 표기 관행).
SG90_STALL_DATASHEET = 1.8
# 낮은 쪽 비교값. 우리 서보가 TowerPro 정품인지 모른다(#243). 호환 서보 Feetech FS90은 1.3 kgf·cm(4.8 V)로 적는다
#   (Pololu FS90 사양 https://www.pololu.com/product/2818/specs). 이 값을 "SG90의 사양"으로 쓰지 않는다. 정품이 아닐 때의 하한 비교다.
SG90_STALL_CLONE_LOW = 1.3
# 이슈 #382 예비 계산 댓글은 "일부 자료가 1.2"라고 적었지만 출처를 찾지 못했다. 쓰지 않는다. 1.3 이하는 아래 break-even 표로 덮는다.

# --- 추력 (N) ---------------------------------------------------------------------------------
# 마스터 설계 L1: 정적 추력 1.3~1.45 kgf (판매 사양, 실측 아님. 실험 A 전). docs/design/00-hopper-master-design.md
THRUST_SPEC = (1.3 * G, 1.45 * G)

# --- 가정 (실측 아님) ---------------------------------------------------------------------------
#  r_hub: 꼬리 원뿔(모터 허브) 반경. #118이 실측한다. 0이면 허브 없음(A_eff 최대), 15 mm는 지름 30 mm 가정(근거 없는 상한 추정).
#  k_peak: 제트 속도 분포가 균일하지 않을 때 베인 구간 속도 / 평균 속도. 1.3은 가정이다(근거 없음). 동압은 제곱으로 커진다.
#  CN 상한 2π·α: 무한 스팬 얇은 판 이론 기울기. 종횡비 1.12 베인은 이보다 작다(Helmbold 1.637/rad).
#           실제 베인의 법선력이 이 값을 넘을 수 있는지는 확인하지 못했다. 그래서 "상한"이라 부르지 않고 "가정 상한"으로 쓴다.
#  d: 얇은 판 이론에서 압력중심은 시위 앞쪽 25 %(양력 중심). 피벗이 시위 50 %이므로 6.25 mm. 저종횡비에서 이 위치는 실측이 없다.
SAFETY_FACTOR_REQUIRED = 2.0  # 가정: 스톨 토크의 절반 이하로 쓴다. 근거 문헌 없음. TowerPro는 연속 허용 토크를 적지 않았다.


def read_scad(name):
    m = re.search(rf"^\s*{re.escape(name)}\s*=\s*([-0-9.]+)\s*;", SCAD.read_text(encoding="utf-8"), re.M)
    if not m:
        sys.exit(f"{SCAD}에서 {name}을 찾지 못했다")
    return float(m.group(1))


def read_yaml_number(key):
    """params.yaml의 'key: 숫자' 줄(들여쓰기 무관, 첫 번째)을 읽는다. yaml 패키지 없이 표준 라이브러리만 쓴다."""
    m = re.search(rf"^\s*{re.escape(key)}:\s*([-0-9.eE+]+)", PARAMS.read_text(encoding="utf-8"), re.M)
    if not m:
        sys.exit(f"{PARAMS}에서 {key}를 찾지 못했다")
    return float(m.group(1))


def load_inputs():
    d = {
        "inner_r": read_yaml_number("inner_r_mm") / 1000.0,
        "outer_r": read_yaml_number("outer_r_mm") / 1000.0,
        "chord": read_yaml_number("chord_mm") / 1000.0,
        "CLalpha": read_yaml_number("CLalpha"),
        "mass": read_yaml_number("mass"),
        "Kf": read_yaml_number("Kf"),
        "omega_t_per_throttle": read_yaml_number("omega_t_per_throttle"),
        "scad_chord": read_scad("vane_chord") / 1000.0,
        "scad_inner_r": read_scad("vane_inner_r") / 1000.0,
        "stop_deg": read_scad("vane_stop_deg"),
    }
    # params.yaml의 베인 기하는 CAD에서 옮긴 값이다. 어긋나면 어느 쪽이 맞는지 모르니 멈춘다.
    if abs(d["chord"] - d["scad_chord"]) > 1e-9 or abs(d["inner_r"] - d["scad_inner_r"]) > 1e-9:
        sys.exit("params.yaml vane_geometry와 hopper_params.scad의 chord/inner_r가 다르다. 먼저 맞춘다.")
    return d


def hinge_moment(Ft, alpha_deg, cn_model, d_arm, k_peak, r_hub, g):
    """베인 1장 힌지모멘트 [N·m]. cn_model: 'repo'(CLalpha·α) 또는 'plate'(2π·α)."""
    R, rin, c = g["outer_r"], g["inner_r"], g["chord"]
    a = math.radians(alpha_deg)
    A_eff = math.pi * (R ** 2 - r_hub ** 2)
    q = (k_peak ** 2) * Ft / (2.0 * A_eff)
    S = (R - rin) * c
    CN = (g["CLalpha"] if cn_model == "repo" else 2 * math.pi) * a
    F = q * S * CN
    return F * d_arm, dict(q=q, S=S, CN=CN, F=F, A_eff=A_eff)


def kgfcm(nm):
    return nm / KGFCM_TO_NM


def main():
    g = load_inputs()
    c = g["chord"]
    stop = g["stop_deg"]
    Ft_params_max = g["Kf"] * (g["omega_t_per_throttle"] ** 2)
    Ft_hover = g["mass"] * G
    d_nom, d_max = c / 4, c / 2

    # 자체 검사: 손계산(이슈 댓글 예비 계산)과 같은 자릿수여야 한다.
    _, p = hinge_moment(THRUST_SPEC[0], 15, "plate", d_nom, 1.0, 0.0, g)
    assert abs(p["q"] - 1982) < 20, p["q"]          # q ≈ 1,980 Pa (이슈 #382 댓글)
    assert abs(p["S"] - 7.0e-4) < 1e-6, p["S"]       # S = 28 mm × 25 mm
    assert abs(kgfcm(0.0143) - 0.146) < 0.002
    assert abs(KGFCM_TO_NM - 0.0980665) < 1e-9

    print("## 입력 (읽은 위치)")
    print(f"- 베인 안쪽 r {g['inner_r']*1e3:.1f} mm, 제트 바깥 R {g['outer_r']*1e3:.1f} mm(추정), 시위 {c*1e3:.1f} mm "
          f"-> S = {(g['outer_r']-g['inner_r'])*c*1e6:.0f} mm² (params.yaml vane_geometry, CAD와 chord·inner_r 일치 확인)")
    print(f"- CAD 하드스톱 ±{stop:.0f}°, 시뮬 alpha_max 10°")
    print(f"- CLalpha(repo, 저종횡비 보정) {g['CLalpha']:.3f}/rad, 2π 판 이론 {2*math.pi:.3f}/rad")
    print(f"- 추력: 판매 사양 {THRUST_SPEC[0]:.2f}-{THRUST_SPEC[1]:.2f} N, params.yaml 100 % 스로틀 {Ft_params_max:.2f} N, "
          f"호버(질량 {g['mass']} kg) {Ft_hover:.2f} N")
    print(f"- 피벗 = 시위 중앙(CAD vane_one: 판은 pivot_z ± chord/2, 스파는 pivot_z). d 공칭 {d_nom*1e3:.2f} mm(시위 25 %), "
          f"기하 한계 {d_max*1e3:.2f} mm(시위 50 %)")

    cases = [
        # 이름, 추력, 각, CN모델, d, k_peak(속도비), r_hub
        ("공칭 (params.yaml 그대로)", Ft_params_max, 10, "repo", d_nom, 1.0, 0.0),
        ("사양 추력 하한, 하드스톱 15°", THRUST_SPEC[0], stop, "repo", d_nom, 1.0, 0.0),
        ("보수: 사양 하한, 15°, 판 이론 CN, d 25 %", THRUST_SPEC[0], stop, "plate", d_nom, 1.0, 0.0),
        ("보수+: 위에 d 50 %(기하 한계)", THRUST_SPEC[0], stop, "plate", d_max, 1.0, 0.0),
        ("겹침: 사양 상한, 15°, 판 이론, d 50 %, 속도 1.3배, 허브 반경 15 mm", THRUST_SPEC[1], stop, "plate", d_max, 1.3, 0.015),
    ]
    print("\n## 필요 모멘트 (베인 1장, 직결 구동) 대 서보 스톨 토크")
    print("| 경우 | Ft N | 각 ° | q Pa | CN | F N | d mm | M N·m | M kgf·cm | 여유(1.8) | 여유(1.3) |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    rows = []
    for name, Ft, a, cn, d, kp, rh in cases:
        M, p = hinge_moment(Ft, a, cn, d, kp, rh, g)
        mk = kgfcm(M)
        rows.append((name, mk))
        print(f"| {name} | {Ft:.2f} | {a:.0f} | {p['q']:.0f} | {p['CN']:.2f} | {p['F']:.2f} | {d*1e3:.2f} | {M:.4f} | {mk:.3f} | "
              f"{SG90_STALL_DATASHEET/mk:.1f} | {SG90_STALL_CLONE_LOW/mk:.1f} |")

    # 민감도: 겹침 경우에서 입력 하나씩만 공칭으로 되돌렸을 때 모멘트가 얼마나 줄어드는가.
    base = dict(Ft=THRUST_SPEC[1], a=stop, cn="plate", d=d_max, kp=1.3, rh=0.015)
    print("\n## 민감도 (겹침 경우에서 한 입력만 낮은 값으로 바꿈)")
    print("| 바꾼 입력 | M kgf·cm | 여유(1.8) |")
    print("|---|---:|---:|")
    alts = [("겹침 그대로", {}), ("추력 상한 → 하한(12.75 N)", dict(Ft=THRUST_SPEC[0])),
            ("각 15° → 10°", dict(a=10)), ("CN 판 이론 → repo(저종횡비)", dict(cn="repo")),
            ("d 50 % → 25 %", dict(d=d_nom)), ("속도 1.3배 → 균일", dict(kp=1.0)), ("허브 15 mm → 0", dict(rh=0.0))]
    for name, ch in alts:
        b = {**base, **ch}
        M, _ = hinge_moment(b["Ft"], b["a"], b["cn"], b["d"], b["kp"], b["rh"], g)
        print(f"| {name} | {kgfcm(M):.3f} | {SG90_STALL_DATASHEET/kgfcm(M):.1f} |")

    # break-even: 공칭·보수·겹침 각각에서 스톨(여유 1) 또는 여유 2에 닿으려면 모멘트가 몇 배가 돼야 하는가.
    print("\n## 모르는 부하가 얼마나 더 붙어도 되나 (서보 스톨 1.8 kgf·cm 기준)")
    print(f"여유 {SAFETY_FACTOR_REQUIRED:.0f}배(가정)를 지키려면 공력 외 부하(부싱 마찰·스파 비틀림·백래시 등 합)가 아래 값 이하여야 한다.")
    print("| 경우 | 공력 M kgf·cm | 여유 2배 허용 한도 kgf·cm | 공력 외 부하 허용치 kgf·cm | 모멘트를 몇 배 키워도 여유 2배 |")
    print("|---|---:|---:|---:|---:|")
    for name, mk in rows:
        lim = SG90_STALL_DATASHEET / SAFETY_FACTOR_REQUIRED
        print(f"| {name} | {mk:.3f} | {lim:.2f} | {max(lim-mk,0):.2f} | {lim/mk:.1f} |")
    worst = max(mk for _, mk in rows)
    print(f"\n최악(겹침) 경우 M = {worst:.3f} kgf·cm. 데이터시트 1.8 대비 여유 {SG90_STALL_DATASHEET/worst:.1f}배, "
          f"호환 서보 하한 1.3 대비 {SG90_STALL_CLONE_LOW/worst:.1f}배.")
    # 모멘트를 스톨과 같게 만드는 법선력 계수(공칭 형상, d 한계) — CN이 얼마나 커야 SG90이 멈추는가.
    Ft, kp, rh = THRUST_SPEC[1], 1.3, 0.015
    A = math.pi * (g["outer_r"] ** 2 - rh ** 2)
    q = kp ** 2 * Ft / (2 * A)
    S = (g["outer_r"] - g["inner_r"]) * c
    for lab, T in (("1.8", SG90_STALL_DATASHEET), ("1.3", SG90_STALL_CLONE_LOW)):
        for dl, d in (("d 25 %", d_nom), ("d 50 %", d_max)):
            cn = T * KGFCM_TO_NM / (q * S * d)
            print(f"스톨 {lab} kgf·cm에 닿는 법선력 계수 CN = {cn:.2f} (겹침 입력의 추력·속도·허브, {dl}) (비교: 2π·15° = 1.65)")


if __name__ == "__main__":
    main()

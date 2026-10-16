"""
BNO085 SPI 넷 대조표 초안 (PRD #26 이민우 담당 6절).

gen_schematic.py의 COMPONENTS(회로도를 만드는 원본)에서 Teensy IMU 핀 그룹(J3)과 BNO085(J6)의
넷 이름을 읽어, 01-avionics-integration-final.md 2.2절 핀맵과 같은지 표로 보여 준다.

이건 '회로도를 만든 원본 스크립트'를 대조하는 것이다. 실제 .kicad_sch를 KiCad로 열어 같은 넷이
그려져 있는지 눈으로 확인하는 일과 ERC 실행은 여전히 사람이 한다(kicad/README.md).

실행: python kicad/_tools/check_imu_nets.py   (KiCad 설치 없이 동작, 표준 라이브러리만 씀)
"""
import ast
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# 01-avionics 2.2 / 2.4, firmware/cosmos/imu_test/src/imu_test.ino 배선 주석 (10/15 실물 실크 확인)
EXPECTED = [
    # 신호, Teensy 핀, 넷 이름, GY 모듈 실크
    ("CS", "10", "IMU_CS", "CS"),
    ("MOSI", "11", "IMU_MOSI", "ADDR/MOSI"),
    ("MISO", "12", "IMU_MISO", "SDA/MISO/TX"),
    ("SCK", "13", "IMU_SCK", "SCL/SCK/RX"),
    ("RST", "20", "IMU_RST", "RST"),
    ("INT", "21", "IMU_INT", "INT"),
    ("WAK/PS0", "22", "IMU_WAK", "PS0"),
    ("PS1", "3V3", "+3V3", "PS1"),
    ("VIN", "3V3", "+3V3", "VCC_3V3"),
    ("GND", "G", "GND", "GND"),
]
# J3 값 "Teensy D10-13,20-22": 핀 1~7이 Teensy 10, 11, 12, 13, 20, 21, 22 순서
J3_TEENSY_PIN = {"1": "10", "2": "11", "3": "12", "4": "13", "5": "20", "6": "21", "7": "22"}
# J6 심볼 핀 이름 (gen_schematic.py J6 값 문자열의 순서)
J6_PIN_NAME = {"1": "CS", "2": "SCK", "3": "MOSI", "4": "MISO", "5": "INT", "6": "RST",
               "7": "WAK", "8": "PS1", "9": "VIN", "10": "GND"}


def load_components():
    """gen_schematic.py를 실행하지 않고(KiCad 경로가 필요하므로) COMPONENTS 리터럴만 읽는다."""
    src = open(os.path.join(HERE, "gen_schematic.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    consts = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name == "NC":
                consts["NC"] = ast.literal_eval(node.value)
            if name == "COMPONENTS":
                text = ast.get_source_segment(src, node.value).replace("NC", repr(consts.get("NC", "__NC__")))
                return ast.literal_eval(text)
    raise SystemExit("gen_schematic.py에서 COMPONENTS를 찾지 못했다")


def main():
    comps = {c[0]: c for c in load_components()}
    j3, j6 = comps["J3"][4], comps["J6"][4]
    teensy_net = {J3_TEENSY_PIN[p]: net for p, net in j3.items()}
    j6_by_name = {J6_PIN_NAME[p]: net for p, net in j6.items()}

    print("| 신호 | Teensy 핀 | 기대 넷 | Teensy 쪽(J3) 넷 | BNO085 쪽(J6) 핀 이름 -> 넷 | 실물 GY 실크 | 결과 |")
    print("|---|---|---|---|---|---|---|")
    bad = 0
    for sig, tpin, net, silk in EXPECTED:
        j6_name = "WAK" if sig == "WAK/PS0" else sig
        j6_net = j6_by_name.get(j6_name, "(없음)")
        t_net = teensy_net.get(tpin, "(전원/GND, J3 아님)")
        ok = j6_net == net and (tpin not in J3_TEENSY_PIN.values() or t_net == net)
        bad += not ok
        print(f"| {sig} | {tpin} | {net} | {t_net} | {j6_name} -> {j6_net} | {silk} | {'일치' if ok else '불일치'} |")
    print()
    print("원본 스크립트 기준 " + ("전부 일치" if bad == 0 else f"불일치 {bad}건"))
    print("남은 확인: KiCad에서 .kicad_sch를 열어 J6 핀 옆 레이블이 위 넷과 같은지 보고, ERC를 돌려 결과를 남긴다.")


if __name__ == "__main__":
    main()

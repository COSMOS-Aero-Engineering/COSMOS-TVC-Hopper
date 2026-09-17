#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COSMOS PRJ-01 — 보드 배치 도면 생성기 (빵판 / 만능기판)

`docs/design/01-avionics-integration-final.md` §4·§5 의 좌표표를 그대로 그림으로 그린다.
문서(표)와 도면(SVG)이 따로 놀지 않게, **좌표는 이 파일 한 곳에만** 적어두고 SVG를 생성한다.
좌표를 바꿀 일이 생기면 여기 PIN_MAP/배치 상수만 고치고 다시 실행할 것.

    python docs/design/tools/gen_board_svgs.py

출력:
    docs/design/avionics-breadboard.svg
    docs/design/avionics-perfboard.svg
"""

import os

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# ---------------------------------------------------------------- 공통 정의
# Teensy 4.0: 한 줄에 14핀 × 2줄. USB를 왼쪽으로 뒀을 때 왼→오 순서.
TEENSY_BOTTOM = ["GND", "0", "1", "2", "3", "4", "5", "6",
                 "7", "8", "9", "10", "11", "12"]
TEENSY_TOP    = ["VIN", "GND", "3V3", "23", "22", "21", "20", "19",
                 "18", "17", "16", "15", "14", "13"]

# 핀 용도 (01-avionics-integration-final.md §2.2) — 색으로 구분해서 그린다
USE = {
    "2": ("서보1 FWD", "servo"), "3": ("서보2 LEFT", "servo"),
    "4": ("서보3 AFT", "servo"),  "5": ("서보4 RIGHT", "servo"),
    "8": ("DShot→ESC", "esc"),
    "9": ("RC CH5 킬", "rc"), "18": ("RC CH1 스로틀", "rc"),
    "19": ("RC CH2 롤", "rc"), "23": ("RC CH3 피치", "rc"), "1": ("RC CH4 요", "rc"),
    "10": ("IMU CS", "imu"), "11": ("MOSI", "imu"), "12": ("MISO", "imu"),
    "13": ("SCK", "imu"), "20": ("IMU RST", "imu"), "21": ("IMU INT", "imu"),
    "22": ("IMU WAK/PS0", "imu"),
    "7": ("SD CS(선택)", "rsv"), "6": ("광류CS 예약", "rsv"), "0": ("예약", "rsv"),
    "14": ("ESP32 TX 예약", "rsv"), "15": ("ESP32 RX 예약", "rsv"),
    "16": ("ToF SCL1 예약", "rsv"), "17": ("ToF SDA1 예약", "rsv"),
    "3V3": ("3.3V 출력", "pwr"), "VIN": ("5V 입력", "pwr"), "GND": ("접지", "gnd"),
}

COLOR = {
    "servo": "#1f6feb", "esc": "#b4551f", "rc": "#7a3fa8", "imu": "#2f7d5d",
    "rsv": "#9aa7b0", "pwr": "#c0392b", "gnd": "#3d4a52",
}

CSS = """
  .bg{fill:#ffffff}
  .brd{fill:#f2f5f7;stroke:#94a3ac;stroke-width:1.4}
  .hole{fill:#ffffff;stroke:#b9c4cb;stroke-width:0.8}
  .ch{fill:#e3e9ed;stroke:#b9c4cb;stroke-width:1}
  .t{font-family:Helvetica,Arial,sans-serif;fill:#152029}
  .title{font-size:17px;font-weight:bold}
  .sub{font-size:11.5px;fill:#5b6b75}
  .lbl{font-size:10px}
  .lblb{font-size:11px;font-weight:bold}
  .tiny{font-size:8.5px;fill:#5b6b75}
  .warn{font-size:11px;font-weight:bold;fill:#b4551f}
  .chip{fill:#2b3a42;stroke:#16212a;stroke-width:1.2}
  .mod{fill:#e8f1ec;stroke:#2f7d5d;stroke-width:1.4}
  .mod2{fill:#f4e9f7;stroke:#7a3fa8;stroke-width:1.4}
  .mod3{fill:#fbeadd;stroke:#b4551f;stroke-width:1.4}
  .note{fill:#fff8f2;stroke:#e6c9b0}
  .railp{stroke:#c0392b;stroke-width:2;fill:none}
  .railn{stroke:#3d4a52;stroke-width:2;fill:none}
  .bus{stroke:#152029;stroke-width:3;fill:none;stroke-linecap:round}
"""


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def txt(x, y, s, cls="lbl", anchor="start", rot=None, fill=None):
    f = ' fill="%s"' % fill if fill else ""
    r = ' transform="rotate(%g %g %g)"' % (rot, x, y) if rot is not None else ""
    return ('<text class="t %s" x="%g" y="%g" text-anchor="%s"%s%s>%s</text>'
            % (cls, x, y, anchor, f, r, esc(s)))


# ================================================================ 빵판 도면
def breadboard():
    P = 17.0                      # 홀 피치(px) — 실물 2.54mm
    NCOL = 30
    L, T = 90.0, 150.0            # 보드 왼쪽 위 기준점(첫 홀 중심)
    rows = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]

    def hx(c):                    # 열(1~30) → x
        return L + (c - 1) * P

    def hy(r):                    # 행 문자 → y (E와 F 사이에 채널)
        i = rows.index(r)
        return T + i * P + (P if i >= 5 else 0)

    W, H = 1180, 640
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">' % (W, H),
         "<style>%s</style>" % CSS,
         '<rect class="bg" x="0" y="0" width="%d" height="%d"/>' % (W, H)]

    o.append(txt(28, 34, "COSMOS 호퍼 — 빵판(브레드보드) 배치도  [Week 1 벤치 전용]", "title"))
    o.append(txt(28, 54, "01-avionics-integration-final.md §4 의 좌표표와 1:1. "
                         "비행·구속시험에는 쓰지 않는다(§5.5) — 같은 배선을 만능기판으로 옮겨 납땜한다.", "sub"))
    o.append(txt(28, 72, "Teensy 4.0 은 USB 커넥터가 왼쪽(1열 방향)을 향하게, 가운데 홈을 걸치도록 꽂는다.", "sub"))

    # 보드 외곽
    bw = (NCOL - 1) * P + 2 * P
    bh = 11 * P + 2 * P
    o.append('<rect class="brd" x="%g" y="%g" width="%g" height="%g" rx="6"/>'
             % (L - P, T - P - 46, bw, bh + 92))

    # 전원 레일 (위/아래)
    for yy, sign in ((T - P - 30, "+"), (T - P - 14, "-")):
        cls = "railp" if sign == "+" else "railn"
        o.append('<line class="%s" x1="%g" y1="%g" x2="%g" y2="%g"/>'
                 % (cls, L - 6, yy, hx(NCOL) + 6, yy))
        o.append(txt(L - 16, yy + 4, sign, "lblb", "end",
                     fill="#c0392b" if sign == "+" else "#3d4a52"))
    ybotp = T + 11 * P + 16
    ybotn = T + 11 * P + 32
    for yy, sign in ((ybotn, "+"), (ybotp, "-")):
        cls = "railp" if sign == "+" else "railn"
        o.append('<line class="%s" x1="%g" y1="%g" x2="%g" y2="%g"/>'
                 % (cls, L - 6, yy, hx(NCOL) + 6, yy))
        o.append(txt(L - 16, yy + 4, sign, "lblb", "end",
                     fill="#c0392b" if sign == "+" else "#3d4a52"))

    # 가운데 채널
    o.append('<rect class="ch" x="%g" y="%g" width="%g" height="%g"/>'
             % (L - P / 2, hy("E") + P / 2, (NCOL - 1) * P + P, P))

    # 홀
    for c in range(1, NCOL + 1):
        for r in rows:
            o.append('<circle class="hole" cx="%g" cy="%g" r="3.2"/>' % (hx(c), hy(r)))
    # 열/행 번호
    for c in range(1, NCOL + 1):
        if c % 5 == 0 or c == 1:
            o.append(txt(hx(c), T - P - 52 + 46 - 4, str(c), "tiny", "middle"))
            o.append(txt(hx(c), T + 11 * P + 6, str(c), "tiny", "middle"))
    for r in rows:
        o.append(txt(L - P - 10, hy(r) + 3, r, "tiny", "middle"))
        o.append(txt(hx(NCOL) + P - 4, hy(r) + 3, r, "tiny", "middle"))

    # ---- Teensy 4.0 (5~18열, E행=윗줄 / F행=아랫줄)
    c0, c1 = 5, 18
    tx0, tx1 = hx(c0) - P / 2, hx(c1) + P / 2
    o.append('<rect class="chip" x="%g" y="%g" width="%g" height="%g" rx="4" opacity="0.92"/>'
             % (tx0, hy("E") - 8, tx1 - tx0, hy("F") - hy("E") + 16))
    o.append(txt((tx0 + tx1) / 2, hy("E") + (hy("F") - hy("E")) / 2 + 4,
                 "Teensy 4.0", "lblb", "middle", fill="#ffffff"))
    o.append('<rect x="%g" y="%g" width="10" height="26" rx="2" fill="#8c98a0"/>'
             % (tx0 - 10, hy("E") + 14))
    o.append(txt(tx0 - 14, hy("E") + 8, "USB", "tiny", "end"))

    # 핀 라벨: 칩 바로 위/아래에 세로로 (용도 설명은 오른쪽 표로 뺀다 — 겹침 방지)
    for i, name in enumerate(TEENSY_TOP):
        c = c0 + i
        col = COLOR[USE.get(name, ("", "rsv"))[1]]
        o.append('<circle cx="%g" cy="%g" r="3.4" fill="%s"/>' % (hx(c), hy("E"), col))
        o.append(txt(hx(c) + 3, hy("C") - 2, name, "lblb", "end", rot=-90, fill=col))
    for i, name in enumerate(TEENSY_BOTTOM):
        c = c0 + i
        col = COLOR[USE.get(name, ("", "rsv"))[1]]
        o.append('<circle cx="%g" cy="%g" r="3.4" fill="%s"/>' % (hx(c), hy("F"), col))
        o.append(txt(hx(c) - 3, hy("H") + 2, name, "lblb", "start", rot=-90, fill=col))

    # ---- BNO085 모듈 (21~26열, F행에 핀)
    bx0, bx1 = hx(21) - P / 2, hx(26) + P / 2
    o.append('<rect class="mod" x="%g" y="%g" width="%g" height="%g" rx="4"/>'
             % (bx0, hy("F") - 10, bx1 - bx0, 3 * P))
    o.append(txt((bx0 + bx1) / 2, hy("F") + 14, "BNO085 (SPI)", "lblb", "middle"))
    o.append(txt((bx0 + bx1) / 2, hy("G") + 14, "PS1→3V3 로 SPI 모드", "tiny", "middle"))
    for i, nm in enumerate(["VIN", "GND", "SCK", "SI", "SO", "CS"]):
        o.append('<circle cx="%g" cy="%g" r="3.4" fill="#2f7d5d"/>' % (hx(21 + i), hy("F")))
        o.append(txt(hx(21 + i), hy("F") - 14, nm, "tiny", "middle"))
    o.append(txt(L - P, ybotp + 44,
                 "※ BNO085 의 INT(21)·RST(20)·WAK/PS0(22)·PS1 은 모듈 핀 배열에 맞춰 남은 홀에 꽂는다 "
                 "— 모듈마다 핀 순서가 달라 실물 실크를 보고 결정.", "tiny"))

    # ---- 레벨시프터 (21~26열, A~C)
    lx0, lx1 = hx(21) - P / 2, hx(26) + P / 2
    o.append('<rect class="mod2" x="%g" y="%g" width="%g" height="%g" rx="4"/>'
             % (lx0, hy("A") - 10, lx1 - lx0, 3 * P))
    o.append(txt((lx0 + lx1) / 2, hy("B") + 4, "레벨시프터 4ch (BSS138)", "lblb", "middle"))
    o.append(txt((lx0 + lx1) / 2, hy("C") + 6, "HV=5V(수신기) / LV=3.3V(Teensy)", "tiny", "middle"))
    o.append(txt((lx0 + lx1) / 2, hy("C") + 18, "※ 핀 간격은 제품마다 다름 — 실물 보고 열 조정", "tiny", "middle"))

    # ---- 핀 용도 표 (보드 위에 글자를 얹지 않고 옆으로 뺀다)
    ux, uy = 640, 150
    o.append(txt(ux, uy - 12, "Teensy 핀 용도 (§2.2)", "lblb"))
    order = [("18", "RC CH1 스로틀"), ("19", "RC CH2 롤"), ("23", "RC CH3 피치"),
             ("1", "RC CH4 요"), ("9", "RC CH5 킬"), ("2", "서보1 FWD"),
             ("3", "서보2 LEFT"), ("4", "서보3 AFT"), ("5", "서보4 RIGHT"),
             ("8", "DShot → ESC"), ("10", "IMU CS"), ("11", "IMU MOSI"),
             ("12", "IMU MISO"), ("13", "IMU SCK"), ("20", "IMU RST"),
             ("21", "IMU INT"), ("22", "IMU WAK/PS0")]
    for i, (pin, use) in enumerate(order):
        yy = uy + 8 + i * 17
        col = COLOR[USE.get(pin, ("", "rsv"))[1]]
        o.append('<circle cx="%g" cy="%g" r="4.5" fill="%s"/>' % (ux + 6, yy - 4, col))
        o.append(txt(ux + 20, yy, "핀 %s" % pin, "lblb"))
        o.append(txt(ux + 66, yy, use, "lbl"))
    yy = uy + 8 + len(order) * 17 + 6
    o.append(txt(ux, yy, "나머지 핀(0·6·7·14~17)은 예약 — 비워둔다.", "tiny"))
    o.append(txt(ux, yy + 14, "3V3=BNO085·시프터LV / VIN=미연결(USB급전) / GND=공통", "tiny"))

    # ---- 보드 밖 부품
    def outbox(x, y, w, h, cls, title, lines):
        o.append('<rect class="%s" x="%g" y="%g" width="%g" height="%g" rx="5"/>' % (cls, x, y, w, h))
        o.append(txt(x + w / 2, y + 19, title, "lblb", "middle"))
        for k, ln in enumerate(lines):
            o.append(txt(x + w / 2, y + 36 + k * 14, ln, "tiny", "middle"))

    outbox(890, 150, 262, 86, "mod3", "ESC (DShot) — 보드 밖",
           ["신호선 → 핀 8 (14열 F행)",
            "GND → −레일  ★ 없으면 DShot 안 나감",
            "전원(굵은선)은 빵판에 절대 꽂지 않는다"])
    outbox(890, 256, 262, 86, "mod2", "FS-iA6B 수신기 — 보드 밖",
           ["CH1 스로틀 / CH5 킬 최소 2채널",
            "5V 신호 → 레벨시프터 경유 필수",
            "전원은 UBEC 5V 에서"])
    outbox(890, 362, 262, 100, "mod", "UBEC 5.5V — 보드 밖",
           ["서보 4개 전원 = UBEC 직결",
            "빵판 레일로 서보 전원 보내지 말 것",
            "(돌입전류로 접점이 탄다)",
            "GND 는 −레일과 공통"])

    # 점퍼 예시선 (IMU SPI 4선)
    for pin, modcol, color in (("10", 26, "#d4a017"), ("13", 23, "#1f6feb"),
                               ("11", 24, "#2f9e44"), ("12", 25, "#8c98a0")):
        if pin in TEENSY_BOTTOM:
            c = c0 + TEENSY_BOTTOM.index(pin)
            y0 = hy("J")
        else:
            c = c0 + TEENSY_TOP.index(pin)
            y0 = hy("A")
        x0 = hx(c)
        x1, y1 = hx(modcol), hy("J")
        o.append('<path d="M%g,%g C%g,%g %g,%g %g,%g" fill="none" stroke="%s" '
                 'stroke-width="2.2" opacity="0.85"/>'
                 % (x0, y0 + 6, x0, y0 + 60, x1, y1 + 60, x1, y1 + 6, color))

    # 주의 박스
    o.append('<rect class="note" x="28" y="%g" width="1124" height="86" rx="6"/>' % (H - 118))
    o.append(txt(44, H - 96, "안전 · 필독", "lblb"))
    o.append(txt(44, H - 78, "• 빵판에 들어오는 최고 전압은 5V. 4S(16.8V)는 한 가닥도 빵판에 오지 않는다.", "lbl"))
    o.append(txt(44, H - 60, "• 배선 변경은 항상 배터리를 물리적으로 분리한 뒤 (킬스위치만 믿지 않는다).", "lbl"))
    o.append(txt(44, H - 42, "• 전원 인가 순서: ① USB로 Teensy만 → ② UBEC·수신기 → ③ 마지막에 배터리 메인.", "lbl"))
    o.append(txt(44, H - 24, "• EDF는 추력 스탠드에 볼트로 고정된 상태에서만 회전시킨다. 보안경·방호판·지도교사 입회.", "warn"))

    o.append("</svg>")
    return "\n".join(o)


# ============================================================== 만능기판 도면
def perfboard():
    P = 24.0
    NC, NR = 24, 18
    L, B = 150.0, 640.0           # C1R1 홀 중심

    def hx(c):
        return L + (c - 1) * P

    def hy(r):
        return B - (r - 1) * P

    W, H = 1180, 780
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">' % (W, H),
         "<style>%s</style>" % CSS,
         '<rect class="bg" x="0" y="0" width="%d" height="%d"/>' % (W, H)]

    o.append(txt(28, 34, "COSMOS 호퍼 — 만능기판(비행용) 배치도 · 납땜 도면", "title"))
    o.append(txt(28, 54, "5×7cm 양면 만능기판(2.54mm 피치), 가로 24홀 × 세로 18홀 기준. "
                         "01-avionics-integration-final.md §5 좌표표와 1:1.", "sub"))
    o.append(txt(28, 72, "좌표: 왼쪽아래 홀 = C1R1, 오른쪽으로 C 증가, 위로 R 증가. "
                         "보드 실제 홀 수가 다르면 전체를 ±1 이동(가장자리에서 2홀 안쪽 유지).", "sub"))

    o.append('<rect class="brd" x="%g" y="%g" width="%g" height="%g" rx="4"/>'
             % (hx(1) - P, hy(NR) - P, (NC + 1) * P, (NR + 1) * P))

    for c in range(1, NC + 1):
        for r in range(1, NR + 1):
            o.append('<circle class="hole" cx="%g" cy="%g" r="3.0"/>' % (hx(c), hy(r)))
    for c in range(1, NC + 1):
        if c == 1 or c % 4 == 0:
            o.append(txt(hx(c), hy(NR) - P + 14, "C%d" % c, "tiny", "middle"))
    for r in range(1, NR + 1):
        if r == 1 or r % 3 == 0:
            o.append(txt(hx(1) - P - 6, hy(r) + 3, "R%d" % r, "tiny", "end"))

    # 버스
    o.append('<line class="bus" x1="%g" y1="%g" x2="%g" y2="%g" stroke="#3d4a52"/>'
             % (hx(1), hy(1), hx(NC), hy(1)))
    o.append(txt(hx(NC) + 12, hy(1) + 4, "GND 버스 (R1) — 별 접지의 중심", "lblb", fill="#3d4a52"))
    o.append('<line class="bus" x1="%g" y1="%g" x2="%g" y2="%g" stroke="#c0392b"/>'
             % (hx(1), hy(18), hx(NC), hy(18)))
    o.append(txt(hx(NC) + 12, hy(18) + 4, "+5V 버스 (R18) — UBEC 급전", "lblb", fill="#c0392b"))
    o.append('<line class="bus" x1="%g" y1="%g" x2="%g" y2="%g" stroke="#e06c2b" stroke-width="2.2"/>'
             % (hx(1), hy(17), hx(8), hy(17)))
    o.append(txt(hx(9), hy(17) + 4, "+3.3V (R17, C1~C8) ← Teensy 3V3", "tiny", fill="#e06c2b"))

    # 장착홀
    for (c, r) in ((2, 2), (23, 2), (2, 17), (23, 17)):
        o.append('<circle cx="%g" cy="%g" r="7.5" fill="#ffffff" stroke="#152029" stroke-width="1.6"/>'
                 % (hx(c), hy(r)))
        o.append('<circle cx="%g" cy="%g" r="2" fill="#152029"/>' % (hx(c), hy(r)))
    o.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#152029" stroke-width="1" '
             'stroke-dasharray="4 3"/>' % (hx(2), hy(2) + 26, hx(23), hy(2) + 26))
    o.append(txt((hx(2) + hx(23)) / 2, hy(2) + 42, "53.34 mm (Ø3.2 확공, M3 스탠드오프)", "lblb", "middle"))
    o.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#152029" stroke-width="1" '
             'stroke-dasharray="4 3"/>' % (hx(2) - 26, hy(2), hx(2) - 26, hy(17)))
    o.append(txt(hx(2) - 32, (hy(2) + hy(17)) / 2, "38.10 mm", "lblb", "end"))

    # Teensy 소켓 (R6 아랫줄 / R12 윗줄, C5~C18)
    o.append('<rect class="chip" x="%g" y="%g" width="%g" height="%g" rx="4" opacity="0.9"/>'
             % (hx(5) - P / 2, hy(12) - P / 2, 14 * P, 6 * P + P))
    o.append(txt((hx(5) + hx(18)) / 2, hy(9) + 5, "Teensy 4.0 (암핀헤더 소켓 2줄)", "lblb", "middle",
                 fill="#ffffff"))
    o.append('<rect x="%g" y="%g" width="12" height="30" rx="2" fill="#8c98a0"/>'
             % (hx(5) - P / 2 - 12, hy(9) - 15))
    o.append(txt(hx(5) - P / 2 - 16, hy(9) - 20, "USB", "tiny", "end"))
    for i, name in enumerate(TEENSY_TOP):
        c = 5 + i
        col = COLOR[USE.get(name, ("", "rsv"))[1]]
        o.append('<circle cx="%g" cy="%g" r="4" fill="%s"/>' % (hx(c), hy(12), col))
        o.append(txt(hx(c) + 3, hy(10), name, "tiny", "start", rot=-90, fill="#ffffff"))
    for i, name in enumerate(TEENSY_BOTTOM):
        c = 5 + i
        col = COLOR[USE.get(name, ("", "rsv"))[1]]
        o.append('<circle cx="%g" cy="%g" r="4" fill="%s"/>' % (hx(c), hy(6), col))
        o.append(txt(hx(c) + 3, hy(6) - 6, name, "tiny", "start", rot=-90, fill="#ffffff"))
    o.append(txt(hx(5) - P / 2, hy(12) + 2, "R12", "tiny", "end", fill="#ffffff"))
    o.append(txt(hx(5) - P / 2, hy(6) + 2, "R6", "tiny", "end", fill="#ffffff"))

    # IMU 소켓
    o.append('<rect class="mod" x="%g" y="%g" width="%g" height="%g" rx="4"/>'
             % (hx(15) - P / 2, hy(16) - P / 2, 6 * P, 2 * P))
    o.append(txt((hx(15) + hx(20)) / 2, hy(16) + 2, "BNO085 IMU (6핀 소켓, R15)", "lblb", "middle"))
    o.append(txt((hx(15) + hx(20)) / 2, hy(15) + 4, "수평으로 눕힌다 → 축이 기체축과 일치", "tiny", "middle"))
    o.append(txt((hx(15) + hx(20)) / 2, hy(15) + 18, "밑에 1mm 폼테이프(진동 절연)", "tiny", "middle"))

    # 캡
    o.append('<rect class="mod3" x="%g" y="%g" width="%g" height="%g" rx="4"/>'
             % (hx(2) - P / 2, hy(16) - P / 2, 3 * P, 2 * P))
    o.append(txt(hx(3), hy(16) + 2, "470µF", "lblb", "middle"))
    o.append(txt(hx(3), hy(15) + 4, "5V 레일 안정화", "tiny", "middle"))

    # 레벨시프터 2개
    o.append('<rect class="mod2" x="%g" y="%g" width="%g" height="%g" rx="4"/>'
             % (hx(3) - P / 2, hy(4) - P / 2, 6 * P, P))
    o.append(txt((hx(3) + hx(8)) / 2, hy(4) + 5, "레벨시프터 #1 (CH1·CH2)", "tiny", "middle"))
    o.append('<rect class="mod2" x="%g" y="%g" width="%g" height="%g" rx="4"/>'
             % (hx(11) - P / 2, hy(4) - P / 2, 6 * P, P))
    o.append(txt((hx(11) + hx(16)) / 2, hy(4) + 5, "레벨시프터 #2 (CH3·CH4·CH5)", "tiny", "middle"))

    # R3 헤더들
    for i, nm in enumerate(["S1", "S2", "S3", "S4"]):
        c = 1 + i * 3
        o.append('<rect x="%g" y="%g" width="%g" height="%g" rx="3" fill="#dbe6ef" stroke="#1f6feb"/>'
                 % (hx(c) - P / 2, hy(3) - P / 2, 3 * P, P))
        o.append(txt(hx(c + 1), hy(3) + 5, nm, "tiny", "middle"))
    o.append(txt(hx(1) - P / 2, hy(2) + 6, "서보 3핀 헤더 ×4 (신호-5V-GND)", "tiny"))
    for i, nm in enumerate(["CH1", "CH2", "CH3", "CH4", "CH5"]):
        c = 14 + i * 2
        if c + 1 > NC:
            break
        o.append('<rect x="%g" y="%g" width="%g" height="%g" rx="3" fill="#f0e6f7" stroke="#7a3fa8"/>'
                 % (hx(c) - P / 2, hy(3) - P / 2, 2 * P, P))
        o.append(txt(hx(c) + P / 2, hy(3) + 5, nm, "tiny", "middle"))
    o.append(txt(hx(14) - P / 2, hy(2) + 6, "RC 입력 헤더 ×5 (수신기)", "tiny"))
    o.append('<rect x="%g" y="%g" width="%g" height="%g" rx="3" fill="#fbeadd" stroke="#b4551f"/>'
             % (hx(22) - P / 2, hy(5) - P / 2, 2 * P, P))
    o.append(txt(hx(22) + P / 2, hy(5) + 5, "ESC", "tiny", "middle"))
    o.append(txt(hx(21), hy(6) + 4, "ESC 2핀(신호·GND)", "tiny"))

    # 범례
    lx, ly = 900, 120
    o.append(txt(lx, ly - 10, "핀 색 범례", "lblb"))
    for i, (k, nm) in enumerate([("servo", "서보 PWM"), ("esc", "DShot/ESC"), ("rc", "RC 입력"),
                                 ("imu", "IMU SPI"), ("pwr", "전원"), ("gnd", "접지"),
                                 ("rsv", "예약(지금 안 씀)")]):
        o.append('<circle cx="%g" cy="%g" r="5" fill="%s"/>' % (lx + 8, ly + 12 + i * 20, COLOR[k]))
        o.append(txt(lx + 22, ly + 16 + i * 20, nm, "lbl"))

    # 납땜 순서
    sx, sy = 900, 300
    o.append('<rect class="note" x="%g" y="%g" width="250" height="196" rx="6"/>' % (sx - 12, sy - 22))
    o.append(txt(sx, sy - 4, "납땜 순서 (§5.4)", "lblb"))
    for i, ln in enumerate(["1. 장착홀 4개 Ø3.2 확공 → 선반에 맞춰보기",
                            "2. GND·+5V 버스 주석선 (제일 먼저)",
                            "3. Teensy 암헤더 2줄 (정렬 확인 후)",
                            "4. 3핀 헤더 → 레벨시프터 → IMU 소켓",
                            "5. 핀맵대로 배선, 한 줄마다 체크",
                            "6. 무전원 도통·단락 검사",
                            "7. 5V만 인가 → 레일 확인 → Teensy 장착"]):
        o.append(txt(sx, sy + 16 + i * 22, ln, "tiny"))

    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    for name, data in (("avionics-breadboard.svg", breadboard()),
                       ("avionics-perfboard.svg", perfboard())):
        path = os.path.normpath(os.path.join(OUT_DIR, name))
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        print("wrote", path, len(data), "bytes")

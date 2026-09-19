#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COSMOS PRJ-01 — 시스템 도면 생성기 (전체 결선도 / 기계 통합도)

치수는 `cad/hopper_params.scad` rev C.1 과 같은 값을 여기에 한 번 더 적어두고 그림을 그린다.
CAD 값이 바뀌면 아래 GEO 딕셔너리만 고치고 다시 실행할 것.

    python docs/design/tools/gen_system_svgs.py

출력:
    docs/design/system-wiring-final.svg
    docs/design/mechanical-integration.svg
"""

import math
import os

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# ---- cad/hopper_params.scad rev C.1 과 동일한 값 (mm) -------------------------
GEO = dict(
    edf_od=72, edf_body_len=92, edf_clamp_z=70,
    col_len=200, top_plate_t=4, vane_gap_below_exit=22, vane_ring_h=28,
    foot_below_exit=140, foot_circle=360,
    ring_od=96, ring_id=76, col_r=48,
    shelf_top_z=150, shelf_t=3, shelf_r_inner=42,
    # batt_shelf_l = 접선(tangential) 방향, batt_shelf_w = 반경(radial) 방향 — cad/hopper_params.scad
    # equip_shelf_battery() 실측정: 접선 2*y_half=80, 반경 x_out-(shelf_r_inner-20)=70
    batt_shelf_l=80, batt_shelf_w=70, avio_shelf_l=84, avio_shelf_w=60,
    batt_l=63.5, batt_w=32.5, batt_h=15,  # 2026-09-19 실측 최종 (cad/measurements.md)
    servo_boss_t=4, servo_body_h=28,      # 2026-09-19 실측 최종
    vane_inner_r=4, vane_chord=25,
)
G = GEO
RING_TOP_Z = -G["vane_gap_below_exit"]                 # -22
RING_BOT_Z = RING_TOP_Z - G["vane_ring_h"]             # -50
VANE_PIVOT_Z = (RING_TOP_Z + RING_BOT_Z) / 2           # -36  (링 수직 중앙)
TOP_PLATE_BOT_Z = RING_TOP_Z + G["col_len"]            # 178
TOP_PLATE_TOP_Z = TOP_PLATE_BOT_Z + G["top_plate_t"]   # 182
FOOT_Z = -G["foot_below_exit"]                         # -140
COL_XY = G["col_r"] * math.cos(math.radians(45))       # 33.94

CSS = """
  .bg{fill:#ffffff}
  .t{font-family:Helvetica,Arial,sans-serif;fill:#152029}
  .title{font-size:17px;font-weight:bold}
  .sub{font-size:11.5px;fill:#5b6b75}
  .h{font-size:13px;font-weight:bold}
  .lbl{font-size:10.5px}
  .lblb{font-size:11px;font-weight:bold}
  .tiny{font-size:9px;fill:#5b6b75}
  .warn{font-size:10.5px;font-weight:bold;fill:#b4551f}
  .prt{fill:#e7edf2;stroke:#41525c;stroke-width:1.4}
  .prt2{fill:#dbe7f5;stroke:#1f6feb;stroke-width:1.4}
  .buy{fill:#f6efdc;stroke:#a8842c;stroke-width:1.4}
  .elec{fill:#e8f1ec;stroke:#2f7d5d;stroke-width:1.4}
  .hot{fill:#fbeadd;stroke:#b4551f;stroke-width:1.4}
  .flow{fill:#eaf2fb;stroke:none;opacity:0.75}
  .jet{fill:#fdeee2;stroke:none;opacity:0.85}
  .dim{stroke:#7d8ea0;stroke-width:0.8;fill:none}
  .axis{stroke:#b9c4cb;stroke-width:1;stroke-dasharray:6 4;fill:none}
  .pwr{fill:none;stroke:#c0392b;stroke-width:3.2}
  .pwr2{fill:none;stroke:#e08a3c;stroke-width:2.4}
  .sig{fill:none;stroke:#1f6feb;stroke-width:2}
  .gnd{fill:none;stroke:#6b7a83;stroke-width:1.8;stroke-dasharray:3 3}
  .note{fill:#fff8f2;stroke:#e6c9b0}
  .box{fill:#eef2f6;stroke:#2b3a42;stroke-width:1.6}
"""


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def txt(x, y, s, cls="lbl", anchor="start", rot=None, fill=None):
    f = ' fill="%s"' % fill if fill else ""
    r = ' transform="rotate(%g %g %g)"' % (rot, x, y) if rot is not None else ""
    return ('<text class="t %s" x="%.1f" y="%.1f" text-anchor="%s"%s%s>%s</text>'
            % (cls, x, y, anchor, f, r, esc(s)))


def rect(x, y, w, h, cls, rx=2):
    return ('<rect class="%s" x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%g"/>'
            % (cls, x, y, w, h, rx))


# ========================================================== 1. 전체 결선도
def system_wiring():
    W, H = 1240, 900
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">' % (W, H),
         "<style>%s</style>" % CSS, rect(0, 0, W, H, "bg", 0)]

    o.append(txt(28, 34, "COSMOS 호퍼 — 전체 결선도 (비행 형상, rev C.1)", "title"))
    o.append(txt(28, 54, "01-avionics-integration-final.md §2(핀맵)·§3(전원)·§6(하네스)와 1:1. "
                         "굵은 빨강 = 배터리 메인(최대 50A) / 주황 = 5V / 파랑 = 신호 / 점선 = 공통 GND", "sub"))

    # ---- 전원 계통 (왼쪽 열)
    o.append(rect(40, 96, 250, 58, "hot", 5))
    o.append(txt(165, 118, "4S LiPo 1300mAh 75C", "lblb", "middle"))
    o.append(txt(165, 136, "14.8~16.8V · XT60 · 배터리 선반(+Y)", "tiny", "middle"))

    o.append(rect(40, 186, 250, 52, "box", 5))
    o.append(txt(165, 206, "물리 킬스위치 (≥80A, 인라인)", "lblb", "middle"))
    o.append(txt(165, 223, "배터리 (+) 경로 · 상시 손 닿는 위치", "tiny", "middle"))
    o.append('<path class="pwr" d="M165,154 L165,186"/>')

    o.append(rect(40, 272, 250, 40, "box", 4))
    o.append(txt(165, 297, "470µF/35V 저ESR 캡 (ESC 입력단 20mm 내)", "tiny", "middle"))
    o.append('<path class="pwr" d="M165,238 L165,272"/>')

    o.append(rect(40, 344, 250, 70, "hot", 5))
    o.append(txt(165, 366, "ESC 60A · DShot600", "lblb", "middle"))
    o.append(txt(165, 383, "BEC 는 쓰지 않음(잘라내거나 절연)", "tiny", "middle"))
    o.append(txt(165, 399, "270° 브래킷 · 흡기 통과 공기로 냉각", "tiny", "middle"))
    o.append('<path class="pwr" d="M165,312 L165,344"/>')
    o.append(txt(178, 332, "H1 · 14AWG", "tiny"))

    o.append('<circle cx="165" cy="470" r="34" class="buy"/>')
    o.append(txt(165, 466, "64mm", "lblb", "middle"))
    o.append(txt(165, 481, "EDF", "lblb", "middle"))
    o.append('<path class="pwr" d="M150,414 L150,436 M165,414 L165,436 M180,414 L180,436"/>')
    o.append(txt(196, 430, "H2 · 3상(꼬아서)", "tiny"))

    o.append(rect(40, 560, 250, 58, "elec", 5))
    o.append(txt(165, 582, "UBEC 5.5V / 3A↑ (5A 권장)", "lblb", "middle"))
    o.append(txt(165, 599, "서보·수신기 전원 단일 소스", "tiny", "middle"))
    o.append('<path class="pwr" d="M75,212 L75,589 L40,589"/>')
    o.append(txt(80, 540, "H4 · 20AWG 배터리 탭", "tiny"))

    # ---- Teensy (가운데)
    o.append(rect(420, 150, 300, 300, "prt2", 8))
    o.append(txt(570, 178, "Teensy 4.0  (만능기판 위, 아비오닉스 선반 −Y)", "h", "middle"))
    o.append(txt(570, 196, "3.3V 로직 · USB 급전(STAGE 1) · USB 시리얼 로깅", "tiny", "middle"))

    pins_left = [("핀 8", "DShot → ESC", "#b4551f", 240),
                 ("핀 2~5", "서보 1~4 PWM", "#1f6feb", 280),
                 ("핀 18·19·23·1·9", "RC CH1~CH5", "#7a3fa8", 330),
                 ("핀 10~13·20·21·22", "BNO085 SPI", "#2f7d5d", 380),
                 ("GND", "공통 접지", "#6b7a83", 424)]
    for name, use, col, y in pins_left:
        o.append('<circle cx="420" cy="%d" r="5" fill="%s"/>' % (y, col))
        o.append(txt(432, y - 6, name, "lblb", "start", fill=col))
        o.append(txt(432, y + 8, use, "tiny"))

    o.append(txt(570, 444, "핀 7·6·14~17 = 예약(SD·광류·ESP32·ToF)", "tiny", "middle"))

    # ESC ← 신호
    o.append('<path class="sig" d="M420,240 C350,240 320,378 290,378"/>')
    o.append(txt(300, 262, "H3 신호", "tiny"))
    o.append('<path class="gnd" d="M420,424 C350,424 330,400 290,400"/>')
    o.append(txt(300, 418, "GND 공통 — 없으면 DShot 안 나감", "warn"))

    # ---- 오른쪽: 서보 · 수신기 · IMU
    o.append(rect(830, 150, 330, 120, "elec", 6))
    o.append(txt(995, 174, "BNO085 IMU (SPI)", "h", "middle"))
    o.append(txt(995, 194, "만능기판 위, 수평으로 눕힘 → 축 = 기체축", "tiny", "middle"))
    o.append(txt(995, 211, "PS1→3V3, PS0→핀22 로 SPI 모드 고정", "tiny", "middle"))
    o.append(txt(995, 228, "밑에 1mm 폼테이프(진동 절연)", "tiny", "middle"))
    o.append(txt(995, 252, "중심축에서 약 65mm 오프셋 — 자세엔 무영향", "tiny", "middle"))
    o.append('<path class="sig" d="M720,380 C780,380 780,210 830,210"/>')

    o.append(rect(830, 300, 330, 150, "prt2", 6))
    o.append(txt(995, 324, "베인 서보 MG90S ×4 (직결 구동)", "h", "middle"))
    for i, (nm, az) in enumerate([("S1  FWD  0°", 0), ("S2  LEFT  90°", 90),
                                  ("S3  AFT  180°", 180), ("S4  RIGHT 270°", 270)]):
        o.append(rect(852 + (i % 2) * 160, 340 + (i // 2) * 46, 145, 38, "box", 4))
        o.append(txt(924 + (i % 2) * 160, 364 + (i // 2) * 46, nm, "lbl", "middle"))
    o.append('<path class="sig" d="M720,280 C780,280 790,330 830,330"/>')
    o.append(txt(742, 300, "H6~H9 · 26AWG 300mm", "tiny"))
    o.append('<path class="pwr2" d="M290,589 C600,589 700,420 830,420"/>')
    o.append(txt(560, 560, "H5 · 서보 전원은 UBEC 에서 직접 (Teensy 3V3 금지)", "tiny"))

    o.append(rect(830, 500, 330, 110, "elec", 6))
    o.append(txt(995, 524, "FS-iA6B 수신기 (PWM 5채널)", "h", "middle"))
    o.append(txt(995, 543, "CH1 스로틀 · CH2 롤 · CH3 피치 · CH4 요 · CH5 킬", "tiny", "middle"))
    o.append(txt(995, 560, "전원 5V(UBEC) · 안테나 2개 서로 90°", "tiny", "middle"))
    o.append(txt(995, 580, "iBUS 아님 — 스톡 펌웨어가 PWM 을 읽는다", "tiny", "middle"))
    o.append(txt(995, 598, "안테나는 전원선에서 30mm 이상 이격", "tiny", "middle"))

    o.append(rect(560, 660, 300, 70, "hot", 6))
    o.append(txt(710, 683, "레벨시프터 4ch ×2 (BSS138)", "lblb", "middle"))
    o.append(txt(710, 700, "수신기 5V 신호 → Teensy 3.3V", "tiny", "middle"))
    o.append(txt(710, 718, "직결 금지 — Teensy 4.0 은 5V 비관용", "warn", "middle"))
    o.append('<path class="sig" d="M830,545 C900,600 800,660 860,690"/>')
    o.append('<path class="sig" d="M560,690 C480,690 470,360 420,330"/>')

    # GND 버스
    o.append('<path class="gnd" d="M165,618 L165,790 L1100,790 L1100,610"/>')
    o.append('<path class="gnd" d="M570,450 L570,790"/>')
    o.append('<path class="gnd" d="M165,506 L165,560"/>')
    o.append(txt(600, 806, "공통 GND (별 접지) — 배터리(−)=ESC(−)=UBEC(−)=만능기판 GND 버스=Teensy GND=수신기 GND", "lbl"))

    # 노트
    o.append(rect(28, 828, 1184, 56, "note", 6))
    o.append(txt(44, 848, "전원 인가 순서 · 필독", "lblb"))
    o.append(txt(44, 866, "① USB 로 Teensy 만 → ② UBEC·수신기(킬 스위치 동작 확인) → ③ 마지막에 배터리 메인. "
                          "끌 때는 역순.  |  Teensy VIN 에 UBEC 5V 를 넣으려면 먼저 뒷면 VUSB 패드를 잘라야 한다(§3.4).", "lbl"))

    o.append("</svg>")
    return "\n".join(o)


# ====================================================== 2. 기계 통합도
def mechanical():
    W, H = 1280, 900
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">' % (W, H),
         "<style>%s</style>" % CSS, rect(0, 0, W, H, "bg", 0)]
    o.append(txt(28, 34, "COSMOS 호퍼 — 기계 통합도 (전자부품이 프린트 구조 어디에 붙나, rev C.1)", "title"))
    o.append(txt(28, 54, "왼쪽 = 입면(YZ 평면, +Y 오른쪽) / 오른쪽 = 평면(위에서 본 것). "
                         "01-avionics-integration-final.md §7 · cad/hopper_params.scad rev C.1 과 동일 치수.", "sub"))

    # ---------------- 입면도 -------------------------------------------------
    S = 1.50
    CX, CZ = 375.0, 400.0

    def X(y_mm):
        return CX + y_mm * S

    def Z(z_mm):
        return CZ - z_mm * S

    o.append(txt(375, 92, "입면 (elevation)", "h", "middle"))

    # 흡기 통로 / 배기 제트
    o.append(rect(X(-39), Z(TOP_PLATE_BOT_Z), 78 * S,
                  (TOP_PLATE_BOT_Z - G["edf_body_len"]) * S, "flow", 0))
    o.append(txt(X(0), Z(140), "흡기 통로", "tiny", "middle"))
    o.append(txt(X(0), Z(130), "(부품·배선 금지)", "tiny", "middle"))
    o.append(rect(X(-36), Z(0), 72 * S, (0 - FOOT_Z + 10) * S, "jet", 0))
    o.append(txt(X(0), Z(-115), "배기 제트", "tiny", "middle"))
    o.append('<path class="axis" d="M%.1f,%.1f L%.1f,%.1f"/>' % (X(0), Z(195), X(0), Z(-150)))

    # 구조
    o.append(rect(X(-63), Z(TOP_PLATE_TOP_Z), 126 * S, G["top_plate_t"] * S, "prt"))
    for sgn in (-1, 1):
        o.append(rect(X(sgn * COL_XY) - 2, Z(TOP_PLATE_BOT_Z), 4,
                      (TOP_PLATE_BOT_Z - RING_TOP_Z) * S, "buy", 1))
    o.append(rect(X(-36), Z(G["edf_body_len"]), 72 * S, G["edf_body_len"] * S, "buy"))
    o.append(txt(X(0), Z(46), "64mm EDF", "lblb", "middle"))
    o.append(rect(X(-40), Z(G["edf_clamp_z"] + 6), 80 * S, 12 * S, "hot"))

    # 장비 선반
    sz = G["shelf_top_z"]
    o.append(rect(X(G["shelf_r_inner"]), Z(sz), G["batt_shelf_w"] * S, G["shelf_t"] * S, "prt2"))
    o.append(rect(X(G["shelf_r_inner"] + 6), Z(sz + G["batt_h"]), G["batt_w"] * S,
                  G["batt_h"] * S, "hot"))
    o.append(rect(X(-G["shelf_r_inner"] - G["avio_shelf_w"]), Z(sz), G["avio_shelf_w"] * S,
                  G["shelf_t"] * S, "prt2"))
    o.append(rect(X(-G["shelf_r_inner"] - 57), Z(sz + 13), 50 * S, 2 * S, "elec"))
    o.append(rect(X(-G["shelf_r_inner"] - 50), Z(sz + 21), 36 * S, 6 * S, "prt2"))
    o.append(rect(X(-58), Z(145), 6 * S, 35 * S, "hot"))

    # 베인링 · 베인 · 서보
    o.append(rect(X(-48), Z(RING_TOP_Z), 96 * S, G["vane_ring_h"] * S, "prt"))
    o.append(rect(X(-41), Z(VANE_PIVOT_Z + G["vane_chord"] / 2), 82 * S, G["vane_chord"] * S, "prt2"))
    for sgn in (-1, 1):
        x0 = X(48) if sgn > 0 else X(-48 - 27)
        o.append(rect(x0, Z(VANE_PIVOT_Z + 11), 27 * S, 22 * S, "box"))

    # 다리 · 발
    for sgn in (-1, 1):
        o.append('<path class="buy" d="M%.1f,%.1f L%.1f,%.1f" stroke-width="4"/>'
                 % (X(sgn * 48), Z(RING_BOT_Z), X(sgn * 180), Z(FOOT_Z)))
        o.append(rect(X(sgn * 180) - 9, Z(FOOT_Z), 18, 6, "hot", 2))

    # ---- 콜아웃(지시선) — 왼쪽 열 = −Y 쪽, 오른쪽 열 = +Y 쪽
    def callout(col_x, ty, tx, tz, lines, side):
        anchor = "end" if side < 0 else "start"
        o.append('<path class="dim" d="M%.1f,%.1f L%.1f,%.1f L%.1f,%.1f"/>'
                 % (col_x + (6 * side), ty - 4, col_x + 26 * side, ty - 4, X(tx), Z(tz)))
        for k, ln in enumerate(lines):
            o.append(txt(col_x, ty + k * 13, ln, "lblb" if k == 0 else "tiny", anchor))

    LC, RC = 196.0, 596.0
    callout(LC, 150, -72, sz, ["아비오닉스 선반 (−Y, 프린트)",
                               "만능기판 70×50 + Teensy + IMU + 수신기",
                               "M3 열융착 인서트 4개 · 53.34×38.10",
                               "UBEC 은 선반 하면에 타이 2개"], -1)
    callout(LC, 236, -58, 128, ["ESC 브래킷 (270°)",
                                "흡기로 빨려드는 공기가 지나 냉각됨"], -1)
    callout(LC, 300, -COL_XY, 60, ["Ø6 CF 기둥 ×4",
                                   "45°·135°·225°·315°"], -1)
    callout(LC, 372, -48, VANE_PIVOT_Z, ["베인링 (프린트)",
                                         "서보 보스 4 · 스파 부싱 4 · 하드스톱 슬롯 4"], -1)
    callout(LC, 470, -120, -100, ["착륙다리 ×4 (Ø6 CF)",
                                  "기둥과 같은 방위 = 서보와 45° 엇갈림"], -1)

    callout(RC, 140, 50, TOP_PLATE_TOP_Z, ["상판 (프린트)", "Ø78 흡기홀"], 1)
    callout(RC, 196, 65, sz + 12, ["배터리 선반 (+Y, 프린트)",
                                   "4S 1300mAh 팩 · 벨크로 2줄",
                                   "스트랩 슬롯이 길어 ±8mm 반경 트림"], 1)
    callout(RC, 288, 38, G["edf_clamp_z"], ["EDF 클램프 (프린트)",
                                            "볼트 플랜지 없는 EDF용 분할 클램프"], 1)
    callout(RC, 372, 60, VANE_PIVOT_Z, ["MG90S ×4 — 베인 직결",
                                        "스플라인 = 베인 피벗축(반경 방향)"], 1)
    callout(RC, 452, 20, -80, ["배기 제트 (하향)",
                               "이 원뿔 안엔 배선·다리 뿌리 금지"], 1)

    # z 기준표 (눈금자 대신 표로 — 콜아웃과 겹치지 않게)
    o.append(rect(40, 548, 230, 190, "note", 6))
    o.append(txt(52, 570, "z 기준 (배기면 = 0)", "lblb"))
    for k, (z_mm, lab) in enumerate([(TOP_PLATE_TOP_Z, "상판 윗면"), (TOP_PLATE_BOT_Z, "상판 아랫면"),
                                     (sz, "장비 선반 상면"), (G["edf_body_len"], "EDF 흡입구 립"),
                                     (G["edf_clamp_z"], "EDF 클램프"), (0, "배기면 (기준)"),
                                     (VANE_PIVOT_Z, "베인 피벗축"), (RING_BOT_Z, "베인링 하단"),
                                     (FOOT_Z, "발 바닥")]):
        o.append(txt(52, 590 + k * 15, "%+d mm" % z_mm, "tiny"))
        o.append(txt(120, 590 + k * 15, lab, "tiny"))
    o.append(txt(52, 728, "CG 목표 +60~75 → 베인까지 모멘트암 ≈ 100mm", "lblb"))

    # ---------------- 평면도 -------------------------------------------------
    S2 = 1.10
    PX, PY = 930.0, 430.0

    def px(x_mm, y_mm):
        return (PX + x_mm * S2, PY - y_mm * S2)

    o.append(txt(PX, 92, "평면 (plan, 위에서 본 것)", "h", "middle"))
    o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" class="jet"/>' % (PX, PY, 36 * S2))
    o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="#b9c4cb" stroke-dasharray="5 4"/>'
             % (PX, PY, 39 * S2))
    o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="#41525c" stroke-width="1.6"/>'
             % (PX, PY, 48 * S2))
    o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="#41525c" stroke-width="1"/>'
             % (PX, PY, 38 * S2))

    names = {0: "0° FWD · S1", 90: "90° LEFT · S2", 180: "180° AFT · S3", 270: "270° RIGHT · S4"}
    for az in (0, 90, 180, 270):
        a = math.radians(az)
        x0, y0 = px(4 * math.cos(a), 4 * math.sin(a))
        x1, y1 = px(41 * math.cos(a), 41 * math.sin(a))
        o.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="#1f6feb" stroke-width="4"/>' % (x0, y0, x1, y1))
        sx, sy = px(62 * math.cos(a), 62 * math.sin(a))
        o.append('<g transform="rotate(%g %.1f %.1f)">%s</g>'
                 % (-az, sx, sy, rect(sx - 15, sy - 9, 30, 18, "box", 2)))
        lx, ly = px(104 * math.cos(a), 104 * math.sin(a))
        o.append(txt(lx, ly + 3, names[az], "tiny", "middle"))

    for az in (45, 135, 225, 315):
        a = math.radians(az)
        cx_, cy_ = px(48 * math.cos(a), 48 * math.sin(a))
        fx, fy = px(180 * math.cos(a), 180 * math.sin(a))
        o.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="#a8842c" stroke-width="2.5" '
                 'stroke-dasharray="6 4" fill="none"/>' % (cx_, cy_, fx, fy))
        o.append('<circle cx="%.1f" cy="%.1f" r="5" class="buy"/>' % (cx_, cy_))
        o.append('<circle cx="%.1f" cy="%.1f" r="7" class="hot"/>' % (fx, fy))
    tx_, ty_ = px(150, 150)
    o.append(txt(tx_, ty_, "기둥·다리 45° 계열", "tiny", "middle"))

    bx, by = px(-G["batt_shelf_l"] / 2, G["shelf_r_inner"] + G["batt_shelf_w"])
    o.append(rect(bx, by, G["batt_shelf_l"] * S2, G["batt_shelf_w"] * S2, "prt2"))
    o.append(txt(PX, by + 28, "배터리 선반 (%g×%g, 접선x반경)" % (G["batt_shelf_l"], G["batt_shelf_w"]),
                 "tiny", "middle"))
    ax, ay = px(-G["avio_shelf_l"] / 2, -G["shelf_r_inner"])
    o.append(rect(ax, ay, G["avio_shelf_l"] * S2, G["avio_shelf_w"] * S2, "prt2"))
    o.append(txt(PX, ay + 26, "아비오닉스 선반 (84×60)", "tiny", "middle"))
    o.append(txt(PX, ay + 40, "만능기판 70×50", "tiny", "middle"))

    for az, lab, col in ((225, "서보선 2다발", "#1f6feb"), (315, "서보선 2다발", "#1f6feb"),
                         (270, "3상 · 메인전원", "#c0392b")):
        a = math.radians(az)
        x0, y0 = px(50 * math.cos(a), 50 * math.sin(a))
        x1, y1 = px(128 * math.cos(a), 128 * math.sin(a))
        o.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="%s" stroke-width="2" fill="none"/>'
                 % (x0, y0, x1, y1, col))
        o.append(txt(x1, y1 + (14 if math.sin(a) < 0 else -8), lab, "tiny", "middle", fill=col))

    lx0, ly0 = 1130, 130
    o.append(txt(lx0, ly0, "범례", "lblb"))
    for i, (cls, nm) in enumerate([("prt", "프린트 파트"), ("prt2", "프린트(전자 장착)"),
                                   ("buy", "구매품(CF관·EDF)"), ("hot", "전자·고전류"),
                                   ("flow", "흡기 통로"), ("jet", "배기 제트")]):
        o.append(rect(lx0, ly0 + 10 + i * 20, 16, 12, cls, 2))
        o.append(txt(lx0 + 22, ly0 + 20 + i * 20, nm, "tiny"))

    o.append(rect(28, 790, 1224, 88, "note", 6))
    o.append(txt(44, 812, "이 도면이 강제하는 규칙 4가지", "lblb"))
    o.append(txt(44, 832, "① 반경 39mm 안쪽(흡기) · 36mm 안쪽(배기)에는 배선·부품·케이블타이 그 무엇도 두지 않는다.", "lbl"))
    o.append(txt(44, 850, "② 베인·서보 = 0/90/180/270, 기둥·다리·선반 = 45/135/225/315. 방위를 섞으면 다리 뿌리와 서보가 같은 자리를 차지한다.", "lbl"))
    o.append(txt(44, 868, "③ 고전류(3상·메인)는 270° 쪽, 신호선은 225°/315° 쪽으로 분리한다.   "
                          "④ 선반 높이는 CG 트림 수단이다 — 클램프를 풀어 5mm씩 올린다.", "lbl"))

    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    for name, data in (("system-wiring-final.svg", system_wiring()),
                       ("mechanical-integration.svg", mechanical())):
        path = os.path.normpath(os.path.join(OUT_DIR, name))
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        print("wrote", path, len(data), "bytes")

"""
외주 발주용 STL을 한 번에 만들고 검사한다 (#59).

hopper_params.scad의 변수·모듈 정의부(`// ---------- 조립 ----------` 앞)를 임시 파일로 복사하고,
부품 호출 한 줄씩 붙여 OpenSCAD로 STL을 뽑는다. 원본 .scad는 고치지 않는다.
다 뽑은 뒤 STL마다 크기(mm), 부피(cm3), 열린 모서리 수를 출력한다. 열린 모서리가 0이 아니면 실패한다.

실행 (레포 루트에서):
  python cad/tools/export_print_parts.py                 # cad/print_parts/ 에 저장
  python cad/tools/export_print_parts.py --out 폴더       # 다른 폴더에 저장 (예: cad/print-orders/20261017)
  python cad/tools/export_print_parts.py --only vane_ring

OpenSCAD 위치: 환경변수 OPENSCAD, PATH의 openscad, Windows 기본 설치 경로 순서로 찾는다.
표준 라이브러리만 쓴다.
"""
import argparse
import collections
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAD = ROOT / "cad" / "hopper_params.scad"
MARKER = "// ---------- 조립 ----------"

# 파일 이름 -> 부품 호출. 기본 render_mode "print" 분기와 같은 호출이다.
COUPLERS = ("for (i=[0:n_vanes-1]) rotate([0,0,i*360/n_vanes + az_vane]) "
            "translate([servo_mount_r + 1.5, 0, vane_pivot_z]) vane_coupler({});")
PARTS = {
    "top_plate": "translate([0,0,top_plate_bot_z]) top_plate();",
    "vane_ring": "vane_ring();",
    "vanes_x4": "vanes();",
    "edf_clamp": "edf_clamp();",
    "battery_shelf": "rotate([0,0,90]) equip_shelf_battery();",
    "avionics_shelf": "rotate([0,0,270]) equip_shelf_avionics();",
    "esc_bracket": "rotate([0,0,270]) esc_bracket();",
    "vane_couplers_x4": COUPLERS.format("0"),
    # 혼 실측 전 발주용: 슬롯 두께·폭 +0.4 mm. 맞는 세트를 쓴다.
    "vane_couplers_x4_slack0.4": COUPLERS.format("0.4"),
    "foot_pads_x4": "foot_pads();",
}


def find_openscad():
    cands = [os.environ.get("OPENSCAD"), shutil.which("openscad")]
    if os.name == "nt":
        cands += [r"C:\Program Files\OpenSCAD\openscad.exe",
                  str(Path.home() / "Desktop" / "openscad.exe")]
    for c in cands:
        if c and Path(c).is_file():
            # 설치가 깨진 경우가 있었다(9/18, Program Files). 실제로 실행되는 것만 쓴다.
            r = subprocess.run([c, "--version"], capture_output=True)
            if r.returncode == 0:
                return c
    sys.exit("OpenSCAD를 찾지 못했다. 환경변수 OPENSCAD에 openscad.exe 경로를 넣는다.")


def load_stl(path):
    b = path.read_bytes()
    if b[:5] == b"solid" and b"facet" in b[:400]:
        tris, cur = [], []
        for line in b.decode(errors="replace").splitlines():
            t = line.split()
            if t and t[0] == "vertex":
                cur.append(tuple(float(x) for x in t[1:4]))
                if len(cur) == 3:
                    tris.append(cur)
                    cur = []
        return tris
    n = struct.unpack("<I", b[80:84])[0]
    return [[struct.unpack("<3f", b[84 + i * 50 + 12 + j * 12:84 + i * 50 + 24 + j * 12]) for j in range(3)]
            for i in range(n)]


def check_stl(path):
    tris = load_stl(path)
    vol = 0.0
    edges = collections.Counter()
    for a, b, c in tris:
        vol += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6
        for u, v in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted((u, v)))] += 1
    open_edges = sum(1 for k in edges.values() if k != 2)
    pts = [p for t in tris for p in t]
    if not pts:
        return None, 0.0, 0
    size = [max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3)]
    return size, abs(vol) / 1000, open_edges


def main():
    ap = argparse.ArgumentParser(description="발주용 STL 일괄 내보내기와 검사")
    ap.add_argument("--out", default=str(ROOT / "cad" / "print_parts"))
    ap.add_argument("--only", nargs="*", choices=sorted(PARTS))
    a = ap.parse_args()

    exe = find_openscad()
    src = SCAD.read_text(encoding="utf-8")
    if MARKER not in src:
        sys.exit(f"{SCAD.name}에서 '{MARKER}' 줄을 찾지 못했다.")
    head = src[:src.index(MARKER)]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    bad = 0
    print(f"| 부품 | 크기 (mm) | 부피 (cm3) | 열린 모서리 |")
    print(f"|---|---|---|---|")
    with tempfile.TemporaryDirectory() as tmp:
        for name in (a.only or PARTS):
            scad = Path(tmp) / f"{name}.scad"
            scad.write_text(head + "\n" + PARTS[name] + "\n", encoding="utf-8")
            stl = out / f"{name}.stl"
            if stl.exists():
                stl.unlink()   # 실패했을 때 옛 STL이 발주 폴더에 남지 않게
            r = subprocess.run([exe, "--render", "-o", str(stl), str(scad)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode != 0 or not stl.exists():
                print(f"| {name} | 렌더 실패 (exit {r.returncode}) | | |")
                sys.stderr.write(r.stderr[-2000:])
                bad += 1
                continue
            # OpenSCAD는 없는 모듈·변수를 경고만 하고 exit 0으로 끝낼 수 있다. 경고는 항상 보여 준다.
            warns = [l for l in r.stderr.splitlines() if "WARNING" in l or "ERROR" in l]
            for w in warns:
                print(f"  {name}: {w}", file=sys.stderr)
            size, vol, open_edges = check_stl(stl)
            if size is None:
                print(f"| {name} | 빈 STL (삼각형 0개) | | |")
                bad += 1
                continue
            bad += open_edges != 0 or bool(warns)
            print(f"| {name} | {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} | {vol:.1f} | {open_edges} |")
    print()
    print("전부 통과" if bad == 0 else f"문제 {bad}건")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

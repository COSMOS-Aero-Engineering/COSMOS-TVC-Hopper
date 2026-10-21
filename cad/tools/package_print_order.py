"""Split validated master STLs into exactly 31 individual order files (#224).

Each output STL contains one physical part and is printed once. Keep the
master x4 STLs outside the ZIP to prevent accidental duplicate quantities.
"""
import argparse
import collections
import hashlib
import json
import struct
import zipfile
from pathlib import Path

try:
    from .export_print_parts import PARTS, SCAD, check_stl, load_stl
except ImportError:
    from export_print_parts import PARTS, SCAD, check_stl, load_stl

# Number of connected pieces in one master; number of times that master is used.
ORDER = {
    "vane_ring": (1, 1), "top_plate": (1, 1), "edf_clamp": (2, 1),
    "battery_shelf": (1, 1), "avionics_shelf": (1, 1), "esc_bracket": (1, 1),
    "vanes_x4": (4, 2), "vane_couplers_x4": (4, 2),
    "vane_couplers_x4_slack0.4": (4, 1), "foot_pads_x4": (4, 1),
}


def components(triangles):
    """Connected components by shared vertex, preserving all input triangles."""
    owners, neighbors = {}, collections.defaultdict(set)
    for index, triangle in enumerate(triangles):
        for point in triangle:
            key = tuple(point)
            if key in owners:
                other = owners[key]
                neighbors[index].add(other)
                neighbors[other].add(index)
            else:
                owners[key] = index
    remaining = set(range(len(triangles)))
    result = []
    while remaining:
        seed = min(remaining)
        remaining.remove(seed)
        pending, group = [seed], []
        while pending:
            index = pending.pop()
            group.append(triangles[index])
            new = neighbors[index] & remaining
            remaining.difference_update(new)
            pending.extend(sorted(new))
        result.append(group)
    return result


def write_stl(path, triangles):
    """Only translate: center XY and put the lowest vertex at Z=0, in mm."""
    points = [p for t in triangles for p in t]
    lo = [min(p[i] for p in points) for i in range(3)]
    hi = [max(p[i] for p in points) for i in range(3)]
    offset = [(lo[0] + hi[0])/2, (lo[1] + hi[1])/2, lo[2]]
    data = bytearray(b"COSMOS individual part; mm; print once".ljust(80, b" "))
    data.extend(struct.pack("<I", len(triangles)))
    for triangle in triangles:
        xyz = [p[i] - offset[i] for p in triangle for i in range(3)]
        data.extend(struct.pack("<12fH", 0, 0, 0, *xyz, 0))
    path.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--masters", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="Fresh order directory")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    output = args.out / "PRINT_ONCE_31_FILES"
    output.mkdir()
    records = []
    for master, (expected, repetitions) in ORDER.items():
        source = args.masters / (master + ".stl")
        size, volume, edges = check_stl(source)
        if size is None or volume <= 0 or edges:
            raise SystemExit(f"Invalid source {master}: {size}, {volume}, {edges}")
        groups = components(load_stl(source))
        if len(groups) != expected:
            raise SystemExit(f"{master}: expected {expected} physical pieces, got {len(groups)}")
        for repetition in range(repetitions):
            for index, triangles in enumerate(groups):
                number = len(records) + 1
                individual_name = master.replace("_x4", "")
                path = output / f"{number:02d}_{individual_name}_{repetition+1}_{index+1}.stl"
                write_stl(path, triangles)
                dims, part_volume, open_edges = check_stl(path)
                if open_edges or part_volume <= 0 or len(components(load_stl(path))) != 1:
                    raise SystemExit(f"Invalid individual output: {path.name}")
                records.append(dict(file=path.name, quantity=1, master=master,
                                    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                                    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                    size_mm=dims, volume_cm3=part_volume, open_edges=open_edges))
    assert len(records) == 31 and set(ORDER) == set(PARTS)
    manifest = dict(source_scad_sha256=hashlib.sha256(SCAD.read_bytes()).hexdigest(),
                    total_physical_parts=31, quantity_per_file=1, files=records)
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    text = """COSMOS 3D打印订单 / 발주서 — 2026-10-21 R2

请停止使用旧ZIP和旧排版。本ZIP完整替换旧版，不要叠加打印。
只打印 PRINT_ONCE_31_FILES 文件夹内的31个STL，每个文件打印1件，共31件。
所有STL已拆分为独立零件，已包含备件。不要再按x4文件名乘4。
每个STL实际只有一个独立零件。

数量：叶片环1、顶板1、EDF夹具半件2、电池托架1、电子托架1、ESC支架1、
叶片8、标准连接件8、加宽0.4mm连接件4、脚垫4。总计31件。
装机用19件；其余12件是备件及另一种配合间隙的连接件。

材料PETG；单位mm；比例100%；喷嘴0.4mm；层高0.2mm；
外壁4圈；顶/底各6层；40% gyroid填充。
托架套筒及其根部请设置局部100%填充。保持孔的尺寸，不要自动缩放。
本次已修改两种托架：去除内侧扎带槽，外侧扎带槽移位，保留完整套筒。
叶片环包含之前的舵机安装面修正。两种托架和叶片环请使用本ZIP的文件。
请按设备与受力方向选择摆放和支撑，清除孔槽内支撑；不要把零件焊接或合并。
这些是机械原型件，不代表已完成装机或强度试验。

한국어 확인:
이 ZIP 전체로 기존 발주본을 대체한다. 예전 파일과 합산하지 않는다.
PRINT_ONCE_31_FILES 안의 STL 31개를 각각 1개씩 출력한다.
본체용 19개 + 베인 예비4 + 기본 커플러 예비4 + 여유 커플러4 = 31개.
발 범퍼도 이번 주문에서는 PETG다. 기존 질량표의 EVA 가정과 다르므로 입고 후 실측한다.
서포트와 방향은 업체가 장비에 맞춰 정한다. 동봉 G-code는 없으며 STL로 슬라이싱한다.
"""
    (args.out / "ORDER_KO_ZH.txt").write_text(text, encoding="utf-8-sig")
    archive = args.out.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(args.out.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(args.out))
    print(f"Validated {len(records)} individual closed parts; each quantity=1")
    print(archive)


if __name__ == "__main__":
    main()

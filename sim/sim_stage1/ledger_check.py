"""params-ledger.md의 대장 표가 params.yaml의 잎 키를 모두 담는지 검사한다(#267).

    python ledger_check.py      `python tasks.py check`가 같이 돌린다(작업 이름 ledger)

잎 키는 값이 매핑이 아닌 키다. 점으로 잇는다(예: `servo.tau`). 목록 값(`rotor_inertia_range`)도
잎 키다. 대장 쪽은 `## 대장` 절 안의 표 행에서 첫 열의 `` `키` ``를 읽는다.

출력은 `파일:줄: 내용` 형식이다. 편집기와 CI 로그 도구가 이 형식으로 해당 줄을 연다.
- params.yaml에는 있고 대장에 없는 키: params.yaml의 그 키 줄
- 대장에만 있는 키, 대장에 두 번 있는 키, 첫 열을 키로 읽지 못한 행: 대장의 그 행 줄

줄 번호는 PyYAML의 compose()가 노드마다 남기는 start_mark에서 얻는다. safe_load()는 줄 번호를
남기지 않는다. 출처 상태나 이슈 번호가 맞는지는 보지 않는다(#267 제외 항목, 사람이 리뷰한다).
"""
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARAMS = HERE / "params.yaml"
LEDGER = HERE / "params-ledger.md"
# 키를 읽는 절의 제목. 이 절 다음의 `## ` 제목에서 멈춘다.
LEDGER_SECTION = "## 대장"
# 표 행의 첫 열이 백틱 하나로 감싼 키인 형식.
KEY_CELL_RE = re.compile(r"^`([^`]+)`$")
# 표 머리 행의 첫 열과 구분 행.
HEADER_CELL = "키"
SEPARATOR_RE = re.compile(r"^\|[\s:|-]+\|$")


def yaml_leaf_keys(text):
    """params.yaml 본문에서 잎 키를 (점 이름, 줄 번호) 목록으로 돌려준다. 줄 번호는 1부터 센다.

    최상위가 매핑이 아니면 ValueError를 낸다.
    """
    root = yaml.compose(text, Loader=yaml.SafeLoader)
    if not isinstance(root, yaml.MappingNode):
        raise ValueError("params.yaml의 최상위가 매핑이 아니다.")
    keys = []

    def walk(node, prefix):
        for key_node, value_node in node.value:
            name = f"{prefix}{key_node.value}"
            if isinstance(value_node, yaml.MappingNode):
                walk(value_node, name + ".")
            else:
                keys.append((name, key_node.start_mark.line + 1))

    walk(root, "")
    return keys


def ledger_keys(text):
    """대장 본문의 `## 대장` 절에서 표 행의 키를 읽는다.

    (키 목록, 읽지 못한 행 목록)을 돌려준다. 키 목록은 (키, 줄 번호), 읽지 못한 행 목록은
    (줄 번호, 첫 열 글자)다. 머리 행과 구분 행은 건너뛴다. 절이 없으면 ValueError를 낸다.
    """
    keys, bad = [], []
    inside = found = False
    for lineno, line in enumerate(text.split("\n"), start=1):
        stripped = line.strip()
        if stripped.startswith("## "):
            inside = stripped == LEDGER_SECTION
            found = found or inside
            continue
        if not inside or not stripped.startswith("|") or SEPARATOR_RE.match(stripped):
            continue
        first = stripped.strip("|").split("|", 1)[0].strip()
        if first == HEADER_CELL:
            continue
        m = KEY_CELL_RE.match(first)
        if m:
            keys.append((m.group(1), lineno))
        else:
            bad.append((lineno, first))
    if not found:
        raise ValueError(f"대장에서 '{LEDGER_SECTION}' 절을 찾지 못했다.")
    return keys, bad


def compare(yaml_keys, table_keys, bad_rows, params_rel, ledger_rel):
    """두 키 목록을 비교해서 출력할 줄 목록을 돌려준다. 빈 목록이면 두 곳이 같다."""
    out = []
    in_table = {k for k, _ in table_keys}
    in_yaml = {k for k, _ in yaml_keys}
    for key, lineno in yaml_keys:
        if key not in in_table:
            out.append(f"{params_rel}:{lineno}: 대장에 없는 키 '{key}'")
    seen = set()
    for key, lineno in table_keys:
        if key not in in_yaml:
            out.append(f"{ledger_rel}:{lineno}: params.yaml에 없는 키 '{key}'")
        elif key in seen:
            out.append(f"{ledger_rel}:{lineno}: 대장에 두 번 있는 키 '{key}'")
        seen.add(key)
    for lineno, cell in bad_rows:
        out.append(f"{ledger_rel}:{lineno}: 첫 열을 키로 읽지 못했다 '{cell}'. 키는 `이름`처럼 백틱으로 감싼다")
    return out


def main():
    params_rel = PARAMS.relative_to(ROOT).as_posix()
    ledger_rel = LEDGER.relative_to(ROOT).as_posix()
    yaml_keys = yaml_leaf_keys(PARAMS.read_text(encoding="utf-8"))
    table_keys, bad = ledger_keys(LEDGER.read_text(encoding="utf-8"))
    if not yaml_keys or not table_keys:
        # 읽는 코드가 고장 나서 양쪽 다 0건이면 늘 통과한다. 그렇게 두지 않는다.
        print(f"키를 읽지 못했다: params.yaml {len(yaml_keys)}개, 대장 {len(table_keys)}개", file=sys.stderr)
        return 1
    problems = compare(yaml_keys, table_keys, bad, params_rel, ledger_rel)
    for line in problems:
        print(line, flush=True)
    if problems:
        print(f"\n대장과 params.yaml의 키가 {len(problems)}곳에서 다르다(#267).\n"
              f"     params.yaml에 키를 더하거나 지웠으면 {ledger_rel}의 표에도 행을 더하거나 지운다.",
              file=sys.stderr)
        return 1
    print(f"대장이 params.yaml의 잎 키 {len(yaml_keys)}개를 모두 담는다")
    return 0


if __name__ == "__main__":
    sys.exit(main())

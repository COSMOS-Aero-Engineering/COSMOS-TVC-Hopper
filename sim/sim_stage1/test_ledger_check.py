"""ledger_check.py(#267)의 단위 검사. 검사기가 걸러야 할 차이를 실제로 거르는지 본다.

    python -m unittest test_ledger_check    `python tasks.py check`가 같이 돌린다(작업 이름 ledger)

검사기가 고장 나면 키를 0건 읽거나 차이를 못 찾고 조용히 통과한다. 그래서 걸려야 하는 예와
걸리면 안 되는 예를 여기에 둔다. PyYAML이 필요해서 uv 환경(.venv)에서 돈다.
"""
import unittest

import ledger_check as lc

YAML = """\
# 주석
mass: 0.735   # kg
servo:
  enabled: false
  tau: 0.05
domain_rand:
  rotor_inertia_range: [5.0e-6, 3.5e-5]
  nested:
    deep: 1
"""

LEDGER = """\
# 제목

## 출처 상태

| 상태 | 뜻 |
|---|---|
| 실측 | 잰 값 |

## 대장

### 질량

| 키 | 값 |
|---|---|
| `mass` | 0.735 |
| `servo.enabled` | false |
| `servo.tau` | 0.05 |
| `domain_rand.rotor_inertia_range` | [..] |
| `domain_rand.nested.deep` | 1 |

## 실측 결과가 들어오면

| `not_a_key` | 이 절은 대장이 아니다 |
"""


def run(yaml_text, ledger_text):
    keys, bad = lc.ledger_keys(ledger_text)
    return lc.compare(lc.yaml_leaf_keys(yaml_text), keys, bad, "p.yaml", "l.md")


class LeafKeys(unittest.TestCase):
    def test_leaf_keys_and_lines(self):
        self.assertEqual(lc.yaml_leaf_keys(YAML), [
            ("mass", 2), ("servo.enabled", 4), ("servo.tau", 5),
            ("domain_rand.rotor_inertia_range", 7), ("domain_rand.nested.deep", 9)])

    def test_top_level_not_mapping(self):
        with self.assertRaises(ValueError):
            lc.yaml_leaf_keys("- a\n- b\n")


class LedgerKeys(unittest.TestCase):
    def test_reads_only_ledger_section(self):
        keys, bad = lc.ledger_keys(LEDGER)
        self.assertEqual([k for k, _ in keys], [
            "mass", "servo.enabled", "servo.tau", "domain_rand.rotor_inertia_range",
            "domain_rand.nested.deep"])
        self.assertEqual(keys[0][1], 15)
        self.assertEqual(bad, [])

    def test_missing_section(self):
        with self.assertRaises(ValueError):
            lc.ledger_keys("## 다른 절\n| `mass` | 1 |\n")

    def test_row_without_backticks(self):
        _, bad = lc.ledger_keys(LEDGER.replace("| `servo.tau` |", "| servo.tau |"))
        self.assertEqual(bad, [(17, "servo.tau")])


class Compare(unittest.TestCase):
    def test_same_keys_pass(self):
        self.assertEqual(run(YAML, LEDGER), [])

    def test_key_added_to_yaml(self):
        # 판정 기준: params.yaml에 키를 하나 더하면 그 키 이름을 출력한다.
        out = run(YAML.replace("  tau: 0.05\n", "  tau: 0.05\n  new_key: 1\n"), LEDGER)
        self.assertEqual(out, ["p.yaml:6: 대장에 없는 키 'servo.new_key'"])

    def test_key_only_in_ledger(self):
        out = run(YAML.replace("mass: 0.735   # kg\n", ""), LEDGER)
        self.assertEqual(out, ["l.md:15: params.yaml에 없는 키 'mass'"])

    def test_duplicate_row(self):
        ledger = LEDGER.replace("| `mass` | 0.735 |\n", "| `mass` | 0.735 |\n| `mass` | 0.735 |\n")
        self.assertEqual(run(YAML, ledger), ["l.md:16: 대장에 두 번 있는 키 'mass'"])

    def test_bad_row_reported(self):
        out = run(YAML, LEDGER.replace("| `servo.tau` |", "| servo.tau |"))
        self.assertIn("p.yaml:5: 대장에 없는 키 'servo.tau'", out)
        self.assertTrue(any(line.startswith("l.md:17: 첫 열을 키로 읽지 못했다") for line in out))


if __name__ == "__main__":
    unittest.main()

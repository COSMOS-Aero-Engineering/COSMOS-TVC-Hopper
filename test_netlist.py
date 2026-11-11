"""Regression checks for the exported artifact checker, without KiCad installed."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "kicad" / "_tools"))
from check_netlist import check

ARTIFACT = ROOT / "kicad/reports/2026-10-19/netlist.xml"
ERC_ARTIFACT = ROOT / "kicad/reports/2026-10-19/erc.json"


class ExportedPins(unittest.TestCase):
    def run_artifact(self, tree):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            p = Path(tmp) / "net.xml"
            tree.write(p)
            return check(p)

    def test_verified_export_passes(self):
        self.assertTrue(self.run_artifact(ET.parse(ARTIFACT)))

    def test_verified_export_has_portable_source_path(self):
        self.assertEqual(ET.parse(ARTIFACT).findtext("./design/source"),
                         "cosmos-avionics.kicad_sch")

    def test_power_label_merge_fails(self):
        tree = ET.parse(ARTIFACT)
        for net in tree.findall("./nets/net"):
            if net.get("name") == "/+BATT":
                net.set("name", "/+5V")
        self.assertFalse(self.run_artifact(tree))

    def test_swapped_battery_polarity_fails(self):
        tree = ET.parse(ARTIFACT)
        for node in tree.findall("./nets/net/node"):
            if node.get("ref") == "BT1":
                node.set("pin", "2" if node.get("pin") == "1" else "1")
        self.assertFalse(self.run_artifact(tree))

    def test_unexpected_exported_pin_fails(self):
        tree = ET.parse(ARTIFACT)
        net = tree.find("./nets/net")
        ET.SubElement(net, "node", ref="UNEXPECTED", pin="99", pintype="passive")
        self.assertFalse(self.run_artifact(tree))

    def test_missing_imu_pin_fails(self):
        tree = ET.parse(ARTIFACT)
        for net in tree.findall("./nets/net"):
            for node in list(net):
                if node.get("ref") == "J6" and node.get("pin") == "10":
                    net.remove(node)
        self.assertFalse(self.run_artifact(tree))


class ElectricalRules(unittest.TestCase):
    def test_verified_export_has_no_errors_or_off_grid_endpoints(self):
        report = json.loads(ERC_ARTIFACT.read_text(encoding="utf-8"))
        violations = [item for sheet in report["sheets"]
                      for item in sheet["violations"]]
        self.assertFalse([item for item in violations if item["severity"] == "error"])
        self.assertFalse([item for item in violations
                          if item["type"] == "endpoint_off_grid"])


if __name__ == "__main__":
    unittest.main()

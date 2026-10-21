"""Contact, real overlap and failed render regressions for #220."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import tasks

TOOLS = Path(__file__).parent / "cad/tools"
sys.path.insert(0, str(TOOLS))
from check_interference import PARTS, classify_render, off_contact, overlap, planar_components, planned_pairs


def tetra(origin=(0, 0, 0), height=1):
    x, y, z = origin
    a, b, c, d = (x, y, z), (x+1, y, z), (x, y+1, z), (x, y, z+height)
    return [(a, c, b), (a, b, d), (b, c, d), (c, a, d)]


def write_stl(path, triangles):
    lines = ["solid fixture"]
    for t in triangles:
        lines += ["facet normal 0 0 0", "outer loop"]
        lines += ["vertex " + " ".join(map(str, p)) for p in t]
        lines += ["endloop", "endfacet"]
    path.write_text("\n".join(lines + ["endsolid fixture"]), encoding="utf-8")


WARNING = "WARNING: Object may not be a valid 2-manifold and may need repair!"
PLANE = [((0, 0, 0), (0, 1, 0), (0, 0, 1))]


class RenderClassification(unittest.TestCase):
    def classify(self, triangles, log="", code=0, intersection=True):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "result.stl"
            write_stl(p, triangles)
            return classify_render(p, subprocess.CompletedProcess([], code, "", log), intersection)

    def test_separate_flat_contacts_are_not_a_solid(self):
        triangles = PLANE + [tuple((p[0]+10, p[1], p[2]) for p in t) for t in PLANE]
        self.assertEqual(self.classify(triangles, WARNING)[0], "contact")
        self.assertEqual(len(planar_components(triangles)), 2)

    def test_flat_plus_solid_is_not_accepted_as_contact(self):
        with self.assertRaises(ValueError):
            self.classify(PLANE + tetra((10, 0, 0)), WARNING)

    def test_folded_surface_is_not_planar(self):
        folded = PLANE + [((0, 0, 0), (0, 1, 0), (1, 0, 0))]
        with self.assertRaises(ValueError):
            self.classify(folded, WARNING)

    def test_thin_volume_is_not_contact(self):
        self.assertEqual(self.classify(tetra(height=0.000001))[0], "solid")

    def test_solid_volume(self):
        kind, volume = self.classify(tetra())
        self.assertEqual(kind, "solid")
        self.assertAlmostEqual(volume, 1/6000)

    def test_unknown_module_warning_is_never_ignored(self):
        with self.assertRaises(ValueError):
            self.classify(PLANE, WARNING + "\nWARNING: Ignoring unknown module 'missing'")

    def test_empty_is_only_valid_for_successful_intersection(self):
        self.assertEqual(self.classify([], "Current top level object is empty.", 1)[0], "empty")
        with self.assertRaises(ValueError):
            self.classify([], "Current top level object is empty.", 1, False)
        with self.assertRaises(ValueError):
            self.classify([], "Current top level object is empty.\nWARNING: unknown module", 1)
        with self.assertRaises(ValueError):
            self.classify([], "Current top level object is empty.", 2)

    def test_empty_stl_without_diagnostic_fails(self):
        with self.assertRaises(ValueError):
            self.classify([])

    def test_render_error_and_nonzero_exit_fail(self):
        for log, code in (("ERROR: Parser error", 0), ("", 1)):
            with self.assertRaises(ValueError):
                self.classify(tetra(), log, code)

    def test_planar_part_is_not_valid_solid(self):
        with self.assertRaises(ValueError):
            self.classify(PLANE, WARNING, intersection=False)

    def test_broad_phase_does_not_skip_sub_001_mm_overlap(self):
        self.assertTrue(overlap(((0,0,0),(1,1,1)), ((.999,0,0),(2,1,1))))

    def test_focus_keeps_every_pair_touching_changed_parts(self):
        focus = {"perfboard", "receiver", "teensy", "imu", "kill_switch"}
        complete, selected = planned_pairs(), planned_pairs(focus)
        self.assertEqual(len(complete), 322)
        self.assertEqual(len(selected), 115)
        self.assertTrue(all(a in focus or b in focus for a, b in selected))
        self.assertEqual(selected, [pair for pair in complete if pair[0] in focus or pair[1] in focus])


class OffContactProof(unittest.TestCase):
    def classify(self, text, log="", code=0):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"case.off"
            p.write_text(text, encoding="utf-8")
            return off_contact(p, subprocess.CompletedProcess([], code, "", log))

    def test_planar_contact(self):
        self.assertEqual(self.classify("OFF 3 1 0 0 0 0 0 1 0 0 0 1 3 0 1 2"), [(0, 0.0)])

    def test_closed_thin_volume_fails_contact(self):
        with self.assertRaises(ValueError):
            self.classify("OFF 4 4 0 0 0 0 1 0 0 0 1 0 0 0 0.000001 3 0 2 1 3 0 1 3 3 1 2 3 3 2 0 3")

    def test_flat_plus_solid_fails_contact(self):
        with self.assertRaises(ValueError):
            self.classify("OFF 7 5 0 10 0 0 10 1 0 10 0 1 0 0 0 1 0 0 0 1 0 0 0 1 3 0 1 2 3 3 5 4 3 3 4 6 3 4 5 6 3 5 3 6")

    def test_unclassified_data_fails(self):
        for text in ("OFF 0 0 0", "OFF 3 1 0 0 0 0", "bad", "OFF 3 1 0 nan 0 0 0 1 0 0 0 1 3 0 1 2", "OFF 3 1 0 0 0 0 0 1 0 0 0 1 3 0 1 3"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.classify(text)

    def test_render_failure_and_unknown_warning_fail(self):
        text="OFF 3 1 0 0 0 0 0 1 0 0 0 1 3 0 1 2"
        for log, code in (("WARNING: unknown module", 0), ("", 1)):
            with self.assertRaises(ValueError):
                self.classify(text, log, code)


@unittest.skipUnless(tasks.find_openscad(), "OpenSCAD not installed")
class RealRenderer(unittest.TestCase):
    def render(self, source, intersection=True):
        with tempfile.TemporaryDirectory() as tmp:
            src, stl = Path(tmp)/"case.scad", Path(tmp)/"case.stl"
            src.write_text(source, encoding="utf-8")
            result = subprocess.run([tasks.find_openscad(), "--render", "-o", str(stl), str(src)],
                                    capture_output=True, text=True, encoding="utf-8", errors="replace")
            return classify_render(stl, result, intersection)

    def test_shared_face_is_not_volume(self):
        kind, _ = self.render("intersection(){ cube(2); translate([2,0,0]) cube(2); }")
        self.assertIn(kind, ("empty", "contact"))

    def test_real_overlap_is_measured(self):
        kind, volume = self.render("intersection(){ cube(2); translate([1,0,0]) cube(2); }")
        self.assertEqual(kind, "solid")
        self.assertAlmostEqual(volume, .004)

    def test_unknown_module_and_syntax_error_fail(self):
        for source in ("intersection(){ missing(); cube(2); }", "cube(;"):
            with self.assertRaises(ValueError):
                self.render(source)

    def test_empty_part_fails(self):
        with self.assertRaises(ValueError):
            self.render("intersection(){ cube(1); translate([2,0,0]) cube(1); }", False)


if __name__ == "__main__":
    unittest.main()

"""Palette parsing and confusable-pair analysis tests."""

import json
import os
import tempfile
import unittest

from chromashift.color import ColorError
from chromashift.palette import (PaletteError, analyze, parse_palette,
                                 parse_palette_file, render_json, render_text)

GOOD = """// comment
error #d32f2f
success #2e7d32
#1565c0 info
plainhex #455a64
"""


class ParseTests(unittest.TestCase):
    def test_mixed_forms(self):
        colors = parse_palette(GOOD)
        self.assertEqual([c.name for c in colors],
                         ["error", "success", "info", "plainhex"])
        self.assertEqual(colors[0].rgb, (211, 47, 47))
        self.assertEqual(colors[2].hex, "#1565c0")

    def test_nameless_color_gets_generated_name(self):
        colors = parse_palette("#aabbcc\n#112233\n")
        self.assertEqual(colors[0].name, "color-1")
        self.assertEqual(colors[1].name, "color-2")

    def test_comment_lines_ignored(self):
        colors = parse_palette("// just a comment\n\n#d32f2f\n")
        self.assertEqual(len(colors), 1)

    def test_hash_line_that_is_not_a_color_errors_with_line_number(self):
        with self.assertRaises(PaletteError) as ctx:
            parse_palette("ok #ffffff\n#nothex\n")
        self.assertIn("line 2", str(ctx.exception))

    def test_empty_palette_errors(self):
        with self.assertRaises(PaletteError) as ctx:
            parse_palette("// nothing\n\n")
        self.assertIn("no colors", str(ctx.exception))

    def test_invalid_hex_token_in_named_line_skipped_then_parsed(self):
        colors = parse_palette("name notacolor #ff0000\n")
        self.assertEqual(len(colors), 1)
        self.assertEqual(colors[0].hex, "#ff0000")

    def test_parse_file_missing(self):
        with self.assertRaises(PaletteError) as ctx:
            parse_palette_file(os.path.join(tempfile.gettempdir(), "nope-palette.txt"))
        self.assertIn("cannot read", str(ctx.exception))

    def test_parse_file_ok(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as fh:
            fh.write(GOOD)
            path = fh.name
        try:
            self.assertEqual(len(parse_palette_file(path)), 4)
        finally:
            os.unlink(path)


class AnalyzeTests(unittest.TestCase):
    def make(self, threshold, severity=1.0):
        colors = parse_palette("error #d32f2f\nsuccess #2e7d32\ninfo #1565c0\n")
        return analyze(colors, threshold=threshold, severity=severity)

    def test_high_threshold_flags_red_green_pair(self):
        report = self.make(1000.0)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertGreater(report["flagged_total"], 0)
        deutan = report["conditions"]["deuteranopia"]
        names = {(row["a"], row["b"]) for row in deutan["flagged"]}
        self.assertIn(("error", "success"), names)

    def test_zero_threshold_passes(self):
        report = self.make(0.0)
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["flagged_total"], 0)

    def test_severity_zero_matches_normal_delta_e(self):
        # With severity 0 the simulated ΔE equals the normal-vision ΔE.
        report = self.make(1000.0, severity=0.0)
        for cond in report["conditions"].values():
            for row in cond["flagged"]:
                self.assertAlmostEqual(row["de_cvd"], row["de_normal"], places=2)

    def test_flagged_sorted_by_worst_distance(self):
        report = self.make(1000.0)
        for cond in report["conditions"].values():
            des = [row["de_cvd"] for row in cond["flagged"]]
            self.assertEqual(des, sorted(des))

    def test_pair_count(self):
        report = self.make(6.0)
        self.assertEqual(report["pair_count"], 3)  # C(3,2)

    def test_negative_threshold_rejected(self):
        colors = parse_palette("#ff0000\n")
        with self.assertRaises(ValueError):
            analyze(colors, threshold=-1)

    def test_unknown_condition_rejected(self):
        colors = parse_palette("#ff0000\n")
        with self.assertRaises(ValueError):
            analyze(colors, threshold=1.0, conditions=("colorium",))


class RenderTests(unittest.TestCase):
    def test_text_report(self):
        colors = parse_palette("error #d32f2f\nsuccess #2e7d32\n")
        report = analyze(colors, threshold=1000.0)
        text = render_text(report)
        self.assertIn("chromashift — palette CVD report", text)
        self.assertIn("verdict: FAIL", text)
        self.assertIn("protanopia", text)
        self.assertIn("error (#d32f2f)", text)

    def test_json_round_trip(self):
        colors = parse_palette("#ff0000\n#00ff00\n")
        report = analyze(colors, threshold=5.0)
        parsed = json.loads(render_json(report))
        self.assertEqual(parsed["tool"], "chromashift")
        self.assertEqual(parsed["pair_count"], 1)
        self.assertIn(parsed["verdict"], ("PASS", "FAIL"))


if __name__ == "__main__":
    unittest.main()

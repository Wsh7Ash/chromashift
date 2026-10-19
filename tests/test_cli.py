"""CLI end-to-end tests (real subprocess runs)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTS_DIR)
SRC = os.path.join(ROOT, "src")
EXAMPLES = os.path.join(ROOT, "examples")


def run_cli(*args):
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "chromashift", *args],
        capture_output=True, text=True, env=env, cwd=ROOT,
    )


class CliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="chromashift-test-")
        # Build a tiny 2x1 RGB PNG fixture with the package's own encoder.
        sys.path.insert(0, SRC)
        from chromashift.png import Image, encode_file  # noqa: E402
        cls.fixture = os.path.join(cls.tmp, "shot.png")
        encode_file(Image(2, 1, bytearray((255, 0, 0, 255, 0, 255, 0, 255))),
                    cls.fixture)
        cls.bad_png = os.path.join(cls.tmp, "broken.png")
        with open(cls.bad_png, "wb") as fh:
            fh.write(b"this is not a png at all")

    def test_version(self):
        proc = run_cli("--version")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("chromashift 0.1.0", proc.stdout)

    def test_no_command_is_usage_error(self):
        proc = run_cli()
        self.assertEqual(proc.returncode, 2)

    def test_swatches_writes_grid(self):
        out = os.path.join(self.tmp, "sw.png")
        proc = run_cli("swatches", "--out", out)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        sys.path.insert(0, SRC)
        from chromashift.png import decode_file
        img = decode_file(out)
        # 24 colors, 8 columns → 8*40 + 7*4 wide, 3 rows tall
        self.assertEqual((img.width, img.height), (348, 128))

    def test_swatches_strip(self):
        strip = os.path.join(self.tmp, "strip.png")
        proc = run_cli("swatches", "--out", os.path.join(self.tmp, "s.png"),
                       "--strip", strip, "-c", "protanopia,deuteranopia")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        sys.path.insert(0, SRC)
        from chromashift.png import decode_file
        img = decode_file(strip)
        # 3 images (original + 2 conditions), gap 8
        self.assertEqual(img.width, 348 * 3 + 8 * 2)
        self.assertEqual(img.height, 128)

    def test_simulate_default_all_conditions(self):
        proc = run_cli("simulate", self.fixture, "--out-dir", self.tmp)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for cond in ("protanopia", "deuteranopia", "tritanopia"):
            path = os.path.join(self.tmp, f"shot.{cond}.png")
            self.assertTrue(os.path.exists(path), path)
            self.assertIn(path.replace("\\", "/"), proc.stdout.replace("\\", "/"))

    def test_simulate_strip(self):
        strip = os.path.join(self.tmp, "cmp.png")
        proc = run_cli("simulate", self.fixture, "--out-dir", self.tmp,
                       "-c", "all", "--strip", strip)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        sys.path.insert(0, SRC)
        from chromashift.png import decode_file
        img = decode_file(strip)
        # original + 3 conditions, gap 8 → 2px images
        self.assertEqual(img.width, 2 * 4 + 8 * 3)
        self.assertEqual(img.height, 1)

    def test_simulate_bad_input_exits_2(self):
        proc = run_cli("simulate", self.bad_png)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("signature", proc.stderr)

    def test_simulate_missing_file_exits_2(self):
        proc = run_cli("simulate", os.path.join(self.tmp, "nope.png"))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("error:", proc.stderr)

    def test_unknown_condition_exits_2(self):
        proc = run_cli("simulate", self.fixture, "-c", "colorium")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("unknown condition", proc.stderr)

    def test_bad_severity_exits_2(self):
        proc = run_cli("simulate", self.fixture, "--severity", "4.2")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("severity", proc.stderr)

    def test_palette_high_threshold_fails(self):
        proc = run_cli("palette", os.path.join(EXAMPLES, "ui-palette.txt"),
                       "--threshold", "1000")
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("verdict: FAIL", proc.stdout)

    def test_palette_zero_threshold_passes(self):
        proc = run_cli("palette", os.path.join(EXAMPLES, "ui-palette.txt"),
                       "--threshold", "0")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("verdict: PASS", proc.stdout)

    def test_palette_json_and_swatch(self):
        swatch = os.path.join(self.tmp, "pal.png")
        proc = run_cli("palette", os.path.join(EXAMPLES, "safe-palette.txt"),
                       "--threshold", "0", "--format", "json", "--swatch", swatch)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["tool"], "chromashift")
        self.assertEqual(len(payload["colors"]), 5)
        self.assertTrue(os.path.exists(swatch))
        sys.path.insert(0, SRC)
        from chromashift.png import decode_file
        img = decode_file(swatch)
        # 5 colors, 4 rows (normal + 3 conditions), 5 columns
        self.assertEqual(img.width, 5 * 40 + 4 * 4)
        self.assertEqual(img.height, 4 * 40 + 3 * 4)

    def test_palette_missing_file_exits_2(self):
        proc = run_cli("palette", os.path.join(self.tmp, "nope.txt"))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("cannot read", proc.stderr)

    def test_palette_empty_file_exits_2(self):
        path = os.path.join(self.tmp, "empty.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("// nothing here\n")
        proc = run_cli("palette", path)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("no colors", proc.stderr)


if __name__ == "__main__":
    unittest.main()

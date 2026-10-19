"""CVD matrix and simulation tests (grounded in Machado et al. 2009 Table 1)."""

import unittest

from chromashift.cvd import (CONDITIONS, matrix, side_by_side, simulate_image,
                             simulate_rgb)
from chromashift.png import Image


def px(*rgba):
    return Image(1, 1, bytearray(rgba))


class MatrixTests(unittest.TestCase):
    def test_severity_zero_is_identity(self):
        for cond in CONDITIONS:
            m = matrix(cond, 0.0)
            self.assertEqual(m, [1.0, 0.0, -0.0, 0.0, 1.0, 0.0, -0.0, -0.0, 1.0],
                             msg=cond)

    def test_published_dichromacy_values(self):
        # Transcription check against Table 1, severity 1.0.
        prot = matrix("protanopia", 1.0)
        self.assertAlmostEqual(prot[0], 0.152286, places=6)
        self.assertAlmostEqual(prot[1], 1.052583, places=6)
        self.assertAlmostEqual(prot[8], 1.051998, places=6)
        deut = matrix("deuteranopia", 1.0)
        self.assertAlmostEqual(deut[0], 0.367322, places=6)
        self.assertAlmostEqual(deut[4], 0.672501, places=6)
        trit = matrix("tritanopia", 1.0)
        self.assertAlmostEqual(trit[0], 1.255528, places=6)
        self.assertAlmostEqual(trit[7], 0.691367, places=6)

    def test_severity_zero_point_one_matches_table(self):
        m = matrix("protanopia", 0.1)
        self.assertAlmostEqual(m[0], 0.856167, places=6)
        self.assertAlmostEqual(m[1], 0.182038, places=6)

    def test_interpolation_between_table_rows(self):
        lo, hi = matrix("deuteranopia", 0.4), matrix("deuteranopia", 0.5)
        mid = matrix("deuteranopia", 0.45)
        for a, m, b in zip(lo, mid, hi):
            self.assertAlmostEqual(m, (a + b) / 2, places=6)

    def test_severity_monotonic_for_protanopia(self):
        # First coefficient falls as severity grows (published table).
        values = [matrix("protanopia", s / 10)[0] for s in range(11)]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_unknown_condition(self):
        with self.assertRaises(ValueError) as ctx:
            matrix("colorium", 1.0)
        self.assertIn("unknown condition", str(ctx.exception))

    def test_severity_bounds(self):
        for bad in (-0.1, 1.1):
            with self.assertRaises(ValueError):
                matrix("protanopia", bad)


class SimulateRgbTests(unittest.TestCase):
    def test_pure_red_protanopia(self):
        self.assertEqual(simulate_rgb((255, 0, 0), "protanopia"), (39, 29, 0))

    def test_white_stays_white(self):
        for cond in CONDITIONS:
            self.assertEqual(simulate_rgb((255, 255, 255), cond), (255, 255, 255),
                             msg=cond)

    def test_black_stays_black(self):
        for cond in CONDITIONS:
            self.assertEqual(simulate_rgb((0, 0, 0), cond), (0, 0, 0), msg=cond)

    def test_severity_zero_is_noop(self):
        for cond in CONDITIONS:
            self.assertEqual(simulate_rgb((17, 130, 200), cond, 0.0), (17, 130, 200))

    def test_negative_results_clamped(self):
        r, g, b = simulate_rgb((0, 255, 0), "tritanopia")
        self.assertGreaterEqual(min(r, g, b), 0)
        self.assertLessEqual(max(r, g, b), 255)


class SimulateImageTests(unittest.TestCase):
    def test_transforms_pixels_and_keeps_alpha(self):
        img = Image(2, 1, bytearray((255, 0, 0, 111, 0, 0, 255, 222)))
        out = simulate_image(img, "protanopia")
        self.assertEqual(out.get(0, 0)[3], 111)
        self.assertEqual(out.get(1, 0)[3], 222)
        self.assertEqual(out.get(0, 0)[:3], (39, 29, 0))
        # original untouched
        self.assertEqual(img.get(0, 0), (255, 0, 0, 111))

    def test_severity_zero_copies_pixels(self):
        img = Image(1, 1, bytearray((40, 50, 60, 255)))
        out = simulate_image(img, "deuteranopia", 0.0)
        self.assertEqual(out.get(0, 0), (40, 50, 60, 255))


class SideBySideTests(unittest.TestCase):
    def test_geometry_and_pixels(self):
        a = Image(2, 2, bytearray([1, 1, 1, 255] * 4))
        b = Image(3, 1, bytearray([9, 9, 9, 255] * 3))
        out = side_by_side([a, b], gap=4, divider=(7, 7, 7, 255))
        self.assertEqual(out.width, 2 + 4 + 3)
        self.assertEqual(out.height, 2)
        self.assertEqual(out.get(0, 0)[:3], (1, 1, 1))
        self.assertEqual(out.get(2, 0)[:3], (7, 7, 7))      # divider column
        self.assertEqual(out.get(6, 0)[:3], (9, 9, 9))      # right image starts
        self.assertEqual(out.get(1, 1)[:3], (1, 1, 1))      # short row padded bg
        self.assertEqual(out.get(0, 1)[:3], (1, 1, 1))

    def test_requires_images(self):
        with self.assertRaises(ValueError):
            side_by_side([])


if __name__ == "__main__":
    unittest.main()

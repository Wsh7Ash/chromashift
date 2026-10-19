"""Hex parsing, Lab conversion, and ΔE76 tests."""

import unittest

from chromashift.color import (ColorError, delta_e76, parse_hex, rgb_to_lab,
                               to_hex)


class HexTests(unittest.TestCase):
    def test_parse_full_hex(self):
        self.assertEqual(parse_hex("#d32f2f"), (211, 47, 47))
        self.assertEqual(parse_hex("1565c0"), (21, 101, 192))
        self.assertEqual(parse_hex("  #FAFAFA "), (250, 250, 250))

    def test_parse_short_hex(self):
        self.assertEqual(parse_hex("#abc"), (170, 187, 204))
        self.assertEqual(parse_hex("f00"), (255, 0, 0))

    def test_parse_invalid(self):
        for bad in ("", "#", "#zzzzzz", "#12345", "1234567", "#12345g"):
            with self.assertRaises(ColorError, msg=bad):
                parse_hex(bad)

    def test_to_hex_roundtrip(self):
        self.assertEqual(to_hex((211, 47, 47)), "#d32f2f")
        self.assertEqual(parse_hex(to_hex((1, 2, 3))), (1, 2, 3))


class LabTests(unittest.TestCase):
    def test_white_is_lightness_100(self):
        lab = rgb_to_lab((255, 255, 255))
        self.assertAlmostEqual(lab[0], 100.0, delta=0.05)
        self.assertAlmostEqual(lab[1], 0.0, delta=0.1)
        self.assertAlmostEqual(lab[2], 0.0, delta=0.1)

    def test_black_is_zero(self):
        lab = rgb_to_lab((0, 0, 0))
        self.assertAlmostEqual(lab[0], 0.0, delta=1e-9)
        self.assertAlmostEqual(lab[1], 0.0, delta=1e-6)
        self.assertAlmostEqual(lab[2], 0.0, delta=1e-6)

    def test_pure_red_reference_values(self):
        # Standard sRGB red in CIELAB/D65: L*≈53.24, a*≈80.09, b*≈67.20.
        lab = rgb_to_lab((255, 0, 0))
        self.assertAlmostEqual(lab[0], 53.24, delta=0.1)
        self.assertAlmostEqual(lab[1], 80.09, delta=0.15)
        self.assertAlmostEqual(lab[2], 67.20, delta=0.15)

    def test_delta_e_identical_colors_is_zero(self):
        lab = rgb_to_lab((30, 120, 200))
        self.assertEqual(delta_e76(lab, lab), 0.0)

    def test_delta_e_white_black_is_100(self):
        self.assertAlmostEqual(
            delta_e76(rgb_to_lab((255, 255, 255)), rgb_to_lab((0, 0, 0))),
            100.0, delta=0.05)

    def test_delta_e_symmetric(self):
        a = rgb_to_lab((200, 30, 30))
        b = rgb_to_lab((30, 200, 30))
        self.assertAlmostEqual(delta_e76(a, b), delta_e76(b, a), places=9)


if __name__ == "__main__":
    unittest.main()

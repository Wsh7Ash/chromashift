"""PNG codec tests: round-trips, filters, and rejections."""

import struct
import unittest
import zlib

from chromashift.png import (Image, PNGError, decode, encode, unfilter)


def chunk(ctype: bytes, body: bytes) -> bytes:
    crc = zlib.crc32(ctype + body) & 0xFFFFFFFF
    return struct.pack(">I", len(body)) + ctype + body + struct.pack(">I", crc)


def make_png(w, h, depth, color, scanlines, plte=None, trns=None,
             sig=b"\x89PNG\r\n\x1a\n", corrupt_crc=False):
    ihdr = struct.pack(">IIBBBBB", w, h, depth, color, 0, 0, 0)
    out = sig + chunk(b"IHDR", ihdr)
    if plte is not None:
        out += chunk(b"PLTE", plte)
    if trns is not None:
        out += chunk(b"tRNS", trns)
    idat = chunk(b"IDAT", zlib.compress(bytes(scanlines)))
    if corrupt_crc:
        idat = idat[:-1] + bytes([idat[-1] ^ 0xFF])
    return out + idat + chunk(b"IEND", b"")


def image_from(rows):
    """rows: list of list of (r,g,b,a)."""
    h = len(rows)
    w = len(rows[0])
    px = bytearray()
    for row in rows:
        for cell in row:
            px.extend(cell)
    return Image(w, h, px)


class RoundTripTests(unittest.TestCase):
    def test_encode_decode_roundtrip(self):
        img = image_from([
            [(255, 0, 0, 255), (0, 255, 0, 200)],
            [(0, 0, 255, 128), (10, 20, 30, 0)],
        ])
        out = decode(encode(img))
        self.assertEqual((out.width, out.height), (2, 2))
        self.assertEqual(out.get(0, 0), (255, 0, 0, 255))
        self.assertEqual(out.get(1, 0), (0, 255, 0, 200))
        self.assertEqual(out.get(0, 1), (0, 0, 255, 128))
        self.assertEqual(out.get(1, 1), (10, 20, 30, 0))

    def test_encode_is_valid_png_header(self):
        img = image_from([[(1, 2, 3, 4)]])
        data = encode(img)
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertIn(b"IHDR", data)
        self.assertIn(b"IEND", data)

    def test_set_get(self):
        img = image_from([[(0, 0, 0, 255)]])
        img.set(0, 0, (9, 8, 7, 6))
        self.assertEqual(img.get(0, 0), (9, 8, 7, 6))


class DecodeVariantsTests(unittest.TestCase):
    def test_rgb(self):
        scan = bytes([0, 10, 20, 30])  # filter 0 + one RGB pixel
        img = decode(make_png(1, 1, 8, 2, scan))
        self.assertEqual(img.get(0, 0), (10, 20, 30, 255))

    def test_grayscale(self):
        scan = bytes([0, 77])
        img = decode(make_png(1, 1, 8, 0, scan))
        self.assertEqual(img.get(0, 0), (77, 77, 77, 255))

    def test_gray_alpha(self):
        scan = bytes([0, 77, 128])
        img = decode(make_png(1, 1, 8, 4, scan))
        self.assertEqual(img.get(0, 0), (77, 77, 77, 128))

    def test_palette_with_transparency(self):
        plte = bytes([255, 0, 0, 0, 255, 0])
        trns = bytes([255, 64])
        scan = bytes([0, 0, 1])  # two pixels: index 0, index 1
        img = decode(make_png(2, 1, 8, 3, scan, plte=plte, trns=trns))
        self.assertEqual(img.get(0, 0), (255, 0, 0, 255))
        self.assertEqual(img.get(1, 0), (0, 255, 0, 64))

    def test_palette_index_out_of_range(self):
        plte = bytes([255, 0, 0])
        scan = bytes([0, 9])
        with self.assertRaises(PNGError):
            decode(make_png(1, 1, 8, 3, scan, plte=plte))

    def test_bad_signature(self):
        with self.assertRaises(PNGError) as ctx:
            decode(b"JUNKJUNKJUNK")
        self.assertIn("signature", str(ctx.exception))

    def test_truncated_missing_idat(self):
        data = make_png(1, 1, 8, 2, bytes([0, 1, 2, 3]))
        cut = data.index(b"IDAT") - 4
        with self.assertRaises(PNGError) as ctx:
            decode(data[:cut])
        self.assertIn("truncated", str(ctx.exception))

    def test_corrupt_crc_rejected(self):
        with self.assertRaises(PNGError) as ctx:
            decode(make_png(1, 1, 8, 2, bytes([0, 1, 2, 3]), corrupt_crc=True))
        self.assertIn("CRC", str(ctx.exception))

    def test_bit_depth_16_rejected(self):
        with self.assertRaises(PNGError) as ctx:
            decode(make_png(1, 1, 16, 2, bytes(8)))
        self.assertIn("bit depth 16", str(ctx.exception))

    def test_interlaced_rejected(self):
        ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 1)
        data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) \
            + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00")) + chunk(b"IEND", b"")
        with self.assertRaises(PNGError) as ctx:
            decode(data)
        self.assertIn("interlaced", str(ctx.exception))

    def test_corrupt_idat_rejected(self):
        ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
        data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) \
            + chunk(b"IDAT", b"not zlib data") + chunk(b"IEND", b"")
        with self.assertRaises(PNGError) as ctx:
            decode(data)
        self.assertIn("IDAT", str(ctx.exception))


class UnfilterTests(unittest.TestCase):
    def test_none_filter(self):
        out = unfilter(bytes([0, 1, 2, 3]), width=3, height=1, channels=1)
        self.assertEqual(list(out), [1, 2, 3])

    def test_sub_filter(self):
        out = unfilter(bytes([1, 5, 5, 5]), width=3, height=1, channels=1)
        self.assertEqual(list(out), [5, 10, 15])

    def test_up_filter(self):
        raw = bytes([0, 1, 2, 3]) + bytes([2, 10, 20, 30])
        out = unfilter(raw, width=3, height=2, channels=1)
        self.assertEqual(list(out[3:]), [11, 22, 33])

    def test_average_filter(self):
        # PNG Average: out[i] = enc[i] + ((reconstructed_a + prior[i]) >> 1)
        # i0: (0+10)>>1=5 → 5; i1: (5+10)>>1=7 → 7; i2: (7+10)>>1=8 → 8
        raw = bytes([0, 10, 10, 10]) + bytes([3, 0, 0, 0])
        out = unfilter(raw, width=3, height=2, channels=1)
        self.assertEqual(list(out[3:]), [5, 7, 8])

    def test_paeth_filter(self):
        # prior = [10,10,10], encoded zeros, bpp=1:
        # i0: predictors a=0,b=10,c=0 → Pb wins → 10
        # i1/i2: a=b=c=10 → Pa wins → 10
        raw = bytes([0, 10, 10, 10]) + bytes([4, 0, 0, 0])
        out = unfilter(raw, width=3, height=2, channels=1)
        self.assertEqual(list(out[3:]), [10, 10, 10])

    def test_size_mismatch(self):
        with self.assertRaises(PNGError) as ctx:
            unfilter(bytes([0, 1, 2]), width=3, height=1, channels=1)
        self.assertIn("size mismatch", str(ctx.exception))

    def test_unknown_filter(self):
        with self.assertRaises(PNGError) as ctx:
            unfilter(bytes([9, 1, 2, 3]), width=3, height=1, channels=1)
        self.assertIn("filter type", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

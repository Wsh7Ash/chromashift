"""Minimal, dependency-free PNG codec.

Decode: 8-bit non-interlaced images of color types 0 (gray), 2 (RGB),
3 (palette), 4 (gray+alpha) and 6 (RGBA). Unsupported variants raise
:class:`PNGError` with an actionable message — chromashift never guesses.

Encode: always RGBA8 with filter 0 scanlines and a single IDAT chunk, which
every PNG reader accepts.
"""

from __future__ import annotations

import struct
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"

# color type → (channels, palette?) for bit depth 8
_COLOR_TYPES = {
    0: (1, False),  # gray
    2: (3, False),  # RGB
    3: (1, True),   # palette index
    4: (2, False),  # gray + alpha
    6: (4, False),  # RGBA
}


class PNGError(Exception):
    """Invalid or unsupported PNG input."""


class Image:
    """Decoded image held as an RGBA bytearray (row-major, 4 bytes/pixel)."""

    def __init__(self, width: int, height: int, pixels: bytearray):
        self.width = width
        self.height = height
        self.pixels = pixels

    def get(self, x: int, y: int) -> tuple[int, int, int, int]:
        i = (y * self.width + x) * 4
        px = self.pixels
        return px[i], px[i + 1], px[i + 2], px[i + 3]

    def set(self, x: int, y: int, rgba: tuple[int, int, int, int]) -> None:
        i = (y * self.width + x) * 4
        self.pixels[i:i + 4] = bytes(rgba)

    def new(self, width: int, height: int) -> "Image":
        return Image(width, height, bytearray(width * height * 4))


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def unfilter(raw: bytes, width: int, height: int, channels: int) -> bytearray:
    """Reverse PNG scanline filtering (filters 0–4) for 8-bit samples."""
    stride = width * channels
    if len(raw) != (stride + 1) * height:
        raise PNGError(
            f"IDAT size mismatch: got {len(raw)} bytes, expected "
            f"{(stride + 1) * height} for {width}x{height}x{channels}"
        )
    out = bytearray(stride)
    prior = bytearray(stride)
    pos = 0
    for row in range(height):
        ftype = raw[pos]
        line = bytearray(raw[pos + 1:pos + 1 + stride])
        pos += 1 + stride
        if ftype == 0:
            pass
        elif ftype == 1:  # Sub
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif ftype == 2:  # Up
            for i in range(stride):
                line[i] = (line[i] + prior[i]) & 0xFF
        elif ftype == 3:  # Average
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((a + prior[i]) >> 1)) & 0xFF
        elif ftype == 4:  # Paeth
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                c = prior[i - channels] if i >= channels else 0
                line[i] = (line[i] + _paeth(a, prior[i], c)) & 0xFF
        else:
            raise PNGError(f"unknown PNG filter type {ftype} on row {row}")
        out[row * stride:(row + 1) * stride] = line
        prior = line
    return out


def decode(data: bytes) -> Image:
    """Decode PNG bytes into an RGBA :class:`Image`."""
    if not data.startswith(SIGNATURE):
        raise PNGError("not a PNG file (bad signature)")

    pos = len(SIGNATURE)
    ihdr = None
    palette: bytes | None = None
    trns: bytes | None = None
    idat = bytearray()
    seen_iend = False
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        crc_bytes = data[pos + 8 + length:pos + 12 + length]
        if len(crc_bytes) < 4:
            raise PNGError("truncated PNG chunk")
        (want_crc,) = struct.unpack(">I", crc_bytes)
        if zlib.crc32(ctype + body) & 0xFFFFFFFF != want_crc:
            raise PNGError(f"CRC mismatch in {ctype.decode('latin1')} chunk")
        if ctype == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", body)
        elif ctype == b"PLTE":
            palette = body
        elif ctype == b"tRNS":
            trns = body
        elif ctype == b"IDAT":
            idat.extend(body)
        elif ctype == b"IEND":
            seen_iend = True
            pos += 12 + length
            break
        pos += 12 + length

    if ihdr is None:
        raise PNGError("missing IHDR chunk")
    if not seen_iend or not idat:
        raise PNGError("truncated PNG (missing IDAT/IEND)")

    width, height, depth, color, compression, filter_method, interlace = ihdr
    if compression != 0 or filter_method != 0:
        raise PNGError("unsupported PNG compression/filter method")
    if interlace != 0:
        raise PNGError("interlaced (Adam7) PNGs are not supported; re-export without interlacing")
    if depth != 8:
        raise PNGError(
            f"bit depth {depth} is not supported; re-export as 8-bit "
            "(chromashift handles 8-bit gray/RGB/RGBA/palette only)"
        )
    if color not in _COLOR_TYPES:
        raise PNGError(f"unsupported PNG color type {color}")
    if width <= 0 or height <= 0:
        raise PNGError("invalid PNG dimensions")

    channels, is_palette = _COLOR_TYPES[color]
    if is_palette and palette is None:
        raise PNGError("palette PNG is missing its PLTE chunk")

    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error as exc:
        raise PNGError(f"corrupt IDAT data: {exc}") from None

    flat = unfilter(raw, width, height, channels)
    pixels = bytearray(width * height * 4)
    n = width * height
    if color == 6:
        pixels[:] = flat
    elif color == 2:
        for i in range(n):
            s, d = i * 3, i * 4
            pixels[d:d + 3] = flat[s:s + 3]
            pixels[d + 3] = 255
    elif color == 0:
        for i in range(n):
            v = flat[i]
            pixels[i * 4:i * 4 + 4] = bytes((v, v, v, 255))
    elif color == 4:
        for i in range(n):
            s, d = i * 2, i * 4
            v = flat[s]
            pixels[d:d + 4] = bytes((v, v, v, flat[s + 1]))
    else:  # palette
        plte_entries = len(palette) // 3
        for i in range(n):
            idx = flat[i]
            if idx >= plte_entries:
                raise PNGError(f"palette index {idx} out of range")
            d = i * 4
            pixels[d:d + 3] = palette[idx * 3:idx * 3 + 3]
            pixels[d + 3] = trns[idx] if trns is not None and idx < len(trns) else 255
    return Image(width, height, pixels)


def decode_file(path: str) -> Image:
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError as exc:
        raise PNGError(f"cannot read {path}: {exc}") from None
    return decode(data)


def _chunk(ctype: bytes, body: bytes) -> bytes:
    crc = zlib.crc32(ctype + body) & 0xFFFFFFFF
    return struct.pack(">I", len(body)) + ctype + body + struct.pack(">I", crc)


def encode(img: Image) -> bytes:
    """Encode an RGBA image as PNG bytes (8-bit, non-interlaced, filter 0)."""
    stride = img.width * 4
    raw = bytearray()
    for y in range(img.height):
        raw.append(0)  # filter: None
        raw.extend(img.pixels[y * stride:(y + 1) * stride])
    ihdr = struct.pack(">IIBBBBB", img.width, img.height, 8, 6, 0, 0, 0)
    return (
        SIGNATURE
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )


def encode_file(img: Image, path: str) -> None:
    try:
        with open(path, "wb") as handle:
            handle.write(encode(img))
    except OSError as exc:
        raise PNGError(f"cannot write {path}: {exc}") from None

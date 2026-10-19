"""Color parsing and CIELAB (D65) distance math."""

from __future__ import annotations

# D65 reference white (sRGB)
_WHITE_D65 = (0.95047, 1.0, 1.08883)


class ColorError(ValueError):
    """Invalid color input. Message is safe to show to users."""


def parse_hex(token: str) -> tuple[int, int, int]:
    """Parse ``#RRGGBB``, ``RRGGBB`` or short ``#RGB`` into an RGB triple."""
    s = token.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        raise ColorError(f"{token!r} is not a hex color (want #RRGGBB)")
    try:
        value = int(s, 16)
    except ValueError:
        raise ColorError(f"{token!r} is not a hex color (want #RRGGBB)") from None
    return (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF


def to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _srgb_to_linear(channel: float) -> float:
    c = channel / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def rgb_to_xyz(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    return x, y, z


def _f(t: float) -> float:
    delta = 6.0 / 29.0
    if t > delta ** 3:
        return t ** (1.0 / 3.0)
    return t / (3.0 * delta ** 2) + 4.0 / 29.0


def rgb_to_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """CIE L*a*b* (D65) for an 8-bit sRGB triple."""
    x, y, z = rgb_to_xyz(rgb)
    fx, fy, fz = _f(x / _WHITE_D65[0]), _f(y / _WHITE_D65[1]), _f(z / _WHITE_D65[2])
    return 116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz)


def delta_e76(lab1: tuple[float, float, float],
              lab2: tuple[float, float, float]) -> float:
    """CIE76 color difference (Euclidean distance in L*a*b*)."""
    return sum((a - b) ** 2 for a, b in zip(lab1, lab2)) ** 0.5

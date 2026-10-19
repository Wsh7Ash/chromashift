"""Color-vision-deficiency simulation.

Matrices are the pre-computed simulation matrices published as Table 1 in:

    Machado, G. M., Oliveira, M. M., and Fernandes, L. A. F. (2009).
    "A Physiologically-based Model for Simulation of Color Vision Deficiency."
    IEEE Transactions on Visualization and Computer Graphics, 15(6), 1291–1298.
    DOI: 10.1109/TVCG.2009.113

    Table source: https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html

The table gives one 3×3 matrix per deficiency at severities 0.0–1.0 in steps
of 0.1 (1.0 = full dichromacy). Intermediate severities are produced by
interpolating adjacent tables — the fast approximation the authors themselves
recommend for the 0.1 grid. Severity 0.0 is exactly the identity, so severity 0
is a no-op by construction.

The model multiplies the gamma-encoded RGB triple directly (as the authors'
reference tool does) and the result is clamped to [0, 255]; alpha is untouched.
"""

from __future__ import annotations

from .png import Image

CONDITIONS = ("protanopia", "deuteranopia", "tritanopia")

# Severities 0.0 .. 1.0 (step 0.1); each entry is (protanomaly, deuteranomaly,
# tritanomaly) row-major 3×3 matrices, transcribed from Table 1.
_SEVERITIES = [i / 10 for i in range(11)]

_MATRICES: dict[str, list[list[float]]] = {
    "protanopia": [
        [1.0, 0.0, -0.0, 0.0, 1.0, 0.0, -0.0, -0.0, 1.0],
        [0.856167, 0.182038, -0.038205, 0.029342, 0.955115, 0.015544, -0.002880, -0.001563, 1.004443],
        [0.734766, 0.334872, -0.069637, 0.051840, 0.919198, 0.028963, -0.004928, -0.004209, 1.009137],
        [0.630323, 0.465641, -0.095964, 0.069181, 0.890046, 0.040773, -0.006308, -0.007724, 1.014032],
        [0.539009, 0.579343, -0.118352, 0.082546, 0.866121, 0.051332, -0.007136, -0.011959, 1.019095],
        [0.458064, 0.679578, -0.137642, 0.092785, 0.846313, 0.060902, -0.007494, -0.016807, 1.024301],
        [0.385450, 0.769005, -0.154455, 0.100526, 0.829802, 0.069673, -0.007442, -0.022190, 1.029632],
        [0.319627, 0.849633, -0.169261, 0.106241, 0.815969, 0.077790, -0.007025, -0.028051, 1.035076],
        [0.259411, 0.923008, -0.182420, 0.110296, 0.804340, 0.085364, -0.006276, -0.034346, 1.040622],
        [0.203876, 0.990338, -0.194214, 0.112975, 0.794542, 0.092483, -0.005222, -0.041043, 1.046265],
        [0.152286, 1.052583, -0.204868, 0.114503, 0.786281, 0.099216, -0.003882, -0.048116, 1.051998],
    ],
    "deuteranopia": [
        [1.0, 0.0, -0.0, 0.0, 1.0, 0.0, -0.0, -0.0, 1.0],
        [0.866435, 0.177704, -0.044139, 0.049567, 0.939063, 0.011370, -0.003453, 0.007233, 0.996220],
        [0.760729, 0.319078, -0.079807, 0.090568, 0.889315, 0.020117, -0.006027, 0.013325, 0.992702],
        [0.675425, 0.433850, -0.109275, 0.125303, 0.847755, 0.026942, -0.007950, 0.018572, 0.989378],
        [0.605511, 0.528560, -0.134071, 0.155318, 0.812366, 0.032316, -0.009376, 0.023176, 0.986200],
        [0.547494, 0.607765, -0.155259, 0.181692, 0.781742, 0.036566, -0.010410, 0.027275, 0.983136],
        [0.498864, 0.674741, -0.173604, 0.205199, 0.754872, 0.039929, -0.011131, 0.030969, 0.980162],
        [0.457771, 0.731899, -0.189670, 0.226409, 0.731012, 0.042579, -0.011595, 0.034333, 0.977261],
        [0.422823, 0.781057, -0.203881, 0.245752, 0.709602, 0.044646, -0.011843, 0.037423, 0.974421],
        [0.392952, 0.823610, -0.216562, 0.263559, 0.690210, 0.046232, -0.011910, 0.040281, 0.971630],
        [0.367322, 0.860646, -0.227968, 0.280085, 0.672501, 0.047413, -0.011820, 0.042940, 0.968881],
    ],
    "tritanopia": [
        [1.0, 0.0, -0.0, 0.0, 1.0, 0.0, -0.0, -0.0, 1.0],
        [0.926670, 0.092514, -0.019184, 0.021191, 0.964503, 0.014306, 0.008437, 0.054813, 0.936750],
        [0.895720, 0.133330, -0.029050, 0.029997, 0.945400, 0.024603, 0.013027, 0.104707, 0.882266],
        [0.905871, 0.127791, -0.033662, 0.026856, 0.941251, 0.031893, 0.013410, 0.148296, 0.838294],
        [0.948035, 0.089490, -0.037526, 0.014364, 0.946792, 0.038844, 0.010853, 0.193991, 0.795156],
        [1.017277, 0.027029, -0.044306, -0.006113, 0.958479, 0.047634, 0.006379, 0.248708, 0.744913],
        [1.104996, -0.046633, -0.058363, -0.032137, 0.971635, 0.060503, 0.001336, 0.317922, 0.680742],
        [1.193214, -0.109812, -0.083402, -0.058496, 0.979410, 0.079086, -0.002346, 0.403492, 0.598854],
        [1.257728, -0.139648, -0.118081, -0.078003, 0.975409, 0.102594, -0.003316, 0.501214, 0.502102],
        [1.278864, -0.125333, -0.153531, -0.084748, 0.957674, 0.127074, -0.000989, 0.601151, 0.399838],
        [1.255528, -0.076749, -0.178779, -0.078411, 0.930809, 0.147602, 0.004733, 0.691367, 0.303900],
    ],
}


def matrix(condition: str, severity: float = 1.0) -> list[float]:
    """Return the row-major 3×3 matrix for ``condition`` at ``severity``.

    Severities on the published 0.1 grid return the exact table row;
    values in between are linear interpolations (the authors' recommended
    fast approximation).
    """
    if condition not in _MATRICES:
        raise ValueError(
            f"unknown condition {condition!r} (choose from {', '.join(CONDITIONS)})"
        )
    if not 0.0 <= severity <= 1.0:
        raise ValueError("severity must be in [0, 1]")
    rows = _MATRICES[condition]
    if severity == 1.0:
        return list(rows[-1])
    scaled = severity * 10
    lo = int(scaled)
    hi = min(lo + 1, 10)
    frac = scaled - lo
    a, b = rows[lo], rows[hi]
    if frac == 0:
        return list(a)
    return [x + frac * (y - x) for x, y in zip(a, b)]


def simulate_rgb(rgb: tuple[int, int, int], condition: str,
                 severity: float = 1.0) -> tuple[int, int, int]:
    """Apply the CVD matrix to one RGB triple; output clamped to [0, 255]."""
    m = matrix(condition, severity)
    r, g, b = rgb
    out = []
    for i in range(3):
        v = m[i * 3] * r + m[i * 3 + 1] * g + m[i * 3 + 2] * b
        iv = int(round(v))
        out.append(0 if iv < 0 else 255 if iv > 255 else iv)
    return out[0], out[1], out[2]


def simulate_image(img: Image, condition: str, severity: float = 1.0) -> Image:
    """Return a new Image with every pixel simulated (alpha untouched)."""
    m = matrix(condition, severity)
    src = img.pixels
    out = bytearray(len(src))
    for i in range(0, len(src), 4):
        r, g, b = src[i], src[i + 1], src[i + 2]
        for ch, base in enumerate((r, g, b)):
            v = int(round(m[ch * 3] * r + m[ch * 3 + 1] * g + m[ch * 3 + 2] * b))
            out[i + ch] = 0 if v < 0 else 255 if v > 255 else v
        out[i + 3] = src[i + 3]
    return Image(img.width, img.height, out)


def side_by_side(images: list[Image], gap: int = 8,
                 divider: tuple[int, int, int, int] = (255, 255, 255, 255)) -> Image:
    """Concatenate images horizontally with a solid divider between them."""
    if not images:
        raise ValueError("need at least one image")
    height = max(im.height for im in images)
    width = sum(im.width for im in images) + gap * (len(images) - 1)
    out = Image(width, height, bytearray(width * height * 4))
    # white canvas so short images do not show garbage
    px = bytes(divider)
    for i in range(0, len(out.pixels), 4):
        out.pixels[i:i + 4] = px
    x = 0
    for n, im in enumerate(images):
        if n:
            x += gap
        for y in range(im.height):
            src_off = y * im.width * 4
            dst_off = ((y) * width + x) * 4
            out.pixels[dst_off:dst_off + im.width * 4] = im.pixels[src_off:src_off + im.width * 4]
        x += im.width
    return out

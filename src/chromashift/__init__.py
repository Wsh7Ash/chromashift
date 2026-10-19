"""chromashift: offline color-vision-deficiency simulation for images and palettes."""

from .color import delta_e76, parse_hex, rgb_to_lab, to_hex
from .cvd import CONDITIONS, matrix, side_by_side, simulate_image, simulate_rgb
from .palette import Color, analyze, parse_palette, parse_palette_file
from .png import Image, PNGError, decode, decode_file, encode, encode_file

__version__ = "0.1.0"

__all__ = [
    "delta_e76", "parse_hex", "rgb_to_lab", "to_hex",
    "CONDITIONS", "matrix", "simulate_image", "simulate_rgb", "side_by_side",
    "Color", "analyze", "parse_palette", "parse_palette_file",
    "Image", "PNGError", "decode", "decode_file", "encode", "encode_file",
    "__version__",
]

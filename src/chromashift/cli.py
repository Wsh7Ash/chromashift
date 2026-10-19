"""chromashift command-line interface.

Exit codes:
  0 — success (palette verdict PASS)
  1 — palette verdict FAIL (confusable pairs below threshold)
  2 — usage or input error
"""

from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .color import ColorError
from .cvd import CONDITIONS, side_by_side, simulate_image, simulate_rgb
from .palette import (PaletteError, analyze, parse_palette_file, render_json,
                      render_text)
from .png import PNGError, decode_file, encode_file
from .swatch import DEFAULT_COLUMNS, render_grid, rows_of, swatch_sheet, builtin_rgb


def _conditions(values: list[str] | None) -> tuple[str, ...]:
    if not values:
        return CONDITIONS
    out: list[str] = []
    for value in values:
        for part in value.split(","):
            part = part.strip().lower()
            if not part:
                continue
            if part == "all":
                return CONDITIONS
            if part not in CONDITIONS:
                raise ValueError(
                    f"unknown condition {part!r} (choose from all, {', '.join(CONDITIONS)})"
                )
            if part not in out:
                out.append(part)
    if not out:
        raise ValueError("no conditions selected")
    return tuple(out)


def _severity(value: str) -> float:
    try:
        severity = float(value)
    except ValueError:
        raise ValueError(f"invalid severity {value!r} (want a number in [0, 1])") from None
    if not 0.0 <= severity <= 1.0:
        raise ValueError("severity must be in [0, 1]")
    return severity


def _stem(path: str) -> str:
    base = os.path.basename(path)
    return os.path.splitext(base)[0]


def cmd_simulate(args: argparse.Namespace) -> int:
    conds = _conditions(args.condition)
    severity = _severity(args.severity)
    img = decode_file(args.image)
    out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.image))
    os.makedirs(out_dir, exist_ok=True)

    written: list[str] = []
    simulated = []
    for cond in conds:
        out_img = simulate_image(img, cond, severity)
        path = os.path.join(out_dir, f"{_stem(args.image)}.{cond}.png")
        encode_file(out_img, path)
        written.append(path)
        simulated.append(out_img)
        print(f"wrote {path}")
    if args.strip:
        strip = side_by_side([img, *simulated])
        encode_file(strip, args.strip)
        print(f"wrote {args.strip}")
    print(f"simulated {len(conds)} condition(s) at severity {severity} "
          f"({img.width}x{img.height})")
    return 0


def cmd_swatches(args: argparse.Namespace) -> int:
    conds = _conditions(args.condition)
    severity = _severity(args.severity)
    columns = args.columns
    if columns < 1:
        raise ValueError("--columns must be >= 1")

    original = swatch_sheet(columns)
    encode_file(original, args.out)
    print(f"wrote {args.out} ({original.width}x{original.height}, "
          f"{len(builtin_rgb())} built-in colors)")
    if args.strip:
        grids = [original] + [
            simulate_image(original, cond, severity) for cond in conds
        ]
        encode_file(side_by_side(grids), args.strip)
        print(f"wrote {args.strip}")
    return 0


def cmd_palette(args: argparse.Namespace) -> int:
    conds = _conditions(args.condition)
    severity = _severity(args.severity)
    if args.threshold < 0:
        raise ValueError("--threshold must be >= 0")
    colors = parse_palette_file(args.palette_file)
    report = analyze(colors, threshold=args.threshold, severity=severity,
                     conditions=conds)
    if args.format == "json":
        sys.stdout.write(render_json(report))
    else:
        sys.stdout.write(render_text(report))
    if args.swatch:
        grid_rows = [[c.rgb for c in colors]]
        for cond in conds:
            grid_rows.append([simulate_rgb(c.rgb, cond, severity) for c in colors])
        columns = min(len(colors), 8)
        encode_file(render_grid(grid_rows, columns=columns), args.swatch)
        print(f"wrote {args.swatch}", file=sys.stderr)
    return 1 if report["verdict"] == "FAIL" else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chromashift",
        description="Offline color-vision-deficiency simulation for images and palettes "
                    "(Machado et al. 2009 matrices).",
    )
    parser.add_argument("--version", action="version", version=f"chromashift {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sim = sub.add_parser("simulate", help="simulate an image under CVD conditions")
    sim.add_argument("image", help="input PNG (8-bit gray/RGB/RGBA/palette)")
    sim.add_argument("-c", "--condition", action="append", metavar="NAME",
                     help=f"{'|'.join(CONDITIONS)} or 'all' (repeatable; default: all)")
    sim.add_argument("--severity", default="1.0", metavar="S",
                     help="severity in [0,1] (default: 1.0 = dichromacy)")
    sim.add_argument("--out-dir", default=None, metavar="DIR",
                     help="output directory (default: alongside the input)")
    sim.add_argument("--strip", default=None, metavar="PATH",
                     help="also write a side-by-side strip (original + simulated)")
    sim.set_defaults(func=cmd_simulate)

    sw = sub.add_parser("swatches", help="render the built-in swatch sheet")
    sw.add_argument("--out", default="swatches.png", metavar="PATH",
                    help="output PNG (default: swatches.png)")
    sw.add_argument("--strip", default=None, metavar="PATH",
                    help="also write a side-by-side strip (original + simulated)")
    sw.add_argument("-c", "--condition", action="append", metavar="NAME",
                    help=f"{'|'.join(CONDITIONS)} or 'all' (repeatable; default: all)")
    sw.add_argument("--severity", default="1.0", metavar="S", help="severity in [0,1]")
    sw.add_argument("--columns", type=int, default=DEFAULT_COLUMNS, metavar="N",
                    help=f"swatches per row (default: {DEFAULT_COLUMNS})")
    sw.set_defaults(func=cmd_swatches)

    pa = sub.add_parser("palette", help="flag palette pairs that collapse under CVD")
    pa.add_argument("palette_file", help="text file: one hex color per line, optional name")
    pa.add_argument("-t", "--threshold", type=float, default=6.0, metavar="DE",
                    help="flag pairs with simulated ΔE76 below this (default: 6.0)")
    pa.add_argument("-c", "--condition", action="append", metavar="NAME",
                    help=f"{'|'.join(CONDITIONS)} or 'all' (repeatable; default: all)")
    pa.add_argument("--severity", default="1.0", metavar="S", help="severity in [0,1]")
    pa.add_argument("--format", choices=("text", "json"), default="text",
                    help="report format (default: text)")
    pa.add_argument("--swatch", default=None, metavar="PATH",
                    help="also write a grid PNG: palette rows under each condition")
    pa.set_defaults(func=cmd_palette)
    return parser


def _force_utf8(stream) -> None:
    """Reports contain Δ; Windows locale encodings (cp1252) cannot encode it."""
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8(sys.stdout)
    _force_utf8(sys.stderr)
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (PNGError, PaletteError, ColorError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

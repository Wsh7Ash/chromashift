"""Palette file parsing and CVD confusable-pair analysis."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .color import ColorError, delta_e76, parse_hex, rgb_to_lab, to_hex
from .cvd import CONDITIONS, simulate_rgb


@dataclass(frozen=True)
class Color:
    name: str
    rgb: tuple[int, int, int]

    @property
    def hex(self) -> str:
        return to_hex(self.rgb)


class PaletteError(ValueError):
    """Invalid palette file. Message includes the line number."""


def parse_palette(text: str) -> list[Color]:
    """Parse a palette file: one color per line.

    Accepted forms (hex first or last)::

        #d32f2f
        error #d32f2f
        #2e7d32 success

    Blank lines and ``#``-prefixed comment lines (that are not colors) are
    ignored. Duplicate hex values are allowed (they keep distinct names).
    """
    colors: list[Color] = []
    seen = 0
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        tokens = line.split()
        hex_idx = None
        rgb = None
        for i, tok in enumerate(tokens):
            candidate = tok if tok.startswith("#") else ("#" + tok)
            try:
                rgb = parse_hex(candidate)
            except ColorError:
                continue
            hex_idx = i
            break
        if hex_idx is None or rgb is None:
            if line.startswith("#"):
                raise PaletteError(f"line {lineno}: invalid color {line.split()[0]!r}")
            continue  # plain comment line
        name_tokens = tokens[:hex_idx] + tokens[hex_idx + 1:]
        seen += 1
        name = " ".join(name_tokens) or f"color-{seen}"
        colors.append(Color(name=name, rgb=rgb))
    if not colors:
        raise PaletteError("palette contains no colors")
    return colors


def parse_palette_file(path: str) -> list[Color]:
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        raise PaletteError(f"cannot read palette file: {exc}") from None
    return parse_palette(text)


def analyze(colors: list[Color], threshold: float, severity: float = 1.0,
            conditions: tuple[str, ...] = CONDITIONS) -> dict[str, Any]:
    """Compare every pair under normal vision and each CVD condition.

    A pair is *flagged* for a condition when its simulated ΔE76 falls below
    ``threshold`` (values that a dichromat effectively cannot tell apart at
    this distance). The normal-vision ΔE is reported alongside for context.
    """
    if threshold < 0:
        raise ValueError("threshold must be >= 0")
    for cond in conditions:
        if cond not in CONDITIONS:
            raise ValueError(f"unknown condition {cond!r}")

    pairs = []
    for i in range(len(colors)):
        for j in range(i + 1, len(colors)):
            a, b = colors[i], colors[j]
            de_normal = delta_e76(rgb_to_lab(a.rgb), rgb_to_lab(b.rgb))
            per_cond = {
                cond: delta_e76(
                    rgb_to_lab(simulate_rgb(a.rgb, cond, severity)),
                    rgb_to_lab(simulate_rgb(b.rgb, cond, severity)),
                )
                for cond in conditions
            }
            pairs.append({"a": a.name, "b": b.name,
                          "a_hex": a.hex, "b_hex": b.hex,
                          "de_normal": round(de_normal, 2),
                          "de": {c: round(v, 2) for c, v in per_cond.items()}})

    report: dict[str, Any] = {
        "tool": "chromashift",
        "threshold": threshold,
        "severity": severity,
        "colors": [{"name": c.name, "hex": c.hex} for c in colors],
        "pair_count": len(pairs),
        "conditions": {},
        "flagged_total": 0,
        "verdict": "PASS",
    }
    flagged_total = 0
    for cond in conditions:
        flagged = []
        for pair in pairs:
            de = pair["de"][cond]
            if de < threshold:
                flagged.append({
                    "a": pair["a"], "b": pair["b"],
                    "a_hex": pair["a_hex"], "b_hex": pair["b_hex"],
                    "de_normal": pair["de_normal"], "de_cvd": de,
                })
        flagged.sort(key=lambda row: row["de_cvd"])
        flagged_total += len(flagged)
        report["conditions"][cond] = {
            "flagged_count": len(flagged),
            "flagged": flagged,
        }
    report["flagged_total"] = flagged_total
    if flagged_total:
        report["verdict"] = "FAIL"
    return report


def render_text(report: dict[str, Any]) -> str:
    """Human-readable palette report."""
    lines = [
        "chromashift — palette CVD report",
        f"colors: {len(report['colors'])}   pairs compared: {report['pair_count']}",
        f"severity: {report['severity']}   confusable threshold: ΔE76 < {report['threshold']}",
        "",
    ]
    for cond, data in report["conditions"].items():
        lines.append(f"[{cond}] flagged {data['flagged_count']}")
        for row in data["flagged"]:
            lines.append(
                f"  {row['de_cvd']:6.2f}  {row['a']} ({row['a_hex']}) ~ "
                f"{row['b']} ({row['b_hex']})   normal ΔE {row['de_normal']:.2f}"
            )
        if not data["flagged"]:
            lines.append("  (none)")
        lines.append("")
    lines.append(f"verdict: {report['verdict']}  (flagged pairs total: {report['flagged_total']})")
    return "\n".join(lines) + "\n"


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2) + "\n"

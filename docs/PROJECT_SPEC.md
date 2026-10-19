# PROJECT SPEC — chromashift

- **Name:** chromashift
- **Category:** accessibility (color-vision-inclusive design)
- **Date:** 2026-10-19

## Target user

A visual/UI designer or frontend developer who must ship colors (charts, badges,
status indicators, palettes) that stay distinguishable for the ~8% of men with
color vision deficiency.

## Problem

Designers with normal vision cannot see what a red/green pairing looks like to
a protanope or deuteranope. Palettes ship, then color-blind users cannot tell
"error" from "success" — and nobody notices until an accessibility audit or an
angry user.

## Solution

An offline CLI that:

1. **simulates** images under the published Machado et al. (2009) CVD matrices
   (protanopia / deuteranopia / tritanopia, severity 0.0–1.0 with the authors'
   table + interpolation) and writes the converted PNGs / side-by-side strips;
2. **generates** a built-in swatch sheet and renders it under every condition
   (`swatches`) — no design assets needed to start;
3. **analyzes** a palette file: transforms every color under each condition and
   flags pairs whose CIE76 ΔE in Lab collapses below a threshold, with a CI
   exit code (`palette`).

PNG decoding/encoding is implemented in-repo on the standard library (zlib +
struct), so the tool has zero dependencies and works fully offline.

## Core workflow

```shell
chromashift simulate shot.png --condition all --out-dir out/
chromashift swatches --out results/swatches.png
chromashift palette examples/ui-palette.txt --threshold 6 --format json
```

## Must-have features

- PNG codec: 8-bit gray/RGB/RGBA/palette, non-interlaced decode; RGBA encode;
  clear errors for unsupported variants (16-bit, Adam7, corrupt CRC).
- Machado et al. (2009) matrices (severity table 0.0–1.0 step 0.1, interpolated
  per the authors' own guidance), linear-blended severity, clamped output.
- sRGB → CIELAB (D65) and ΔE76 for palette pair distances.
- Three subcommands (simulate/swatches/palette), text + JSON reports,
  exit codes 0/1/2 (1 = confusable pairs found).

## Stack

Python 3.10+ standard library only; unittest.

## Test strategy

Hand-crafted PNG fixtures per color type and filter type, matrix landmark
checks (pure channels, severity 0 = identity), Lab reference values (white,
black, pure red), threshold/gate tests, subprocess CLI e2e.

## Demo/result strategy

`python examples/demo.py` generates the swatch sheet, simulates all three
conditions, writes a side-by-side strip, and runs palette analysis on
`examples/ui-palette.txt` → `results/*.png` + `results/palette-report.{txt,json}`.

## Safety considerations

Fully offline; only reads paths the user passes; images contain no code.

## Definition of done

Tests green, demo artifacts regenerate, README commands verified, no secrets,
published to GitHub.

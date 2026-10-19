# chromashift

**See your colors the way a color-blind person sees them — offline, from the terminal.**

## The problem

Roughly 1 in 12 men and 1 in 200 women has a color vision deficiency (CVD).
Designers with normal vision cannot *see* what their red/green status pairing
looks like to a deuteranope — so "error" and "success" ship as the same muddy
brown, charts lose their series, and the accessibility audit catches it late.

Real measurements from this repo's own example palette: `#d32f2f` vs `#2e7d32`
are **ΔE76 ≈ 102.8** apart for normal vision and **ΔE76 ≈ 2.8** under
deuteranopia — effectively one color.

## Key features

- **Image simulation** — `simulate` renders any PNG under protanopia,
  deuteranopia or tritanopia, plus side-by-side comparison strips.
- **Grounded color science** — the pre-computed simulation matrices from
  Machado, Oliveira & Fernandes (2009), *IEEE TVCG* 15(6):1291–1298
  (Table 1, severity 0.0–1.0 step 0.1, interpolated exactly the way the
  authors recommend). Severity 0 is identity by construction.
- **Palette gate** — `palette` parses a plain-text palette, transforms every
  color under each condition, flags pairs whose CIELAB ΔE76 collapses below a
  threshold, and **exits 1** so CI can block the PR.
- **Zero dependencies** — PNG codec (gray/RGB/RGBA/palette, 8-bit) implemented
  in-repo on `zlib`/`struct`; sRGB→Lab in ~30 lines. Python stdlib only.
- **Generated assets** — `swatches` renders a built-in 24-color UI sheet so you
  can start without any design files.

## Example output

```
$ chromashift palette examples/ui-palette.txt --threshold 6
chromashift — palette CVD report
colors: 5   pairs compared: 10
severity: 1.0   confusable threshold: ΔE76 < 6.0

[protanopia] flagged 0
  (none)

[deuteranopia] flagged 1
    2.80  error (#d32f2f) ~ success (#2e7d32)   normal ΔE 102.82

[tritanopia] flagged 0
  (none)

verdict: FAIL  (flagged pairs total: 1)
```

Exit code 1. Swap in `examples/safe-palette.txt` and the same command exits 0.

Generated artifacts live in [`results/`](results/): `swatches.png`,
`swatches-strip.png` (original + 3 conditions), `simulate-strip.png`,
`sim/*.png`, `ui-palette-grid.png`, and the palette reports.

## Architecture

```
simulate:  PNG decode → per-pixel 3×3 matrix (Machado 2009) → PNG encode
palette:   parse palette → RGB→Lab (D65) → ΔE76 per pair, normal + simulated
             → flagged pairs sorted worst-first → verdict + exit code
swatches:  built-in color table → grid renderer → same simulate/encode path
```

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Requirements

- Python 3.10+ (standard library only); no network access needed

## Installation

```shell
python -m pip install .
# or run from a checkout without installing
PYTHONPATH=src python -m chromashift --help
```

## Quick start

```shell
chromashift swatches --out swatches.png --strip compare.png   # see the built-in sheet
chromashift simulate photo.png -c all --strip before-after.png
chromashift palette my-palette.txt --threshold 6              # exit 1 = fix your palette
```

## Usage

```shell
chromashift simulate shot.png                      # all 3 conditions, next to input
chromashift simulate shot.png -c protanopia --severity 0.6 --out-dir out/
chromashift swatches --columns 6
chromashift palette brand.txt --format json --threshold 8
chromashift palette brand.txt --swatch grid.png    # palette rows per condition
chromashift --version
```

Full flags and recipes: [docs/USAGE.md](docs/USAGE.md).

## Configuration

Flags only: `--condition` (repeatable, `all`), `--severity` (0–1),
`--threshold` (ΔE76, default 6.0), `--format text|json`, `--out/--strip/--swatch`.

## Testing

```shell
python -m unittest discover -s tests -t .
python examples/demo.py
```

79 tests: PNG round-trips and every scanline filter by hand-computed values,
rejection of 16-bit/interlaced/corrupt PNGs, matrix transcription checks
against Table 1, Lab reference values (white/black/sRGB red), palette
threshold/gate behavior, and subprocess CLI e2e for every exit code.

## Project structure

```
chromashift/
├─ src/chromashift/
│  ├─ png.py        # dependency-free PNG codec
│  ├─ cvd.py        # Machado 2009 matrices + image transform
│  ├─ color.py      # hex parsing, sRGB→CIELAB, ΔE76
│  ├─ palette.py    # palette parse + confusable-pair analysis
│  ├─ swatch.py     # built-in swatch sheet + grid renderer
│  └─ cli.py        # simulate / swatches / palette, exit codes 0/1/2
├─ tests/           # 79 unittest tests
├─ examples/        # demo.py, ui-palette.txt, safe-palette.txt
├─ results/         # generated demo artifacts (PNGs + reports)
└─ docs/            # PROJECT_SPEC, ARCHITECTURE, USAGE
```

## Limitations

- Matrices apply to gamma-encoded sRGB directly (as the authors' reference
  tool does); a CIECAM02-grade appearance model would be more precise.
- ΔE76 is the simplest perceptual distance; ΔE2000 is kinder to blue hues.
- PNG decode supports 8-bit non-interlaced gray/RGB/RGBA/palette only —
  16-bit and Adam7 files are rejected with a clear message, not guessed.
- Tritanopia/tritanomaly modeling is noted as approximate by the original
  paper (severity tables exist but the model intentionally bounds itself).
- Severity interpolation uses the authors' 0.1-grid fast approximation
  instead of re-deriving the model's equations.

## Roadmap

- ΔE2000 option and a perceptual "swatch distance" table
- SVG/HTML report with color chips for design docs
- Daltonize (color-remapping) output, not just simulation
- Batch mode over a directory of images

## Security notes

Fully offline: reads only the paths you pass, writes only to the outputs you
request, and decodes PNG data with bounded allocation — no image can execute
anything. Palette files are plain text; no credentials are read or written.

## License

MIT — see [LICENSE](LICENSE).

## References

- Machado, G. M., Oliveira, M. M., Fernandes, L. A. F. (2009). *A
  Physiologically-based Model for Simulation of Color Vision Deficiency.*
  IEEE TVCG 15(6), 1291–1298. DOI: 10.1109/TVCG.2009.113 — matrix table:
  <https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html>

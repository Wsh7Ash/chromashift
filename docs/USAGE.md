# Usage

## Synopsis

```
chromashift simulate IMAGE [flags]
chromashift swatches    [flags]
chromashift palette     PALETTE_FILE [flags]
```

## Exit codes

| code | meaning |
|---|---|
| 0 | success (palette verdict PASS) |
| 1 | palette verdict FAIL — at least one pair below `--threshold` |
| 2 | usage or input error (bad PNG, bad color, unknown flag value) |

## Commands

### simulate — render an image under a vision condition

```shell
chromashift simulate shot.png
chromashift simulate shot.png -c protanopia -c tritanopia
chromashift simulate shot.png -c all --severity 0.6 --out-dir out/
chromashift simulate shot.png --strip compare.png
```

Outputs one PNG per condition as `<stem>.<condition>.png` (default: alongside
the input, override with `--out-dir`). `--strip` writes
original | simulated | … side by side (8 px white divider).

Input must be an 8-bit non-interlaced PNG (gray, RGB, RGBA or palette);
anything else exits 2 with a message saying how to re-export.

### swatches — the built-in sheet

```shell
chromashift swatches                       # writes ./swatches.png
chromashift swatches --out sheet.png --strip sheet-cvd.png
chromashift swatches --columns 6 --severity 0.8 -c deuteranopia
```

24 built-in colors (8 per row by default) — status pair, categorical series,
neutrals — authored in `swatch.py`.

### palette — the CI gate

```shell
chromashift palette brand.txt --threshold 6
chromashift palette brand.txt --format json > report.json
chromashift palette brand.txt --swatch grid.png
```

Palette file format — one color per line, optional name before or after the
hex, `//` comments on their own line:

```
error   #d32f2f
success #2e7d32
#1565c0 info
```

A line starting with `#` that is not a valid color is an error (line number
reported) — typos must not pass silently.

A pair is **flagged** for a condition when its simulated ΔE76 falls below
`--threshold` (default 6.0). Flagged pairs are listed worst-first per
condition with the normal-vision ΔE alongside.

## Flags

| Flag | Default | Meaning |
|---|---|---|
| `-c/--condition` | all | `protanopia\|deuteranopia\|tritanopia\|all`, repeatable or comma-separated |
| `--severity` | 1.0 | 0.0 (normal) … 1.0 (full dichromacy), interpolated on the published 0.1 grid |
| `--threshold` | 6.0 | palette only: flag pairs with simulated ΔE76 below this |
| `--format` | text | palette only: `text` or `json` |
| `--out` / `--strip` / `--swatch` / `--out-dir` | – | output paths per command |
| `--columns` | 8 | swatches only: colors per row |
| `--version` | – | print version and exit |

## Recipes

**Block an inaccessible palette in CI:**

```yaml
- name: Palette is CVD-safe
  run: python -m chromashift palette design/status-colors.txt --threshold 6
```

**Review a screenshot before/after:**

```shell
chromashift simulate dashboard.png -c all --strip cvd-review.png
```

**Milder deficiency (weak red-green):**

```shell
chromashift simulate shot.png -c protanopia --severity 0.4
```

**Machine-readable audit:**

```shell
chromashift palette brand.txt --format json --threshold 6 | jq .verdict
```

## JSON shape (palette)

```json
{
  "tool": "chromashift",
  "threshold": 6.0,
  "severity": 1.0,
  "colors": [{"name": "error", "hex": "#d32f2f"}, "..."],
  "pair_count": 10,
  "conditions": {
    "deuteranopia": {
      "flagged_count": 1,
      "flagged": [
        {"a": "error", "b": "success", "a_hex": "#d32f2f",
         "b_hex": "#2e7d32", "de_normal": 102.82, "de_cvd": 2.8}
      ]
    }
  },
  "flagged_total": 1,
  "verdict": "FAIL"
}
```

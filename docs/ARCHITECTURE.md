# Architecture

## Design goals

1. Grounded color science — published matrices, reference-tested Lab math,
   no invented numbers.
2. Zero dependencies — PNG codec and color math implemented in-repo.
3. Honest failures — unsupported inputs are rejected with actionable messages
   instead of being half-decoded.
4. Deterministic artifacts — the same input always produces byte-identical
   PNGs and reports.

## Pipeline

```
simulate IMAGE
   │
   ▼
png.decode            signature → chunk walk (CRC verified) → IHDR policy checks
   │                  (8-bit, non-interlaced, known color type) → inflate
   │                  → unfilter (None/Sub/Up/Average/Paeth) → RGBA expansion
   ▼
cvd.simulate_image    per-pixel 3×3 matrix (Machado et al. 2009 Table 1),
   │                  clamp [0,255], alpha copied
   ▼
png.encode            RGBA8, filter-0 scanlines, single IDAT → output

palette FILE
   │
   ▼
palette.parse         line-based: optional name + hex; `//` comments;
   │                  `#`-lines that are not colors are hard errors
   ▼
analyze               all pairs → Lab(D65) → ΔE76 normal
   │                  + simulate_rgb per condition → ΔE76 simulated
   │                  → flagged when simulated ΔE < threshold
   ▼
render text/JSON      verdict PASS/FAIL → exit 0/1 (2 for input errors)
```

## Key decisions

### Why implement a PNG codec

The tool must run offline with no dependencies, and image round-tripping is
exactly testable: every color type and every filter type has a hand-computed
fixture. Unsupported variants (16-bit, Adam7, unknown color types, corrupt
CRCs) raise `PNGError` with a message telling the user how to re-export —
chromashift never silently misreads pixels.

Encoder output is always RGBA8/filter-0: maximally compatible, trivially
verifiable by re-decoding (the test suite round-trips everything).

### The CVD model

`cvd.py` embeds the 11×3 matrices of Table 1 from Machado et al. (2009)
(severities 0.0–1.0 in 0.1 steps for protanomaly/deuteranomaly/tritanomaly):

- severity 0.0 is the identity, so `--severity 0` is a guaranteed no-op;
- intermediate severities linearly interpolate adjacent published rows — the
  "fast approximation" the authors themselves document for the 0.1 grid;
- the matrix multiplies the gamma-encoded RGB triple directly (the reference
  implementation's behavior) and clamps to [0, 255].

Transcription is pinned by tests against the published table values.

### Distance metric

CIELAB (D65) with Euclidean ΔE76. Reference values (white → L\*100, black →
L\*0, sRGB red → 53.24/80.09/67.20) are asserted in tests, so a regression in
the color pipeline cannot hide.

### Exit-code contract

| code | meaning |
|---|---|
| 0 | command succeeded; palette verdict PASS |
| 1 | palette verdict FAIL (≥1 pair below threshold) |
| 2 | usage/input error (bad PNG, bad hex, unknown flag value, missing file) |

`Δ` in reports means stdout/stderr are reconfigured to UTF-8 — Windows'
locale encodings (cp1252) cannot encode it.

### Asset generation

There are no binary fixtures in the repo: `swatch.py` authors the built-in
24-color sheet in code, and tests build PNGs with the package's own encoder
plus hand-crafted bytes for the filter/rejection paths. `results/` holds only
regenerable demo output (`python examples/demo.py`).

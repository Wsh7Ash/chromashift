# Results

Honest record of what was actually executed for chromashift on 2026-10-19.

## Environment

- OS: Windows 11 (MINGW64_NT-10.0-19044, x86_64), MSYS2 MinGW shell
- Runtime: Python 3.14.3 (project venv `.venv/`), pip 25.3
- Dependency manager: pip (`python -m venv .venv` + `.venv/bin/python -m pip install .`)
- Network: needed once during development to fetch the published Machado et al.
  (2009) Table 1 matrix values from the authors' page (cited in `cvd.py`);
  the tool itself performs no network I/O.

## Validation performed

| Gate | Result | Evidence |
|---|---|---|
| install | **PASS** | venv + `pip install .` → exit 0; `.venv/bin/chromashift --version` → `chromashift 0.1.0` (system MSYS pip is PEP-668 managed, hence the venv) |
| build | N/A | pure Python, no build step |
| byte-compile | **PASS** | `python -m compileall -q src` → exit 0 |
| unit tests | **PASS** | `python -m unittest discover -s tests -t .` → `Ran 79 tests … OK`, exit 0 |
| integration tests | **PASS** | included in the 79: subprocess CLI e2e for all three subcommands and all exit codes 0/1/2 |
| lint | N/A | no linter configured for this repo |
| type check | N/A | no type checker configured; annotations present but not mypy-verified |
| demo run | **PASS** | `python examples/demo.py` → 16/16 `[ok]` lines, `demo result: ALL-OK`, exit 0 |
| README commands | **PASS** | `chromashift --version` and `chromashift swatches --out …` run against the installed console script, exit 0 |
| secret scan | **PASS** | grep for `ghp_`/`github_pat_`/`AKIA…`/`sk-…`/private-key headers (excluding `.venv`, `.git`) → no matches |

## Commands executed

```shell
python -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/chromashift --version                 # chromashift 0.1.0
.venv/bin/chromashift swatches --out /tmp/cs-sw.png   # exit 0
python -m compileall -q src                     # exit 0
python -m unittest discover -s tests -t .       # 79 tests, OK, exit 0
python examples/demo.py                         # ALL-OK, exit 0
grep -rIlE '(ghp_|github_pat_|AKIA…|sk-…|BEGIN … PRIVATE KEY)' …   # exit 1 = clean
```

## Observed result

`python examples/demo.py` (deterministic):

```
[ok] swatches --out results/swatches.png --strip results/swatches-strip.png -> exit 0
[ok] simulate results/swatches.png --out-dir results/sim --strip results/simulate-strip.png -> exit 0
[ok] palette examples/ui-palette.txt --threshold 6 --format json --swatch … -> exit 1
[ok] palette examples/ui-palette.txt --threshold 6 -> exit 1
[ok] palette examples/safe-palette.txt --threshold 6 -> exit 0
[ok] simulate results/not-a-png.txt -> exit 2
[ok] all 7 PNG artifacts decode (348x128 / 1416x128 / 216x172)
[ok] ui-palette verdict FAIL (flagged 1)
[info] worst simulated pair ΔE76 = 2.8
demo result: ALL-OK
```

Measured numbers: `error #d32f2f` vs `success #2e7d32` are ΔE76 102.82 for
normal vision and **2.80 under deuteranopia** — flagged at the default
threshold of 6.0; the safe example palette's worst simulated pair is 7.96 and
passes.

## Generated artifacts

- `results/swatches.png` — built-in 24-color swatch sheet (348×128)
- `results/swatches-strip.png` — sheet + protanopia + deuteranopia + tritanopia (1416×128)
- `results/sim/simulates…` → `results/sim/swatches.{protanopia,deuteranopia,tritanopia}.png`
- `results/simulate-strip.png` — `simulate --strip` output on the sheet
- `results/ui-palette-grid.png` — example palette rows under each condition (216×172)
- `results/palette-report.txt` / `palette-report.json` — FAIL report for `ui-palette.txt`
- `results/palette-safe-report.txt` — PASS report for `safe-palette.txt`
- `results/not-a-png.txt` — deliberate bad input proving the exit-2 path

Regenerate with `python examples/demo.py`.

## Defects found and fixed during validation

1. **Windows encoding crash** — the report's `Δ` (U+0394) could not be encoded
   by the console's cp1252; `UnicodeEncodeError` (a `ValueError`) was caught by
   the CLI's error handler and mis-reported as exit 2. Fixed by reconfiguring
   stdout/stderr to UTF-8 in `cli.main()` and in the demo, guarded for streams
   without `reconfigure`.
2. **Wrong test expectations for PNG filters** — the Average and Paeth fixtures
   were hand-computed incorrectly (the tests disagreed with the code, which
   follows the PNG spec: Average uses the already-reconstructed left byte, and
   Paeth's `c` is the prior row's left byte). Corrected the expected values
   after re-deriving them; the implementation was not changed.

## Known limitations

- Matrices multiply gamma-encoded sRGB directly (the reference tool's
  behavior), not a full color-appearance model.
- ΔE76 only (ΔE2000 not implemented) — blue-hue distances are the weak point.
- PNG decode: 8-bit, non-interlaced gray/RGB/RGBA/palette only; 16-bit and
  Adam7 are rejected with actionable errors.
- Tritanomaly/tritanopia severity modeling is noted as approximate by the
  original paper.
- Local run used Python 3.14.3; CI covers 3.10–3.13. No linter/type checker
  configured.

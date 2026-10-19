# Contributing to chromashift

Thanks for considering a contribution.

## Development setup

```shell
git clone https://github.com/Wsh7Ash/chromashift.git
cd chromashift
python -m unittest discover -s tests -t .
python examples/demo.py
```

No dependencies to install; the package runs from `src/` via `PYTHONPATH`
(or `pip install -e .` if you prefer the console script).

## Ground rules

1. **Numbers must be sourced.** CVD matrices come from published tables — cite
   table/DOI in the docstring and pin them with a test. No invented color math.
2. **Lab reference tests stay.** If you touch `color.py`, keep the white /
   black / sRGB-red reference assertions passing.
3. **Reject, never guess.** Unsupported inputs raise `PNGError`/
   `PaletteError` with actionable messages and exit 2.
4. **Zero runtime dependencies.**
5. **No fabricated results** — `results/` only via `python examples/demo.py`.

## Workflow

1. Open an issue describing the bug or idea.
2. Branch from `main`: `git checkout -b fix/short-description`.
3. Add tests alongside the change (hand-computed fixtures for codec work).
4. `python -m unittest discover -s tests -t .` and `python examples/demo.py`
5. Update `CHANGELOG.md` and docs if behavior changed.
6. Open a pull request; CI runs the suite + demo on Python 3.10–3.13.

## Reporting bugs

Include your Python version, the exact command, an input file that reproduces
the problem (never real confidential images or brand palettes), and the full
output. For color-math issues, state the expected vs actual ΔE or Lab values
and their source.

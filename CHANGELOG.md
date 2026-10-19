# Changelog

All notable changes to chromashift are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/).

## [0.1.0] — 2026-10-19

### Added
- Dependency-free PNG codec: decode (8-bit gray/RGB/RGBA/palette, filters
  0–4, CRC verification) and RGBA encode; clear errors for 16-bit / Adam7 /
  corrupt files.
- CVD simulation from Machado, Oliveira & Fernandes (2009) Table 1:
  protanopia / deuteranopia / tritanopia, severity 0.0–1.0 with published
  0.1-grid rows and linear interpolation; severity 0 = identity.
- `simulate` subcommand: per-condition PNGs + side-by-side strips.
- `swatches` subcommand: generated 24-color UI sheet + CVD strip.
- `palette` subcommand: palette file parsing, all-pairs ΔE76 (normal +
  simulated), confusable-pair flags, text/JSON reports, swatch grid,
  CI gate exit codes 0/1/2.
- sRGB → CIELAB (D65) conversion with reference-value tests.
- 79-test suite; `examples/demo.py` producing regenerable `results/` artifacts.
- UTF-8 reconfiguration of stdout/stderr so `Δ` survives Windows consoles.

#!/usr/bin/env python3
"""Deterministic demo: swatches, image simulation, palette gate.

Usage:  python examples/demo.py
Expects: ui-palette FAILs and safe-palette PASSes at threshold 6.0.
Exit 0 only when every step produced its expected exit code and artifacts.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
RESULTS = os.path.join(ROOT, "results")
EXAMPLES = os.path.join(ROOT, "examples")


def run(*args, expect):
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run([sys.executable, "-m", "chromashift", *args],
                          capture_output=True, text=True, env=env, cwd=ROOT,
                          encoding="utf-8", errors="replace")
    ok = proc.returncode == expect
    print(f"[{'ok' if ok else 'bad'}] {' '.join(args)} -> exit {proc.returncode} "
          f"(want {expect})")
    if not ok:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
    return ok and proc


def main() -> int:
    # Reports contain Δ; Windows console encodings may not encode it.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass
    os.makedirs(RESULTS, exist_ok=True)
    swatches = os.path.join(RESULTS, "swatches.png")
    strip = os.path.join(RESULTS, "swatches-strip.png")
    compare = os.path.join(RESULTS, "simulate-strip.png")
    report_txt = os.path.join(RESULTS, "palette-report.txt")
    report_json = os.path.join(RESULTS, "palette-report.json")
    report_safe = os.path.join(RESULTS, "palette-safe-report.txt")
    ui_swatch = os.path.join(RESULTS, "ui-palette-grid.png")
    bad_png = os.path.join(RESULTS, "not-a-png.txt")

    with open(bad_png, "w", encoding="utf-8") as fh:
        fh.write("deliberately not a PNG, to demonstrate the exit-2 path\n")

    ok = True
    ok &= bool(run("swatches", "--out", swatches, "--strip", strip, expect=0))
    ok &= bool(run("simulate", swatches, "--out-dir", os.path.join(RESULTS, "sim"),
                   "--strip", compare, expect=0))
    # Palette gate: the red/green status pair collapses under deuteranopia.
    p_fail = run("palette", os.path.join(EXAMPLES, "ui-palette.txt"),
                 "--threshold", "6", "--format", "json",
                 "--swatch", ui_swatch, expect=1)
    if p_fail:
        with open(report_json, "w", encoding="utf-8") as fh:
            fh.write(p_fail.stdout)
        # Text version of the same run (without --format json).
        t_fail = run("palette", os.path.join(EXAMPLES, "ui-palette.txt"),
                     "--threshold", "6", expect=1)
        if t_fail:
            with open(report_txt, "w", encoding="utf-8") as fh:
                fh.write(t_fail.stdout)
        else:
            ok = False
    else:
        ok = False

    p_safe = run("palette", os.path.join(EXAMPLES, "safe-palette.txt"),
                 "--threshold", "6", expect=0)
    if p_safe:
        with open(report_safe, "w", encoding="utf-8") as fh:
            fh.write(p_safe.stdout)
    else:
        ok = False

    # Bad input must exit 2 and never claim success.
    ok &= bool(run("simulate", bad_png, expect=2))

    # Verify every artifact decodes as a PNG.
    sys.path.insert(0, SRC)
    from chromashift.png import decode_file, PNGError
    artifacts = [swatches, strip, compare, ui_swatch,
                 os.path.join(RESULTS, "sim", "swatches.protanopia.png"),
                 os.path.join(RESULTS, "sim", "swatches.deuteranopia.png"),
                 os.path.join(RESULTS, "sim", "swatches.tritanopia.png")]
    for path in artifacts:
        if not os.path.exists(path):
            print(f"[bad] missing artifact {path}")
            ok = False
            continue
        try:
            img = decode_file(path)
            print(f"[ok] {os.path.relpath(path, ROOT)} decodes "
                  f"({img.width}x{img.height})")
        except PNGError as exc:
            print(f"[bad] {path}: {exc}")
            ok = False

    if os.path.exists(report_json):
        payload = json.load(open(report_json, encoding="utf-8"))
        print(f"[{'ok' if payload['verdict'] == 'FAIL' else 'bad'}] "
              f"ui-palette verdict {payload['verdict']} "
              f"(flagged {payload['flagged_total']})")
        worst = min(
            (row["de_cvd"] for c in payload["conditions"].values()
             for row in c["flagged"]), default=None)
        print(f"[info] worst simulated pair ΔE76 = {worst}")

    print(f"demo result: {'ALL-OK' if ok else 'FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

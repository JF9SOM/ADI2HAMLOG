"""Command line interface: adi2hamlog input.adi -o out.csv --tz jst"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .adif import parse_file
from .config import load_config
from .convert import Options, convert_all
from .writer import write_csv


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="adi2hamlog", description="Convert an ADIF log to a Turbo HAMLOG CSV.")
    p.add_argument("input", type=Path, help="input ADIF file (.adi)")
    p.add_argument("-o", "--output", type=Path, help="output CSV (default: input name with .csv)")
    p.add_argument("--tz", choices=["mixed", "jst", "utc"], default="mixed",
                   help="mixed: domestic JST(J)/foreign UTC(U) [default]; jst: all JST; utc: all UTC")
    p.add_argument("-c", "--config", type=Path, help="JSON config overriding the defaults")
    sat = p.add_mutually_exclusive_group()
    sat.add_argument("--sat-remarks", dest="sat_remarks", action="store_true", default=None,
                     help="put the satellite name in Remarks")
    sat.add_argument("--no-sat-remarks", dest="sat_remarks", action="store_false")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    out = args.output or args.input.with_suffix(".csv")
    try:
        cfg = load_config(args.config)
        parsed = parse_file(args.input)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    rows, messages = convert_all(parsed.records, cfg, Options(tz=args.tz, sat_remarks=args.sat_remarks))
    if not rows:
        print(f"error: no QSO could be converted ({len(parsed.records)} record(s) read); nothing written",
              file=sys.stderr)
        for m in parsed.warnings + messages:
            print(f"warning: {m}", file=sys.stderr)
        return 1
    try:
        enc_warnings = write_csv(out, rows)
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    for m in parsed.warnings + messages + enc_warnings:
        print(f"warning: {m}", file=sys.stderr)
    skipped = len(parsed.records) - len(rows)
    print(f"{len(rows)} QSO written to {out}" + (f" ({skipped} skipped)" if skipped else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

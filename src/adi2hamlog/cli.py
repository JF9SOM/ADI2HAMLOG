"""Command line interface: adi2hamlog input.adi -o out.csv --tz jst"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import load_config
from .convert import Options
from .service import convert_file


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
    p.add_argument("--sat-freq", choices=["mhz", "band"], default=None,
                   help="satellite Freq column: mhz = 145/435, band = V/U (default: from config, mhz)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cfg = load_config(args.config)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    res = convert_file(args.input, args.output, cfg, Options(tz=args.tz, sat_remarks=args.sat_remarks, sat_freq=args.sat_freq))
    for m in res.warnings:
        print(f"warning: {m}", file=sys.stderr)
    if res.error:
        print(f"error: {res.error}", file=sys.stderr)
        return 2 if res.io_error else 1
    print(f"{res.written} QSO written to {res.output}" + (f" ({res.skipped} skipped)" if res.skipped else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

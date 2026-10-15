"""High-level conversion shared by the CLI and the GUI (no I/O to the console)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .adif import parse_file
from .convert import Options, convert_all
from .writer import write_csv


@dataclass
class Result:
    read: int = 0                 # QSO records found in the ADIF
    written: int = 0              # rows written
    output: Path | None = None
    warnings: list[str] = field(default_factory=list)
    error: str | None = None      # set when nothing was written
    io_error: bool = False        # the error was reading/writing a file (not bad data)

    @property
    def skipped(self) -> int:
        return self.read - self.written


def default_output(input_path) -> Path:
    return Path(input_path).with_suffix(".csv")


def convert_file(input_path, output_path=None, cfg: dict | None = None, opts: Options | None = None) -> Result:
    """Convert one ADIF file. Never raises for bad data or I/O: problems end up in Result."""
    from .config import load_config

    res = Result()
    out = Path(output_path) if output_path else default_output(input_path)
    try:
        cfg = cfg if cfg is not None else load_config()
        parsed = parse_file(input_path)
    except (OSError, ValueError) as e:
        res.error, res.io_error = str(e), True
        return res
    res.read = len(parsed.records)
    rows, messages = convert_all(parsed.records, cfg, opts)
    res.warnings = parsed.warnings + messages
    if not rows:
        res.error = f"no QSO could be converted ({res.read} record(s) read); nothing written"
        return res
    try:
        res.warnings += write_csv(out, rows)
    except OSError as e:
        res.error, res.io_error = str(e), True
        return res
    res.written, res.output = len(rows), out
    return res

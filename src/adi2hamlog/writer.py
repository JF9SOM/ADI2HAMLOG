"""CSV output: cp932, CRLF, no header. Characters cp932 cannot encode are replaced and reported."""

from __future__ import annotations

from .columns import ENCODING, NEWLINE, QUOTE_ALL

REPLACEMENT = "?"


def _field(value: str) -> str:
    if QUOTE_ALL or any(c in value for c in ',"\r\n'):
        return '"' + value.replace('"', '""') + '"'
    return value


def encode_rows(rows) -> tuple[bytes, list[str]]:
    """Return (csv bytes, warnings). One warning per row containing replaced characters."""
    lines: list[str] = []
    warnings: list[str] = []
    for n, row in enumerate(rows, 1):
        fixed: list[str] = []
        replaced: list[str] = []
        for v in row:
            out = []
            for ch in v:
                try:
                    ch.encode(ENCODING)
                    out.append(ch)
                except UnicodeEncodeError:
                    out.append(REPLACEMENT)
                    replaced.append(ch)
            fixed.append("".join(out))
        if replaced:
            warnings.append(
                f"row {n} ({row[0]}): {len(replaced)} character(s) not representable in {ENCODING} "
                f"replaced with {REPLACEMENT!r}: {''.join(replaced)}"
            )
        lines.append(",".join(_field(v) for v in fixed))
    text = "".join(line + NEWLINE for line in lines)
    return text.encode(ENCODING), warnings


def write_csv(path, rows) -> list[str]:
    data, warnings = encode_rows(rows)
    with open(path, "wb") as f:
        f.write(data)
    return warnings

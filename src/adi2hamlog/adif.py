"""ADIF reader (stdlib only).

Handles <FIELD:len[:type]>value tags, <EOH>/<EOR>, case-insensitive names.
ADIF defines len in bytes, but some exporters (e.g. Wavelog) count characters
for multi-byte text, so both are tried (bytes first, then characters).
Problems never abort parsing; they are collected in ParseResult.warnings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_TAG = re.compile(r"<([^<>:\s]+)(?::(\d+))?(?::[^<>]*)?>")


@dataclass
class ParseResult:
    records: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def decode_bytes(data: bytes) -> str:
    """Decode an ADIF file: UTF-8 (BOM tolerated) first, then cp932."""
    for enc in ("utf-8-sig", "cp932"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _boundary_ok(text: str, pos: int) -> bool:
    """A value must be followed by optional whitespace and then '<' or EOF."""
    nxt = text.find("<", pos)
    return text[pos:].strip() == "" if nxt < 0 else text[pos:nxt].strip() == ""


def _take_value(text: str, pos: int, length: int) -> tuple[str, int] | None:
    """Return (value, end_pos) for a declared length, or None if inconsistent."""
    # 1) length in bytes (ADIF spec)
    rest = text[pos:].encode("utf-8")
    chunk = rest[:length]
    try:
        value = chunk.decode("utf-8")
    except UnicodeDecodeError:
        value = None
    if value is not None:
        end = pos + len(value)
        if len(chunk) == length and _boundary_ok(text, end):
            return value, end
    # 2) length in characters (Wavelog etc.)
    end = pos + length
    if end <= len(text) and _boundary_ok(text, end):
        return text[pos:end], end
    return None


def parse_text(text: str) -> ParseResult:
    result = ParseResult()
    pos = 0
    m = re.search(r"<eoh>", text, re.IGNORECASE)
    if m:
        pos = m.end()

    current: dict[str, str] = {}
    n = len(text)
    while pos < n:
        lt = text.find("<", pos)
        if lt < 0:
            break
        m = _TAG.match(text, lt)
        if not m:
            result.warnings.append(f"offset {lt}: malformed tag, skipped")
            pos = lt + 1
            continue
        name = m.group(1).upper()
        pos = m.end()
        if name == "EOR":
            if current:
                result.records.append(current)
            current = {}
            continue
        if name == "EOH":
            continue
        if m.group(2) is None:
            result.warnings.append(f"offset {lt}: tag <{name}> has no length, ignored")
            continue
        length = int(m.group(2))
        got = _take_value(text, pos, length)
        if got is None:
            nxt = text.find("<", pos)
            nxt = n if nxt < 0 else nxt
            value, end = text[pos:nxt].strip(), nxt
            result.warnings.append(
                f"record {len(result.records) + 1}: <{name}:{length}> length does not match; "
                f"used text up to next tag"
            )
        else:
            value, end = got
        current[name] = value
        pos = end

    if current:
        result.records.append(current)
        result.warnings.append("last record has no <EOR>; kept")
    return result


def parse_file(path) -> ParseResult:
    with open(path, "rb") as f:
        return parse_text(decode_bytes(f.read()))

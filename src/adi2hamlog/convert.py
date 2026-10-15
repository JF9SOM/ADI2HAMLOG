"""QSO (ADIF record) -> HAMLOG CSV row. Rules and their verification status: CLAUDE.md section 5."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import ROUND_DOWN, Decimal, InvalidOperation

from .columns import KEYS

JST = timedelta(hours=9)
_JA_PREFIX = re.compile(r"^(J[A-S]|7[J-N]|8[J-N])", re.IGNORECASE)


class ConvertError(Exception):
    """The QSO cannot be converted at all (it is skipped and reported)."""


@dataclass
class Options:
    tz: str = "mixed"  # mixed: domestic JST(J) / foreign UTC(U); jst: all J; utc: all U
    sat_remarks: bool | None = None  # None = use config

    def __post_init__(self):
        if self.tz not in ("mixed", "jst", "utc"):
            raise ValueError(f"tz must be mixed/jst/utc, got {self.tz!r}")


@dataclass
class Converted:
    row: list[str]
    warnings: list[str] = field(default_factory=list)


def is_domestic(rec: dict, cfg: dict) -> bool:
    dxcc = rec.get("DXCC", "").strip()
    if dxcc:
        return dxcc == cfg["domestic_dxcc"]
    return bool(_JA_PREFIX.match(rec.get("CALL", "")))


def _datetime(rec: dict) -> datetime:
    d, t = rec.get("QSO_DATE", "").strip(), rec.get("TIME_ON", "").strip()
    if not re.fullmatch(r"\d{8}", d):
        raise ConvertError(f"QSO_DATE missing or invalid: {d!r}")
    if not re.fullmatch(r"\d{4}|\d{6}", t):
        raise ConvertError(f"TIME_ON missing or invalid: {t!r}")
    t = t.ljust(6, "0")
    try:
        return datetime.strptime(d + t, "%Y%m%d%H%M%S")
    except ValueError as e:
        raise ConvertError(f"invalid date/time {d} {t}: {e}") from None


def format_mhz(value: str) -> str:
    """MHz truncated to 3 decimals (kHz), trailing zeros removed. Raises ValueError."""
    try:
        d = Decimal(value.strip()).quantize(Decimal("0.001"), rounding=ROUND_DOWN)
    except InvalidOperation:
        raise ValueError(f"not a number: {value!r}") from None
    if d <= 0:
        raise ValueError(f"not positive: {value!r}")
    s = format(d, "f")
    return s.rstrip("0").rstrip(".")


def _sat_band(mhz: str, bands: dict) -> str | None:
    try:
        f = float(mhz)
    except ValueError:
        return None
    for letter, (lo, hi) in bands.items():
        if lo <= f <= hi:
            return letter
    return None


def _freq(rec: dict, cfg: dict, warns: list[str]) -> str:
    sat = rec.get("PROP_MODE", "").upper() == "SAT"
    if sat and rec.get("FREQ") and rec.get("FREQ_RX"):
        up = _sat_band(rec["FREQ"], cfg["satellite"]["bands"])
        down = _sat_band(rec["FREQ_RX"], cfg["satellite"]["bands"])
        if up and down:
            return f"{up}/{down}"
        warns.append(f"satellite bands not recognised (FREQ={rec['FREQ']}, FREQ_RX={rec['FREQ_RX']}); wrote MHz")
    if rec.get("FREQ"):
        try:
            return format_mhz(rec["FREQ"])
        except ValueError as e:
            warns.append(f"FREQ {e}")
    band = rec.get("BAND", "").lower()
    if band in cfg["band_freq"]:
        warns.append(f"FREQ missing; used representative frequency for BAND={band}")
        return cfg["band_freq"][band]
    warns.append("no usable FREQ or BAND; left empty")
    return ""


def _mode(rec: dict, cfg: dict) -> str:
    mode, sub = rec.get("MODE", "").strip().upper(), rec.get("SUBMODE", "").strip().upper()
    table = {k.upper(): v for k, v in cfg["mode_map"].items() if not k.startswith("_")}
    if sub and f"{mode}/{sub}" in table:
        return table[f"{mode}/{sub}"]
    if mode in table:
        return table[mode]
    return sub or mode


def format_rst(value: str) -> str:
    """Signed values are zero-padded to two digits (-4 -> -04); others pass through."""
    v = value.strip()
    m = re.fullmatch(r"([+-])(\d{1,2})", v)
    return f"{m.group(1)}{int(m.group(2)):02d}" if m else v


def _name(rec: dict, warns: list[str]) -> str:
    name = rec.get("NAME", "").strip()
    if not name:
        return ""
    if not name.isascii():
        warns.append("NAME contains non-ASCII characters; left empty")
        return ""
    return re.sub(r"\s+", "", name).upper()[:12]


def convert_qso(rec: dict, cfg: dict, opts: Options | None = None) -> Converted:
    opts = opts or Options()
    warns: list[str] = []
    call = rec.get("CALL", "").strip()
    if not call:
        raise ConvertError("CALL missing")
    dt = _datetime(rec)
    domestic = is_domestic(rec, cfg)
    dxcc = rec.get("DXCC", "").strip()

    use_jst = opts.tz == "jst" or (opts.tz == "mixed" and domestic)
    local = dt + JST if use_jst else dt
    flags = cfg["field_sources"]

    code = ""
    if not domestic:
        code = cfg["dxcc_code"].get(dxcc, "") if dxcc else ""
        if not code:
            warns.append(f"no HAMLOG code for DXCC {dxcc or '?'} ({rec.get('COUNTRY', '')}); Code left empty")

    # QTH column: continent for foreign stations only. Domestic JCC/JCG goes to Rmks1.
    qth = "" if domestic else rec.get("CONT", "").strip().upper()
    jcc = ""
    if domestic:
        v = rec.get(flags["jcc"], "").strip()
        jcc = v if re.fullmatch(r"\d{4,5}", v) else ""

    dx = cfg["dx_flag"]
    flag = dx["domestic"] if domestic else dx.get(dxcc, dx["default"])

    qsl = "J"
    if (cfg["qsl"]["electronic_received_jee"] and rec.get("QSL_RCVD", "").upper() == "Y"
            and rec.get("QSL_RCVD_VIA", "").upper() == "E"):
        qsl = "JEE"

    his, my = format_rst(rec.get("RST_SENT", "")), format_rst(rec.get("RST_RCVD", ""))
    if not his or not my:
        warns.append("RST missing")

    sat_on = cfg["satellite"]["remarks_enabled"] if opts.sat_remarks is None else opts.sat_remarks
    sat = ""
    if sat_on and rec.get("SAT_NAME", "").strip():
        sat = cfg["satellite"]["remarks_format"].format(sat=rec["SAT_NAME"].strip())
    rmks1 = " ".join(x for x in (jcc, sat) if x)

    values = {
        "call": call.upper(),
        "date": local.strftime("%y/%m/%d"),
        "time": local.strftime("%H:%M") + ("J" if use_jst else "U"),
        "his": his,
        "my": my,
        "freq": _freq(rec, cfg, warns),
        "mode": _mode(rec, cfg),
        "code": code,
        "gl": rec.get(flags["grid"], "").strip().upper(),
        "qsl": qsl,
        "name": _name(rec, warns),
        "qth": qth,
        "rmks1": rmks1,
        "rmks2": "",
        "dx_flag": flag,
        "extra": "",
    }
    return Converted([values[k] for k in KEYS], warns)


def convert_all(records, cfg: dict, opts: Options | None = None):
    """Convert every record; never raises. Returns (rows, messages)."""
    rows: list[list[str]] = []
    messages: list[str] = []
    for i, rec in enumerate(records, 1):
        try:
            c = convert_qso(rec, cfg, opts)
        except ConvertError as e:
            messages.append(f"QSO #{i} ({rec.get('CALL', '?')}): skipped: {e}")
            continue
        rows.append(c.row)
        messages.extend(f"QSO #{i} ({c.row[0]}): {w}" for w in c.warnings)
    return rows, messages

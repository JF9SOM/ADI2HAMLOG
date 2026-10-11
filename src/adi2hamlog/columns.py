"""HAMLOG CSV column definitions -- the single place to change the layout.

Status of every statement here is tracked in CLAUDE.md section 5.
Layout is based on samples/sample.csv (HAMLOG export, 16 columns, no header,
no quoting, cp932, CRLF). Names are provisional; positions come from the sample.
"""

from dataclasses import dataclass
from typing import Optional

ENCODING = "cp932"
NEWLINE = "\r\n"
QUOTE_ALL = False  # adi2csv quotes every field; HAMLOG's own export does not (both unverified for import)


@dataclass(frozen=True)
class Column:
    key: str
    label: str
    max_len: Optional[int] = None  # None = unknown (unverified)


COLUMNS = (
    Column("call", "コール"),
    Column("date", "日付"),            # YY/MM/DD
    Column("time", "時刻"),            # HH:MMU / HH:MMJ
    Column("his", "His"),              # RST_SENT
    Column("my", "My"),                # RST_RCVD
    Column("freq", "Freq"),            # MHz, 3 decimals, trailing zeros stripped; V/U etc. for satellite
    Column("mode", "Mode"),
    Column("code", "Code"),            # DXCC -> HAMLOG code table (foreign only)
    Column("gl", "GL"),                # GRIDSQUARE
    Column("qsl", "QSL"),              # J / JEE
    Column("name", "Name", 12),        # 12 is observed, not documented
    Column("qth", "QTH"),              # CONT (foreign) / JCC-JCG from COMMENT (domestic)
    Column("rmks1", "Rmks1"),
    Column("rmks2", "Rmks2"),
    Column("dx_flag", "DX区分"),       # 0 domestic / 8 foreign / 10 Philippines (meaning unverified)
    Column("extra", "識別"),           # hQSL/user in HAMLOG export; always empty here
)

COLUMN_COUNT = len(COLUMNS)
KEYS = tuple(c.key for c in COLUMNS)

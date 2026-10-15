import csv
import io
import pathlib

import pytest

from adi2hamlog.cli import main
from adi2hamlog.writer import encode_rows

SAMPLES = pathlib.Path(__file__).parent.parent / "samples"

ADI = (
    "<EOH>\n"
    "<CALL:5>JA1AA<QSO_DATE:8>20260831<TIME_ON:6>150000<DXCC:3>339<RST_SENT:2>59<RST_RCVD:2>59"
    "<FREQ:3>7.1<MODE:3>SSB<EOR>\n"
    "<CALL:5>JA2BB<QSO_DATE:8>20260801<TIME_ON:6>000000<DXCC:3>339<MODE:3>CW<FREQ:2>14<EOR>\n"
    "<CALL:5>JA3CC<EOR>\n"
)


def test_crlf_cp932_no_header():
    data, warns = encode_rows([["JA1AA", "26/09/01", "00:00J"], ["JA2BB", "x", "y"]])
    assert data == b"JA1AA,26/09/01,00:00J\r\nJA2BB,x,y\r\n" and warns == []


def test_unencodable_chars_are_replaced_and_reported():
    data, warns = encode_rows([["JA1AA", "name❤"], ["JA2BB", "ok"]])
    assert data.startswith(b"JA1AA,name?\r\n")
    assert len(warns) == 1 and "row 1" in warns[0] and "JA1AA" in warns[0]


def test_japanese_text_encodes_to_cp932():
    data, warns = encode_rows([["JA1AA", "城内"]])
    assert data == "JA1AA,城内\r\n".encode("cp932") and warns == []


def test_field_with_comma_is_quoted():
    data, _ = encode_rows([["JA1AA", "a,b"]])
    assert data == b'JA1AA,"a,b"\r\n'


def test_cli_end_to_end(tmp_path, capsys):
    src, out = tmp_path / "in.adi", tmp_path / "out.csv"
    src.write_text(ADI, encoding="utf-8")
    assert main([str(src), "-o", str(out), "--tz", "jst"]) == 0
    rows = list(csv.reader(io.StringIO(out.read_bytes().decode("cp932"))))
    assert len(rows) == 2 and all(len(r) == 16 for r in rows)
    assert rows[0][:3] == ["JA1AA", "26/09/01", "00:00J"]
    assert b"\r\n" in out.read_bytes()
    cap = capsys.readouterr()
    assert "2 QSO written" in cap.out and "1 skipped" in cap.out
    assert "JA3CC" in cap.err  # skipped QSO is reported, not silent


def test_cli_default_output_name_and_errors(tmp_path, capsys):
    src = tmp_path / "in.adi"
    src.write_text(ADI, encoding="utf-8")
    assert main([str(src)]) == 0 and (tmp_path / "in.csv").exists()
    assert main([str(tmp_path / "missing.adi")]) == 2
    empty = tmp_path / "e.adi"
    empty.write_text("<EOH>", encoding="utf-8")
    assert main([str(empty), "-o", str(tmp_path / "e.csv")]) == 1
    assert not (tmp_path / "e.csv").exists()


@pytest.mark.skipif(not (SAMPLES / "sample.adi").exists(), reason="local samples not available")
def test_cli_on_local_sample(tmp_path):
    out = tmp_path / "o.csv"
    assert main([str(SAMPLES / "sample.adi"), "-o", str(out)]) == 0
    assert len(out.read_bytes().split(b"\r\n")) == 76  # 75 rows + trailing empty


@pytest.mark.skipif(not (SAMPLES / "JF9SOM-20261011-1044.adi").exists(), reason="local samples not available")
def test_satellite_sample_matches_hand_edited_csv(tmp_path):
    out = tmp_path / "o.csv"
    assert main([str(SAMPLES / "JF9SOM-20261011-1044.adi"), "-o", str(out)]) == 0
    got = list(csv.reader(io.StringIO(out.read_bytes().decode("cp932"))))
    assert len(got) == 11
    assert all(r[5] == "V/U" and r[6] == "FT4" and r[12] == "RS-44" for r in got)

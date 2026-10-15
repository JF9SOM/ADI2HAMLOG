import csv
import io
import pathlib

import pytest

from adi2hamlog.adif import parse_file
from adi2hamlog.columns import COLUMN_COUNT
from adi2hamlog.config import load_config
from adi2hamlog.convert import ConvertError, Options, convert_all, convert_qso, format_mhz, format_rst

CFG = load_config()
SAMPLES = pathlib.Path(__file__).parent.parent / "samples"


def rec(**kw):
    base = {"CALL": "JA1ZZZ", "QSO_DATE": "20260801", "TIME_ON": "123456", "DXCC": "339",
            "RST_SENT": "59", "RST_RCVD": "59", "FREQ": "7.1", "MODE": "SSB"}
    base.update(kw)
    return base


def conv(opts=None, **kw):
    return convert_qso(rec(**kw), CFG, opts)


def test_row_has_16_columns():
    assert len(conv().row) == COLUMN_COUNT


def test_domestic_is_jst_and_crosses_midnight():
    r = conv(QSO_DATE="20260831", TIME_ON="150000").row
    assert (r[1], r[2]) == ("26/09/01", "00:00J")


def test_foreign_stays_utc_in_mixed():
    r = conv(DXCC="318", QSO_DATE="20260831", TIME_ON="233000").row
    assert (r[1], r[2]) == ("26/08/31", "23:30U")


def test_tz_options():
    assert conv(Options(tz="jst"), DXCC="318", TIME_ON="150000").row[2] == "00:00J"
    assert conv(Options(tz="utc"), TIME_ON="150000").row[2] == "15:00U"
    with pytest.raises(ValueError):
        Options(tz="x")


def test_four_digit_time_and_domestic_fallback_by_prefix():
    r = conv(DXCC="", CALL="7K1ABC", TIME_ON="0100").row
    assert r[2] == "10:00J"


@pytest.mark.parametrize("bad", [{"QSO_DATE": ""}, {"TIME_ON": "99"}, {"QSO_DATE": "20261301"}, {"CALL": ""}])
def test_unconvertible_qso_raises(bad):
    with pytest.raises(ConvertError):
        conv(**bad)


def test_freq_truncated_and_trailing_zeros_removed():
    assert format_mhz("18.102514") == "18.102"
    assert format_mhz("7.100") == "7.1"
    assert format_mhz("144.940") == "144.94"
    assert format_mhz("145") == "145"
    with pytest.raises(ValueError):
        format_mhz("abc")


def test_freq_from_band_when_missing_warns():
    c = conv(FREQ="", BAND="40m")
    assert c.row[5] == "7.1" and c.warnings


def test_satellite_freq_and_remarks():
    c = conv(DXCC="318", PROP_MODE="SAT", FREQ="145.9", FREQ_RX="435.1", SAT_NAME="RS-44",
             MODE="MFSK", SUBMODE="FT4")
    assert c.row[5] == "V/U" and c.row[6] == "FT4" and c.row[12] == "RS-44"
    assert conv(PROP_MODE="SAT", FREQ="435.1", FREQ_RX="145.9").row[5] == "U/V"


def test_satellite_unknown_bands_falls_back_to_mhz():
    c = conv(PROP_MODE="SAT", FREQ="29.4", FREQ_RX="145.9")
    assert c.row[5] == "29.4" and c.warnings


def test_satellite_remarks_can_be_disabled():
    c = conv(Options(sat_remarks=False), PROP_MODE="SAT", SAT_NAME="RS-44")
    assert c.row[12] == ""


def test_mode_mapping():
    assert conv(MODE="MFSK", SUBMODE="FT4").row[6] == "FT4"
    assert conv(MODE="FT8").row[6] == "FT8"
    assert conv(MODE="SSB", SUBMODE="USB").row[6] == "SSB"
    assert conv(MODE="MFSK", SUBMODE="JS8").row[6] == "JS8"


def test_rst_formatting():
    assert format_rst("-4") == "-04" and format_rst("+9") == "+09" and format_rst("599") == "599"
    c = conv(RST_SENT="-04", RST_RCVD="+01")
    assert (c.row[3], c.row[4]) == ("-04", "+01")


def test_qsl():
    assert conv().row[9] == "J"
    assert conv(QSL_RCVD="Y", QSL_RCVD_VIA="E").row[9] == "J"  # default matches adi2csv
    on = {**CFG, "qsl": {"electronic_received_jee": True}}
    assert convert_qso(rec(QSL_RCVD="Y", QSL_RCVD_VIA="E"), on).row[9] == "JEE"
    assert convert_qso(rec(QSL_RCVD="Y", QSL_RCVD_VIA="D"), on).row[9] == "J"


def test_code_and_dx_flag():
    r = conv(DXCC="318", CONT="as").row
    assert (r[7], r[11], r[14]) == ("565A", "AS", "8")
    r = conv(DXCC="375").row
    assert r[14] == "10"
    c = conv(DXCC="999", COUNTRY="NOWHERE")
    assert c.row[7] == "" and c.row[14] == "8" and c.warnings
    r = conv().row
    assert (r[7], r[11], r[14]) == ("", "", "0")


def test_jcc_goes_to_rmks1_only_if_numeric():
    assert conv(COMMENT="2909").row[12] == "2909"
    assert conv(COMMENT="29009").row[12] == "29009"
    assert conv(COMMENT="08M").row[12] == ""
    assert conv(COMMENT="2909", PROP_MODE="SAT", SAT_NAME="AO-7").row[12] == "2909 AO-7"


def test_name_rules():
    assert conv(NAME="Serge Kozhevnikov").row[10] == "SERGEKOZHEVN"
    assert conv(NAME="Harold").row[10] == "HAROLD"
    c = conv(NAME="城内")
    assert c.row[10] == "" and c.warnings


def test_grid_and_empty_columns():
    r = conv(GRIDSQUARE="pm95he").row
    assert r[8] == "PM95HE" and r[13] == "" and r[15] == ""


def test_convert_all_skips_bad_and_reports():
    rows, msgs = convert_all([rec(), rec(QSO_DATE=""), rec(CALL="JA2ZZZ")], CFG)
    assert [r[0] for r in rows] == ["JA1ZZZ", "JA2ZZZ"]
    assert any("QSO #2" in m and "skipped" in m for m in msgs)


@pytest.mark.skipif(not (SAMPLES / "sample.adi").exists(), reason="local samples not available")
def test_regression_against_hamlog_export():
    """Columns 4-15 should match HAMLOG's own export except where the two files differ
    in time of export (GL gained from LoTW later, QSL received later). Z == U."""
    rows, _ = convert_all(parse_file(SAMPLES / "sample.adi").records, {**CFG, "qsl": {"electronic_received_jee": True}})
    ours = {(r[0], r[1], r[2].replace("U", "Z")): r for r in rows}
    ref = list(csv.reader(io.StringIO((SAMPLES / "sample.csv").read_bytes().decode("cp932"))))
    mismatched = 0
    for r in ref:
        o = ours[(r[0], r[1], r[2])]
        for i in (3, 4, 5, 6, 7, 10, 11, 12, 13, 14):
            assert o[i] == r[i], (r[0], i + 1, r[i], o[i])
        mismatched += o[8] != r[8] or o[9] != r[9]
    assert len(ref) == 58 and mismatched <= 20

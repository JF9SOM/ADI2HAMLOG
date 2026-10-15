import pathlib

import pytest

from adi2hamlog.adif import decode_bytes, parse_file, parse_text

SAMPLES = pathlib.Path(__file__).parent.parent / "samples"


def test_basic_record_and_header_skipped():
    r = parse_text("Header text\n<ADIF_VER:5>3.1.7\n<EOH>\n<CALL:5>JA1AA<MODE:3>FT8<EOR>\n")
    assert r.records == [{"CALL": "JA1AA", "MODE": "FT8"}]
    assert r.warnings == []


def test_no_header():
    r = parse_text("<CALL:5>JA1AA<EOR>")
    assert r.records == [{"CALL": "JA1AA"}]


def test_tags_are_case_insensitive_and_type_ignored():
    r = parse_text("<eoh><call:5:s>JA1AA<Freq:3:N>7.1<eor>")
    assert r.records == [{"CALL": "JA1AA", "FREQ": "7.1"}]


def test_multiple_records_and_newlines_between_fields():
    r = parse_text("<EOH>\r\n<CALL:3>AB1\r\n<EOR>\n\n<CALL:3>CD2\n<EOR>\n")
    assert [x["CALL"] for x in r.records] == ["AB1", "CD2"]


def test_value_containing_angle_bracket():
    r = parse_text("<EOH><COMMENT:7>a<b>c<d<CALL:3>AB1<EOR>")
    assert r.records[0]["COMMENT"] == "a<b>c<d"
    assert r.records[0]["CALL"] == "AB1"


def test_length_in_characters_for_multibyte():
    # Wavelog style: <NAME:2> for two kanji (6 bytes in UTF-8)
    r = parse_text("<EOH><NAME:2>城内<QTH:3>越前市<CALL:3>AB1<EOR>")
    assert r.records[0] == {"NAME": "城内", "QTH": "越前市", "CALL": "AB1"}
    assert r.warnings == []


def test_length_in_bytes_for_multibyte():
    # ADIF-spec style: <NAME:6> for two kanji
    r = parse_text("<EOH><NAME:6>城内<CALL:3>AB1<EOR>")
    assert r.records[0] == {"NAME": "城内", "CALL": "AB1"}
    assert r.warnings == []


def test_bad_length_warns_but_continues():
    r = parse_text("<EOH><CALL:2>AB123<MODE:3>FT8<EOR><CALL:3>CD2<EOR>")
    assert len(r.records) == 2
    assert r.records[0]["MODE"] == "FT8"
    assert any("length" in w for w in r.warnings)


def test_missing_length_and_missing_eor():
    r = parse_text("<EOH><FOO>x<CALL:3>AB1")
    assert r.records == [{"CALL": "AB1"}]
    assert len(r.warnings) == 2


def test_empty_value():
    r = parse_text("<EOH><NAME:0><CALL:3>AB1<EOR>")
    assert r.records == [{"NAME": "", "CALL": "AB1"}]


def test_decode_utf8_bom_and_cp932():
    assert decode_bytes("﻿<CALL:3>AB1".encode("utf-8")).endswith("AB1")
    assert decode_bytes("<NAME:2>城内".encode("cp932")).endswith("城内")


@pytest.mark.skipif(not (SAMPLES / "sample.adi").exists(), reason="local samples not available")
def test_local_sample_counts():
    r = parse_file(SAMPLES / "sample.adi")
    assert len(r.records) == 75
    assert r.warnings == []
    assert all("CALL" in q for q in r.records)

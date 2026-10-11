from adi2hamlog import columns


def test_sixteen_columns():
    assert columns.COLUMN_COUNT == 16
    assert len(set(columns.KEYS)) == 16


def test_matches_sample_csv_width():
    import csv, io, pathlib
    p = pathlib.Path(__file__).parent.parent / "samples" / "sample.csv"
    if not p.exists():
        return
    rows = list(csv.reader(io.StringIO(p.read_bytes().decode(columns.ENCODING))))
    assert rows and all(len(r) == columns.COLUMN_COUNT for r in rows)

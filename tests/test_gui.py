import csv
import io
import os
import pathlib

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl  # noqa: E402
from PySide6.QtGui import QDropEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from adi2hamlog.gui import MainWindow  # noqa: E402

ADI = (
    "<EOH>\n<CALL:5>JA1AA<QSO_DATE:8>20260831<TIME_ON:6>150000<DXCC:3>339"
    "<RST_SENT:2>59<RST_RCVD:2>59<FREQ:3>7.1<MODE:3>SSB<EOR>\n"
)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def adi(tmp_path):
    p = tmp_path / "log.adi"
    p.write_text(ADI, encoding="utf-8")
    return p


def test_initial_state(app):
    w = MainWindow()
    assert not w.convert_btn.isEnabled()


def test_set_input_fills_default_output(app, adi):
    w = MainWindow()
    w.set_input(str(adi))
    assert w.output_edit.text() == str(adi.with_suffix(".csv"))
    assert w.convert_btn.isEnabled()


def test_drop_event_sets_input(app, adi):
    w = MainWindow()
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(adi))])
    ev = QDropEvent(QPointF(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    w.drop.dropEvent(ev)
    assert w.input_edit.text() == str(adi)


def test_convert_with_options(app, adi):
    w = MainWindow()
    w.set_input(str(adi))
    w.tz.setCurrentIndex(1)  # all JST
    res = w.convert(confirm_overwrite=False)
    assert res.written == 1 and not res.error
    rows = list(csv.reader(io.StringIO(adi.with_suffix(".csv").read_bytes().decode("cp932"))))
    assert rows[0][1:3] == ["26/09/01", "00:00J"]
    assert "1 件" in w.status.text()


def test_convert_error_is_shown(app, tmp_path):
    bad = tmp_path / "bad.adi"
    bad.write_text("<EOH>", encoding="utf-8")
    w = MainWindow()
    w.set_input(str(bad))
    res = w.convert(confirm_overwrite=False)
    assert res.error and "エラー" in w.log.toPlainText()
    assert not bad.with_suffix(".csv").exists()

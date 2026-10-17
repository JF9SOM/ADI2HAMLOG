import csv
import io
import os
import pathlib

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMimeData, QPointF, QSettings, Qt, QUrl  # noqa: E402
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
def settings(tmp_path):
    """Isolated settings file so tests never touch the user's real preferences."""
    return QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat)


@pytest.fixture
def adi(tmp_path):
    p = tmp_path / "log.adi"
    p.write_text(ADI, encoding="utf-8")
    return p


def test_initial_state(app, settings):
    w = MainWindow(settings)
    assert not w.convert_btn.isEnabled()


def test_set_input_fills_default_output(app, settings, adi):
    w = MainWindow(settings)
    w.set_input(str(adi))
    assert w.output_edit.text() == str(adi.with_suffix(".csv"))
    assert w.convert_btn.isEnabled()


def test_drop_event_sets_input(app, settings, adi):
    w = MainWindow(settings)
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(adi))])
    ev = QDropEvent(QPointF(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    w.drop.dropEvent(ev)
    assert w.input_edit.text() == str(adi)


def test_convert_with_options(app, settings, adi):
    w = MainWindow(settings)
    w.set_input(str(adi))
    w.tz.setCurrentIndex(1)  # all JST
    res = w.convert(confirm_overwrite=False)
    assert res.written == 1 and not res.error
    rows = list(csv.reader(io.StringIO(adi.with_suffix(".csv").read_bytes().decode("cp932"))))
    assert rows[0][1:3] == ["26/09/01", "00:00J"]
    assert "1 件" in w.status.text()


def test_convert_error_is_shown(app, settings, tmp_path):
    bad = tmp_path / "bad.adi"
    bad.write_text("<EOH>", encoding="utf-8")
    w = MainWindow(settings)
    w.set_input(str(bad))
    res = w.convert(confirm_overwrite=False)
    assert res.error and "エラー" in w.log.toPlainText()
    assert not bad.with_suffix(".csv").exists()


def test_sat_freq_choice_reaches_output(app, settings, tmp_path):
    src = tmp_path / "sat.adi"
    src.write_text("<EOH><CALL:5>BD5EU<QSO_DATE:8>20261007<TIME_ON:6>082845<DXCC:3>318<MODE:3>FM"
                   "<PROP_MODE:3>SAT<FREQ:3>145<FREQ_RX:3>435<EOR>", encoding="utf-8")
    w = MainWindow(settings)
    assert w.sat_freq.currentData() == "mhz"
    w.set_input(str(src))
    w.sat_freq.setCurrentIndex(w.sat_freq.findData("band"))
    w.convert(confirm_overwrite=False)
    assert src.with_suffix(".csv").read_text(encoding="cp932").split(",")[5] == "V/U"


def test_options_are_remembered_between_launches(app, settings):
    w = MainWindow(settings)
    assert w.tz.currentData() == "mixed" and w.sat_freq.currentData() == "mhz"
    assert w.sat.isChecked() and not w.jee.isChecked()
    w.tz.setCurrentIndex(w.tz.findData("utc"))
    w.sat_freq.setCurrentIndex(w.sat_freq.findData("band"))
    w.sat.setChecked(False)
    w.jee.setChecked(True)

    w2 = MainWindow(settings)  # next launch
    assert w2.tz.currentData() == "utc" and w2.sat_freq.currentData() == "band"
    assert not w2.sat.isChecked() and w2.jee.isChecked()


def test_invalid_saved_values_fall_back_to_defaults(app, settings):
    settings.setValue("tz", "bogus")
    settings.setValue("sat_freq", "bogus")
    settings.setValue("sat_remarks", "maybe")
    w = MainWindow(settings)
    assert w.tz.currentData() == "mixed" and w.sat_freq.currentData() == "mhz" and w.sat.isChecked()

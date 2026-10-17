"""PySide6 GUI: drop an .adi file, choose options, convert. Logic lives in service.py/convert.py."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PySide6.QtCore import QSettings, Qt
    from PySide6.QtWidgets import (
        QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
        QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
    )
except ImportError:  # pragma: no cover - exercised only without the optional dependency
    print("GUI には PySide6 が必要です:  pip install 'adi2hamlog[gui]'", file=sys.stderr)
    raise SystemExit(2)

from . import __version__
from .config import load_config
from .convert import Options
from .service import Result, convert_file, default_output

TZ_CHOICES = (
    ("mixed", "国内局は JST(J)/外国局は UTC(U)"),
    ("jst", "すべて JST(J)"),
    ("utc", "すべて UTC(U)"),
)
SAT_FREQ_CHOICES = (
    ("mhz", "145/435(MHz)"),
    ("band", "V/U(バンド記号)"),
)
DROP_TEXT = "ここに .adi ファイルをドロップ\n(クリックで選択)"


class DropArea(QLabel):
    def __init__(self, on_file):
        super().__init__(DROP_TEXT)
        self._on_file = on_file
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(110)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "QLabel { border: 2px dashed palette(mid); border-radius: 8px; padding: 12px; }"
        )

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            self._on_file(paths[0], extra=len(paths) - 1)

    def mouseReleaseEvent(self, e):
        self._on_file(None, extra=0)


class MainWindow(QWidget):
    def __init__(self, settings: QSettings | None = None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings("adi2hamlog", "adi2hamlog")
        self.setWindowTitle(f"adi2hamlog {__version__} - ADIF → HAMLOG CSV")
        self.resize(640, 560)
        self.cfg = load_config()
        self._output_touched = False

        self.drop = DropArea(self.set_input)
        self.input_edit = QLineEdit(readOnly=True)
        self.output_edit = QLineEdit()
        out_btn = QPushButton("保存先…")
        out_btn.clicked.connect(self.choose_output)

        self.tz = QComboBox()
        for key, label in TZ_CHOICES:
            self.tz.addItem(label, key)
        self.sat_freq = QComboBox()
        for key, label in SAT_FREQ_CHOICES:
            self.sat_freq.addItem(label, key)
        self.sat_freq.setCurrentIndex(max(0, self.sat_freq.findData(self.cfg["satellite"]["freq_style"])))
        self.sat = QCheckBox("衛星名(SAT_NAME)を Remarks に入れる")
        self.sat.setChecked(self.cfg["satellite"]["remarks_enabled"])
        self.jee = QCheckBox("電子 QSL を受領済みなら QSL 欄を JEE にする")
        self.jee.setChecked(self.cfg["qsl"]["electronic_received_jee"])

        self._restore_options()
        self.tz.currentIndexChanged.connect(self._save_options)
        self.sat_freq.currentIndexChanged.connect(self._save_options)
        self.sat.toggled.connect(self._save_options)
        self.jee.toggled.connect(self._save_options)

        self.convert_btn = QPushButton("変換")
        self.convert_btn.setEnabled(False)
        self.convert_btn.setDefault(True)
        self.convert_btn.clicked.connect(self.convert)

        self.log = QPlainTextEdit(readOnly=True)
        self.log.setPlaceholderText("警告やエラーがここに表示されます")
        self.status = QLabel("")
        self.status.setWordWrap(True)

        out_row = QHBoxLayout()
        out_row.addWidget(self.output_edit, 1)
        out_row.addWidget(out_btn)
        form = QFormLayout()
        form.addRow("入力", self.input_edit)
        form.addRow("出力", out_row)
        form.addRow("時刻", self.tz)
        form.addRow("衛星の周波数", self.sat_freq)
        form.addRow("", self.sat)
        form.addRow("", self.jee)

        lay = QVBoxLayout(self)
        lay.addWidget(self.drop)
        lay.addLayout(form)
        lay.addWidget(self.convert_btn)
        lay.addWidget(self.status)
        lay.addWidget(self.log, 1)
        self.output_edit.textEdited.connect(lambda _: setattr(self, "_output_touched", True))

    # --- remembered options ---------------------------------------------------------
    def _restore_options(self):
        """Apply saved choices; anything missing or invalid keeps the config default."""
        st = self.settings
        for combo, key in ((self.tz, "tz"), (self.sat_freq, "sat_freq")):
            idx = combo.findData(st.value(key, None))
            if idx >= 0:
                combo.setCurrentIndex(idx)
        for box, key in ((self.sat, "sat_remarks"), (self.jee, "qsl_jee")):
            v = st.value(key, None)
            if v in (True, False, "true", "false"):
                box.setChecked(v in (True, "true"))

    def _save_options(self, *_):
        st = self.settings
        st.setValue("tz", self.tz.currentData())
        st.setValue("sat_freq", self.sat_freq.currentData())
        st.setValue("sat_remarks", self.sat.isChecked())
        st.setValue("qsl_jee", self.jee.isChecked())
        st.sync()

    # --- input / output selection -------------------------------------------------
    def set_input(self, path, extra=0):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "ADIF ファイルを選択", "", "ADIF (*.adi *.adif);;すべて (*)")
            if not path:
                return
        p = Path(path)
        self.input_edit.setText(str(p))
        if not self._output_touched:
            self.output_edit.setText(str(default_output(p)))
        self.convert_btn.setEnabled(True)
        self.drop.setText(p.name)
        self.status.setText("")
        self.log.clear()
        if extra > 0:
            self.log.appendPlainText(f"注意: 複数ファイルがドロップされました。先頭の 1 つだけを使います(他 {extra} 件は無視)。")

    def choose_output(self):
        start = self.output_edit.text() or ""
        path, _ = QFileDialog.getSaveFileName(self, "CSV の保存先", start, "CSV (*.csv)")
        if path:
            self.output_edit.setText(path)
            self._output_touched = True

    # --- conversion -----------------------------------------------------------------
    def current_options(self) -> Options:
        return Options(tz=self.tz.currentData(), sat_remarks=self.sat.isChecked(),
                       sat_freq=self.sat_freq.currentData())

    def current_config(self) -> dict:
        cfg = load_config()
        cfg["qsl"]["electronic_received_jee"] = self.jee.isChecked()
        return cfg

    def convert(self, confirm_overwrite: bool = True) -> Result | None:
        src, dst = self.input_edit.text(), self.output_edit.text().strip()
        if not src or not dst:
            return None
        if confirm_overwrite and Path(dst).exists():
            ans = QMessageBox.question(self, "上書きの確認", f"{dst}\nは既に存在します。上書きしますか?")
            if ans != QMessageBox.Yes:
                return None
        res = convert_file(src, dst, self.current_config(), self.current_options())
        self.log.clear()
        for w in res.warnings:
            self.log.appendPlainText(f"警告: {w}")
        if res.error:
            self.log.appendPlainText(f"エラー: {res.error}")
            self.status.setText("変換できませんでした")
        else:
            msg = f"{res.written} 件を書き出しました → {res.output.name}"
            self.status.setToolTip(str(res.output))
            if res.skipped:
                msg += f"({res.skipped} 件スキップ)"
            self.status.setText(msg)
        return res


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    w = MainWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

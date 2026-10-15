# adi2hamlog

ADIF(`.adi`)形式のログを、Turbo HAMLOG 用の CSV に変換するコマンドラインツールです。
Windows 専用の adi2csv と同等の変換を、Mac / Linux / Windows で行えます。

Wavelog などが出力する ADIF を変換するときに、adi2csv では手作業が必要だった次の点を自動化しています。

- 衛星 QSO の周波数欄を `V/U` などにする
- モードを `MFSK`+`FT4` → `FT4` のように HAMLOG 向けにする
- 衛星名(`RS-44` など)を Remarks 欄に入れる

> **開発中・非公式**: 出力の仕様は、手元のログと HAMLOG の出力 CSV を観察して作った推定を含みます(下記「既知の制限」)。取り込む前に必ず内容を確認してください。

## インストール

Python 3.10 以上が必要です。外部ライブラリは使いません。

```bash
git clone https://github.com/JF9SOM/ADI2HAMLOG.git
cd ADI2HAMLOG
python3 -m pip install .
```

GUI も使う場合は、PySide6 を追加します(コア機能とコマンドライン版は外部ライブラリ不要のままです)。

```bash
python3 -m pip install ".[gui]"
```

インストールせずにコマンドライン版を使う場合は、`src/` を指定して実行できます。

```bash
PYTHONPATH=src python3 -m adi2hamlog input.adi -o out.csv
```

## 使い方(GUI)

```bash
adi2hamlog-gui
```

ウィンドウに `.adi` ファイルをドロップ(またはクリックして選択)し、時刻の扱いなどを選んで「変換」を押します。出力先の既定は入力ファイルと同じ場所の `.csv` で、既存ファイルを上書きするときは確認が出ます。警告やスキップした QSO は、画面下のログに表示されます。複数ファイルをドロップした場合は先頭の 1 つだけを使います。

## 使い方(コマンドライン)

```bash
adi2hamlog input.adi -o out.csv --tz mixed
```

| オプション | 説明 |
|---|---|
| `-o`, `--output` | 出力 CSV。省略すると入力ファイル名の拡張子を `.csv` にします |
| `--tz mixed` | 既定。国内局は JST(時刻の末尾 `J`)、外国局は UTC(末尾 `U`) |
| `--tz jst` | すべて JST(`J`) |
| `--tz utc` | すべて UTC(`U`) |
| `-c`, `--config` | 設定 JSON(既定値に上書きマージされます) |
| `--sat-remarks` / `--no-sat-remarks` | 衛星名を Remarks に入れる/入れない(既定は設定に従い、入れる) |

出力は cp932(Shift_JIS)、改行は CRLF、ヘッダ行なしの 16 列です。cp932 で表せない文字は `?` に置換し、警告を表示します。
変換できなかった QSO は処理を止めずにスキップし、理由を標準エラーに出します。

### 変換のルール(概要)

| 項目 | 内容 |
|---|---|
| 日付・時刻 | `YY/MM/DD`、`HH:MM`+`J`/`U`。JST への変換で日付をまたぐ場合は日付も変換 |
| 国内局の判定 | `DXCC=339`。DXCC が無い場合はコールサインのプレフィックスで判定 |
| 周波数 | MHz を小数 3 桁に切り捨て。`FREQ` が無ければ `BAND` から代表周波数。衛星は `V/U`・`U/V` など |
| モード | `MODE/SUBMODE` の変換表(例 `MFSK/FT4` → `FT4`) |
| RST | His=`RST_SENT`、My=`RST_RCVD`。符号付きは 2 桁にそろえる(`-4` → `-04`) |
| Code(8 列目) | DXCC 番号 → HAMLOG コードの表。表にない国は空欄にして警告 |
| グリッド(9 列目) | `GRIDSQUARE` |
| QSL(10 列目) | 既定は `J`。設定で、電子 QSL 受領時に `JEE` にできる |
| Name(11 列目) | `NAME` を大文字・空白なし・12 文字まで。日本語の名前は空欄 |
| QTH(12 列目) | 外国局は大陸コード(`AS` など) |
| Rmks1(13 列目) | 国内局は `COMMENT` が数字(JCC/JCG)ならその値。衛星名もここに入る |
| DX 区分(15 列目) | 国内 `0`、外国 `8`、フィリピンのみ `10` |
| 16 列目 | 常に空 |

### 設定ファイル

既定値は [`src/adi2hamlog/data/default_config.json`](src/adi2hamlog/data/default_config.json) です。変えたい項目だけを書いた JSON を `-c` で渡すと、既定値に上書きマージされます。

```json
{
  "mode_map": { "MFSK/JS8": "JS8" },
  "dxcc_code": { "xxx": "HAMLOG のコード" },
  "qsl": { "electronic_received_jee": true },
  "satellite": { "remarks_enabled": false }
}
```

## 既知の制限

- **Code 表(8 列目)は不完全です。** HAMLOG の DXCC コード表は公開されておらず、実際の出力から読み取れた 13 エンティティだけを収録しています。表にない国は空欄になり、警告が出ます。設定の `dxcc_code` に追加してください。
- **推定を含む列があります。** 15 列目(DX 区分)の値の意味、QSL 欄 `JEE` の各文字の意味、周波数の切り捨て(四捨五入ではなく)は、サンプルからの推定です。
- **CSV の書式は HAMLOG への取り込みを確認していません。** 引用符なし、16 列、16 列目が空、という形式で出力します。
- **衛星の周波数表記は `V/U`・`U/V`・`V/V`・`U/U` のみ**です(VHF=144–148 MHz、UHF=420–450 MHz)。それ以外の組み合わせ(HF や L バンドなど)は MHz のまま出力し、警告を出します。
- **Name 欄の日本語は空欄**になります(adi2csv/HAMLOG の出力に合わせた挙動)。
- **文字数制限は Name の 12 文字以外は確認できていません。** 他の欄は切り詰めません。
- ADIF のうち、`CNTY`・`QTH`・`STATE` などは使用しません(JCC/JCG は `COMMENT` から取ります)。取得元の切り替えは今後の課題です。
- GUI は 1 ファイルずつの変換のみです。単体アプリの署名・公証はしていません。

## 単体アプリ(Python 不要)

GitHub Actions が macOS(Apple Silicon)・Windows・Linux 用の GUI アプリを PyInstaller でビルドします([`.github/workflows/build.yml`](.github/workflows/build.yml))。

- 手動実行: GitHub の Actions タブ → "Build apps" → Run workflow。成果物はその実行の Artifacts からダウンロードできます。
- リリース: `v0.1.0` のようなタグを push すると、macOS 用の `.dmg`、Windows 用の zip、Linux 用の tar.gz が GitHub Releases に添付されます。

> 署名・公証はしていません。macOS では、`.dmg` を開いて `adi2hamlog.app` を Applications へドラッグし、初回は右クリック →「開く」で起動します(警告が出ます)。Windows では SmartScreen の警告が出る場合があります。

手元でビルドする場合は、対象の OS 上で次を実行します。

```bash
python3 -m pip install -e ".[gui]" pyinstaller
python3 packaging/build.py --smoke     # 結果は dist/ に出力
```

## 開発

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[test]"
.venv/bin/pytest
```

仕様の確認状況(確認済み / 推定 / 未検証)は [CLAUDE.md](CLAUDE.md) にまとめています。

## ライセンス

MIT License(JF9SOM)

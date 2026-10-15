# CLAUDE.md — ADI2HAMLOG(ADIF → Turbo HAMLOG CSV 変換ツール)

## 1. 目的と範囲
アマチュア無線ログ形式 ADIF(.adi)を、Turbo HAMLOG にインポートできる CSV に変換する Python ツール。
Windows 専用の既存ソフト「adi2csv」と同等の機能を、Mac / Linux / Windows で動く MIT ライセンスの OSS として実装する。
GitHub: https://github.com/JF9SOM/ADI2HAMLOG (公開済み)。

- 範囲内: ADIF 読み込み、HAMLOG CSV 書き出し、CLI、設定ファイル(モード表・フィールド対応)、pytest。
- GUI(PySide6、ドラッグ&ドロップ)も範囲内(必須)。コアは外部依存なしのまま、GUI は任意の `[gui]` extra。
- 範囲外: HAMLOG からの逆変換。

## 2. 技術方針
- Python 3.10 以上。コアは標準ライブラリのみ(外部依存なし)。テストのみ pytest 可。
- CLI 例: `adi2hamlog input.adi -o out.csv --tz jst`
- コアロジックは GUI から再利用できるようモジュール分離(パーサ / 変換 / CSV 出力 / CLI)。
- 列定義(列順・列数・文字数制限)は **1 か所**(`columns.py` または設定)に集約し、後から直しやすくする。
- 出力は cp932・CRLF。cp932 で表現できない文字は置換し、件数と該当 QSO を警告表示。
- 変換不能 QSO・欠落フィールドは処理を止めずログ出力。
- git init は可。**コミットは diff をユーザーが確認・承認してから**。

## 3. ディレクトリ構成案
```
ADI2HAMLOG/
├── CLAUDE.md
├── README.md              # インストール/使い方/HAMLOGインポート手順/既知の制限
├── LICENSE                # MIT
├── pyproject.toml
├── samples/               # 実データ(ADIF と HAMLOG CSV)
├── src/adi2hamlog/
│   ├── __init__.py
│   ├── adif.py            # ADIF パーサ(バイト長/文字長対策)
│   ├── columns.py         # HAMLOG 列定義(唯一の定義場所)
│   ├── convert.py         # QSO → HAMLOG 行(時刻/周波数/モード/RST/QSL/Rmks)
│   ├── config.py          # 設定読み込み(モード表・フィールド対応)
│   ├── writer.py          # cp932/CRLF 出力、置換警告
│   ├── cli.py
│   └── data/default_config.json
└── tests/                 # pytest(samples を使った回帰テスト含む)
```

## 4. 作業ルール
- 情報は「確認済み(根拠あり)」と「未検証」を明確に区別して報告する。
- 同じエラーで 2〜3 回修正に失敗したらループせず停止し、状況とエラーログを報告する。
- 各フェーズ終わりに diff 概要を示し、承認後にコミット。
- README に インストール / 使い方 / HAMLOG インポート手順 / 既知の制限 を書く。

## 5. 確認状況の記録

凡例: ✅確認済(サンプルまたはユーザー申告が根拠) / 🔶推定(サンプルからの推測) / ❓未検証

実交信データ(`samples/`)は個人情報を含むため **git 管理外**(`.gitignore`)。本節には個人を特定する具体例を書かない。

### 5.1 根拠にしたサンプル(ローカルのみ)
- Wavelog 出力 ADIF 2 本(衛星 FT4 の 11 QSO、HF/VHF/UHF の 75 QSO)。
- adi2csv の出力 CSV(15 列、引用符付き)と、それを手動編集した CSV(Excel 整形の副産物とみられ、出力基準にしない)。
- HAMLOG 自身の出力 CSV(58 行)。75 QSO の ADIF とは期間指定の違いで完全一致しない(ADIF 側に 17 件多い。「大体同じ」として扱う)。

### 5.2 出力形式(確定方針)
- ✅ cp932・CRLF・ヘッダなし・**16 列**。UTC は **`U`**(ユーザー確認: HAMLOG は `U` で取り込める)。
- ✅ 日付 `YY/MM/DD`、RST は符号付きゼロ詰め(`-04`,`+09`)。
- ❓ 引用符の要否(adi2csv は全項目を引用、HAMLOG 出力は引用なし)。当面は引用なし。HAMLOG 側の取込可否は未検証。

### 5.3 列ごとの仕様
| # | 列 | 規則 | 状態 |
|---|----|------|------|
| 1 | コール | `CALL` | ✅ |
| 2 | 日付 | JST 変換後の日付(日付またぎ対応) | ✅ |
| 3 | 時刻 | 秒を捨て `HH:MM`。国内局(DXCC=339)は JST+`J`、外国局は UTC+`U` | ✅ |
| 4 | His | `RST_SENT` | ✅ |
| 5 | My | `RST_RCVD` | ✅ |
| 6 | Freq | `FREQ`(MHz)を小数 3 桁に切り捨て、末尾 0 削除。**衛星(`PROP_MODE=SAT`)は `V/U` 等** | ✅(切り捨ては🔶)/ 衛星表記の他組合せ ❓ |
| 7 | Mode | `MODE`+`SUBMODE` の変換表(例 MFSK+FT4→FT4) | ✅ |
| 8 | Code | DXCC 番号→HAMLOG コード表(外国局のみ。国内は空)。表にない国は空+警告 | ✅観測 13 件のみ/表は非公開 ❓ |
| 9 | GL | `GRIDSQUARE`(無ければ空) | ✅ |
| 10 | QSL | 既定は常に `J`(JARL 経由。adi2csv 出力と一致)。HAMLOG 出力では電子 QSL 受領行が `JEE`(`E`=電子 QSL)だが、adi2csv は同条件でも `J` だった。設定 `qsl.electronic_received_jee` で `QSL_RCVD=Y`+`VIA=E` → `JEE` に切替可 | ✅ / どちらが望ましいか ❓ |
| 11 | Name | `NAME` を大文字化・空白削除・12 文字切詰め。非 ASCII の名前は空欄 | ✅ |
| 12 | QTH | 外国局=`CONT`(大陸)。国内局は空。`CNTY`/`QTH` は未使用 | ✅ |
| 13 | Rmks1 | 国内局=`COMMENT` が数字(JCC 4 桁/JCG 5 桁)ならその値(HAMLOG 出力で Rmks1 位置と確認)。衛星時はオプションで `SAT_NAME`(例 `RS-44`)を追加。両方ある場合は空白区切りで連結 | ✅ / 連結の仕方は ❓ |
| 14 | Rmks2 | 空 | ✅ |
| 15 | DX 区分 | 国内 `0`、外国 `8`、フィリピンのみ `10`(海外移動局? ユーザー推測) | 🔶 |
| 16 | 識別 | 常に空(hQSL 登録印等で ADIF から判別不能。ユーザー決定) | ✅ |

### 5.4 自動化の主目的(ユーザー要望)
adi2csv 出力にユーザーが手作業で加えていた次の 3 点を自動化する。
1. Freq: `145` → `V/U`(`FREQ`/`FREQ_RX` と `PROP_MODE=SAT` から)
2. Mode: `MFSK` → `FT4`(`MODE`+`SUBMODE`)
3. Remarks: 衛星名(`SAT_NAME`)を追加

### 5.5 未検証事項
- HAMLOG の DXCC→コード表は非公開(Web 検索でも見つからず)。観測分のみ `default_config.json` に収録し、設定で追加可能。
- 各欄の文字数制限(Name の 12 以外)。
- QSL 欄 `JEE` の各文字の意味、他の組合せ(`E` のみ等)。
- 15 列目の値の意味(`10` の条件)。
- 衛星以外の特殊モード・バンド表記(U/V, U/L 等)。
- 引用符の要否、`Z`/`U` 以外の時刻表記。
- ADIF 中の `QSO_DATE`+`TIME_ON` が欠落/不正な QSO の扱い。

## 6. 実装計画(フェーズ)
- **フェーズ0**(完了): フォルダ確認、CLAUDE.md 作成、計画提示。→ 承認待ち
- **フェーズ1**: プロジェクト雛形(pyproject, LICENSE, ディレクトリ, git init)、`columns.py` の列定義(仮)。
- **フェーズ2**: ADIF パーサ(バイト長/文字長、大小文字無視、EOH/EOR、CRLF/LF 混在)+ pytest。
- **フェーズ3**: 変換ロジック(時刻/TZ、日付、周波数、モード表、RST、QSL、衛星 Remarks、フィールド対応設定)+ pytest。
- **フェーズ4**: CSV 出力(cp932/CRLF、置換警告)、CLI(`--tz` 等)、ログ。サンプル ADIF→CSV の回帰テスト。
- **フェーズ5**: 実データでの列仕様確定・仮仕様の解消、README、既知の制限。
- **フェーズ6**(GUI は必須とユーザーが決定): PySide6 によるドラッグ&ドロップ GUI(`gui.py`、共有ロジックは `service.py`)。配布は pip の `[gui]` extra と PyInstaller 単体アプリ(`packaging/`)。macOS でのビルド・起動は確認済み、Windows/Linux は未確認。

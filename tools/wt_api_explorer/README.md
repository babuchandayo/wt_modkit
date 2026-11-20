# WT ローカルAPI 値一覧ツール

War Thunder の起動中にクライアントが公開するローカルHTTP（既定 `http://127.0.0.1:8111`）を定期的に読み、
取得できたキーと値を一覧表示・保存するツール。ゲーム本体やファイルは一切変更しない（HTTPを読むだけ）。

## 必要なもの
- Windows + Python 3.9 以降（python.org 版なら tkinter 同梱）。追加ライブラリ不要。

## 使い方
1. War Thunder を起動する（格納庫でもよいが、`/state` などは戦闘中でないと `valid: false` だけになることが多い）。
2. `run.bat` をダブルクリック（または `python wt_api_explorer.py`）。
3. 「開始」で1秒ごとに取得。戦闘・機種を変えるほど、出現したキーが一覧に追加されていく。
4. 「CSV保存」でキー一覧（Excelで開ける）、「JSON保存」で各エンドポイントの最後の生レスポンスも含めて保存。

GUIなし: `python wt_api_explorer.py --cli -n 10 --out .`

## 一覧の列
| 列 | 意味 |
|---|---|
| endpoint | 取得元のパス |
| key | JSON内のキーパス。配列の要素は `[*]` にまとめ、要素数は `.length` |
| type | 観測した型（複数あれば `/` 区切り） |
| last_value / min / max | 最後の値、数値なら観測中の最小・最大 |
| seen_count | 観測回数（配列要素は要素ごとに数える） |

## 試すエンドポイント
`/state` `/indicators` `/map_obj.json` `/map_info.json` `/mission.json` `/gamechat?lastId=0` `/hudmsg?lastEvt=0&lastDmg=0` `/map.img`

これらはコミュニティで知られているもので、公式の仕様書は確認できていない。存在や中身はゲームのバージョン・状態で変わりうる。
一覧にないパスは「追加パス」欄（空白区切り）や `--extra` で試せる。`/map.img` は画像なので Content-Type とサイズだけ表示する。

## ゲームなしで試す
`python mock_server.py` を起動してから本ツールを起動。モックの応答の形は想定で、実ゲームとは一致しない。

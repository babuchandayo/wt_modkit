# War Thunder ローカルAPI (127.0.0.1:8111) のキー一覧

**信頼度**: ✅ 実際のゲームで観測できた値から確かめたもの ／ 🔶 値から推測したもの ／ ❔ 一般に知られているが、今回は観測できていないもの
公式の仕様書は見つかっていない。意味の説明は、観測した値とコミュニティの情報をもとにしている。

観測した状況（2026-11-20）: 空戦の試合中で、自分は機体に乗っていなかった（`/state` と `/indicators` が `valid:false` だけだったため）。

---

## /map_info.json — マップの座標系
| キー | 観測値 | 意味 | 信頼度 |
|---|---|---|---|
| valid | true | マップ情報が有効か | ✅ |
| map_min[*] / map_max[*] | -8192 / 8192 | マップ全体のワールド座標の範囲（m）。[x, y] の2要素 | 🔶 |
| grid_steps[*] | 1600 | 方眼（A1, B2…）1マスの大きさ（m） | 🔶 |
| grid_size[*] | 16367.5 | 方眼が覆う範囲の全長（m） | 🔶 |
| grid_zero[*] | -8183.75 / 8183.75 | 方眼の原点（左上の角）のワールド座標 | 🔶 |
| hud_type | 1 | HUD / マップの種類。値ごとの意味は不明 | ❔ |
| map_generation | 9 | マップが切り替わるたびに増える番号 | 🔶 |

## /map_obj.json — ミニマップのアイコン（配列で、1要素が1アイコン）
| キー | 観測値 | 意味 | 信頼度 |
|---|---|---|---|
| length | 285 | アイコンの数 | ✅ |
| [*].type | respawn_base_fighter など | 種類（aircraft, ground_model, airfield, capture_zone, respawn_base_* など） | 🔶 |
| [*].icon | respawn_base_fighter, Player など | 表示するアイコンの名前。`Player` が自分 | 🔶 |
| [*].icon_bg | none | アイコンの背景 | 🔶 |
| [*].color | #fa0C00 | 色（16進数）。味方と敵で色が変わる | ✅ |
| [*].color[] | [r,g,b] | 同じ色を 0〜255 のRGBで表したもの | ✅ |
| [*].blink | 0〜2 | 点滅の状態（占領中・攻撃を受けている、など） | 🔶 |
| [*].x / [*].y | 0〜1 | マップ上の位置。マップの幅を1としたときの割合で、左上が(0,0) | 🔶 |
| [*].dx / [*].dy | -360〜357 | 向き（自機などの機首方向）とされている。ただ、観測値が大きいので、単位ベクトルではない可能性がある | ❔ |
| [*].sx, sy, ex, ey | 0〜1付近 | 飛行場の滑走路の始点 (s) と終点 (e) | 🔶 |
| [*].zone_id | 0〜2 | 占領ポイントの番号 | 🔶 |
| [*].zone_label | C | 占領ポイントの名前（A/B/C） | ✅ |
| [*].zone_label_code | 65〜67 | zone_label の文字コード（65=A, 67=C） | ✅ |

## /mission.json — 任務の目標
| キー | 観測値 | 意味 | 信頼度 |
|---|---|---|---|
| status | running | 試合の状態（running の他に success / fail があるとされる） | 🔶 |
| objectives[*].text | Capture and maintain… | 目標の文章 | ✅ |
| objectives[*].status | in_progress | 目標ごとの進み具合 | ✅ |
| objectives[*].primary | true | 主目標かどうか | 🔶 |

## /hudmsg?lastEvt=0&lastDmg=0 — 撃破ログなど
`lastEvt` / `lastDmg` に前回受け取った最後の id を渡すと、それより新しいものだけが返る（とされている）。
| キー | 観測値 | 意味 | 信頼度 |
|---|---|---|---|
| damage[*].msg | 「A destroyed B」 | 撃破・被弾などのログの文章 | ✅ |
| damage[*].id | 1217〜1383 | 通し番号 | ✅ |
| damage[*].time | 80〜1286 | 試合開始からの秒数 | 🔶 |
| damage[*].sender / enemy / mode | 空 / false / 空 | チャット形式と共通の項目。damage では使われていない模様 | 🔶 |
| events[*] | （空） | HUD に出るイベントのメッセージ | ❔ |

## /gamechat?lastId=0 — 試合中のチャット
今回は空（length=0）。要素の項目は id, msg, sender, enemy, mode (All/Team/Squad), time とされている ❔

## /map.img — ミニマップの画像
JPEG（約200KB）。中身はキーではなく画像 ✅

## /state — 自機の飛行データ（乗っているときだけ）
今回は `valid:false` だけだった。機体に乗って飛んでいる間は、次のようなキーが出るとされている ❔
`H, m`（高度）, `TAS, km/h`（真対気速度）, `IAS, km/h`（指示対気速度）, `M`（マッハ数）, `AoA, deg`（迎角）, `AoS, deg`（横滑り角）, `Ny`（G）, `Vy, m/s`（昇降率）, `Wx, deg/s`（ロールレート）, `Mfuel, kg` / `Mfuel0, kg`（残燃料／満タン量）, `aileron, %` `elevator, %` `rudder, %` `flaps, %` `gear, %`（舵とフラップ、脚）, `airbrake, %`, エンジンごとの `throttle 1, %` `RPM 1` `power 1, hp` `manifold pressure 1, atm` `oil temp 1, C` `water temp 1, C` `thrust 1, kgs` など

## /indicators — 計器の値（乗っているときだけ）
今回は `valid:false` だけだった。乗っている間は次のようなキーが出るとされている ❔
- 共通: `army`（air / tank）, `type`（車両の内部名）
- 航空機: `speed`, `altitude_hour` / `altitude_min`, `compass`, `aviahorizon_roll` / `aviahorizon_pitch`, `vario`, `fuel`, `throttle`, `gears` など（どの計器があるかは機体ごとに違う）
- 地上車両: `speed`, `rpm`, `gear`, `stabilizer`, `crew_total` / `crew_current`, `driver_state`, `gunner_state`, `cruise_control` など

> ❔ の項目は、機体に乗った状態でツールを回すと実際に出てくるので、CSVを取ったらこの表を更新できる。

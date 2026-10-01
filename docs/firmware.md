# Firmware Guide | ファームウェアガイド

[← GeaconEquinox](../README.md)

配線・ビルド・自動化・検証状況をまとめた技術資料です。

> 実機検証は未完了です。GeaconSolsticeとはピン配置が異なるため、ファームウェアを取り違えないでください。

## 構成

| | 左手 / Central | 右手 / Peripheral |
| :-- | :-- | :-- |
| 入力デバイス | PAT9125EL・I²C | PMW3610・3-wire SPI |
| キースキャン | 7線チャーリープレックス、29キー | 7線チャーリープレックス、US/JIS切り替え |
| 接続 | PCへUSB / BLE | 左手へBLE |
| 診断 | USB CDCログ・1200 baud起動トリガー設定 | USB CDCログ・1200 baud起動トリガー設定 |

基板のS0〜S6に使われる拡張ピンを備えたXIAO nRF52840系を想定します。
ソフトウェアのビルドターゲットは `xiao_ble//zmk` です。
ピンの根拠と保留事項は [配線メモ](hardware.md) を参照してください。

## ファームウェア

**左右とも同じ配列の組み合わせを使用してください。**
現在はUS/JISの自動判定ではなく、物理配置に合うファームウェアの選択方式です。

| 物理配列 | 左手 | 右手 |
| :-- | :-- | :-- |
| US | `geacon_equinox_left_us.uf2` | `geacon_equinox_right_us.uf2` |
| JIS | `geacon_equinox_left_jis.uf2` | `geacon_equinox_right_jis.uf2` |

通常レイヤーでカーソル移動、Fn（Space長押し）中はスクロールの初期設定です。
キーマップはGeaconSolstice（`25dbb3f`）のUS/JISを参照した5レイヤー構成です。
FnではF1〜F12・矢印・Home/End・Deleteなどを操作できます。
Caps長押しでBluetoothレイヤーへ移り、数字1〜5でプロファイル0〜4を選択します。
USでは上矢印長押しでもスクロールレイヤーへ移ります。
Mouse/Scrollレイヤーにはマウスボタン割り当てを保持していますが、自動Mouseレイヤー切替は未導入です。
Layout ShiftはSolsticeと同じ固定revisionのモジュールを使用し、US/JISともFn+Tabで切り替えます。
ブートローダー起動はCDCまたは基板のリセット操作を使用してください。
配列の編集対象は `config/GeaconEquinox_US.keymap` / `config/GeaconEquinox_JIS.keymap` です。

## ビルド

`build.yaml` に左右×US/JISの4ターゲットを定義しています。
ZMK本体はcormoranフォーク、外部モジュールはコミットSHAで固定しています。

既存の `te9no/zmk-workspace` に専用west環境を用意した場合：

```sh
ZMK_CONFIG_ROOT=/zmk-workspace/config/zmk-config-GeaconEquinox \
  ./just.sh --profile geacon-equinox build-fast geacon_equinox --pristine=always
```

一般的なwest環境で左USをビルドする場合：

```sh
west build -s zmk/app -b xiao_ble//zmk -d build/equinox-left-us -- \
  -DZMK_CONFIG=/absolute/path/zmk-config-GeaconEquinox/config \
  -DZMK_EXTRA_MODULES=/absolute/path/zmk-config-GeaconEquinox \
  -DSHIELD=geacon_equinox_left \
  -DSNIPPET="equinox-us studio-rpc-usb-uart zmk-usb-logging equinox-cdc"
```

先にこのリポジトリの `config/west.yml` をmanifestにして `west update` を実行してください。
右手には `equinox-right-offset` を追加し、`studio-rpc-usb-uart` を指定しません。

## 自動ビルドとファームウェア保存

GeaconPolarisと同じ共通ワークフローを使用します。

| 実行契機 | 動作 |
| :-- | :-- |
| 毎日05:00 JST（実行時刻は遅れる場合があります） | 左右×US/JISの4構成を検査。ファームのコミットは行いません |
| config・boards・snippetsなどの変更をpush | ビルド成功後、UF2と来歴JSONを同じブランチへ自動コミット |
| Actionsから手動実行 | 対象フィルターと`commit_firmware`で保存の有無を指定 |
| 日次ビルド失敗 | `build-health` Issueを作成、既存の未解決Issueがあればコメントで通知 |

CI生成物は`firmware/<repository>/<branch>/`に保存します（名前は安全な形式へ正規化）。
`firmware/bringup/`はローカルで作成した初期検証用で、Git管理対象外です。
ファームだけのコミットではビルドを再起動しません。日次バッジ更新コミットも生成しません。

GitHubに公開し、ワークフローをデフォルトブランチへ配置すると日次チェックが有効になります。
Actionsの実行と`GITHUB_TOKEN`によるcontents/Issuesへの書き込みを許可してください。
ブランチ保護でbotの直接pushが禁止されている場合は、自動コミットも制限されます。
ローカルへの実装時点ではGitHub上の実行・自動コミットは未検証です。

## 検証状況

| 項目 | 状態 |
| :-- | :-- |
| EasyEDA本体回路図の読み取り | 確認済み（2026-10-01） |
| 左PAT9125ELの配線 | 回路図で確認済み |
| 右PMW3610 | 共用モジュールとの申告に基づく初期配線設定・実機未確認 |
| US/JISの物理キー位置 | 旧Solsticeのレイアウトを初期値として使用・実機未確認 |
| ビルド | `just.sh`で左右×US/JISの4構成成功（2026-10-01） |
| 静的テスト | 4件成功：キー数・US/JIS差分・キースキャンピン・Layout Shift |
| センサー方向・連続動作・BLE・CDC復帰 | 実機未確認 |

LEDは安全のため初期状態で電源OFFです。OLEDは今回の回路図に基づく構成へ追加していません。

ローカルの初期検証用UF2と来歴JSONは `firmware/bringup/` に保存します（リポジトリには含めません）。
最新検証はSolstice由来の5レイヤーとLayout Shiftを含む作業ツリーで実施しました。
入力コミット・未コミット差分の識別情報は各UF2のJSONに記録しています。ログはworkspaceの
`.zmk-workspace/profiles/geacon-equinox/logs/build-parallel-20261001-125625/` です。
StudioのUSB設定は含みますが、接続や各センサーのDYA専用診断を実機確認済みとするものではありません。

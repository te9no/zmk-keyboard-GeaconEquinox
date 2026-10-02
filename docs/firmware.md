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
ZMK_CONFIG_ROOT=/zmk-workspace/config/zmk-keyboard-GeaconEquinox \
  ./just.sh --profile geacon-equinox build-fast geacon_equinox --pristine=always
```

一般的なwest環境で左USをビルドする場合：

```sh
west build -s zmk/app -b xiao_ble//zmk -d build/equinox-left-us -- \
  -DZMK_CONFIG=/absolute/path/zmk-keyboard-GeaconEquinox/config \
  -DZMK_EXTRA_MODULES=/absolute/path/zmk-keyboard-GeaconEquinox \
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

## PAT高分解能ダイヤル

`sekigon-gonnoc/zmk-driver-hires-dial`をrevision
`353a21964a2f6df1de128ca6e71ec63518729ab7`に固定して使用します。
従来のXYカーソル入力を置き換え、PATのY軸を次のように使います。

| レイヤー | PATの動作 |
| --- | --- |
| 0（通常）・2・3・4 | 縦スクロール（10カウントでホイール1） |
| 1（Fn） | Windows Radial Controller（回転比1:1） |
| 5（Dial、長押しで移行） | Windows Radial Controller。Fnを離しても維持 |

US/JIS共通。右TBの方向補正・Fn時スクロールとLayout Shiftは維持します。
Fn＋Enterをダイヤル押下に割り当てています。通常レイヤーのEnterは維持します。
Fnを保持してEnterを長押しするとWindowsの円形メニューを開く操作になります。
ダイヤル押下・回転によるメニュー操作は実機確認が必要です。
さらにFnレイヤー最下段の最初のEnter（通常レイヤーでは左親指Space）を、
短押しEnter／長押しダイヤル押下にしています。隣のEnter 2つは変更しません。
200 msで長押しを確定し、その後Windows側の長押し判定で円形メニューが開きます。
長押し中はダイヤルボタンを保持し、キーを離すと解除します。短押し時はEnterだけを送ります。
現行版では長押し開始でDialレイヤー5を有効にし、キーやFnを離しても維持します。
メニュー表示後は手を離してPATで選択できます。親指の同じキー、またはEnterを
短押しするとダイヤルのクリックを送り、選択後もPATで選んだ機能を操作できます。
Dial中の同じキーを400 ms長押し、またはEscでDialレイヤーを解除し、通常操作へ戻ります。
Fnをまだ保持している間はレイヤー1の設定が有効です。終了時はFnも離してください。
この保持モードは`just.sh`で左右US/JISの4構成ビルド成功、静的テスト14件成功。
ログ：`build-parallel-20261002-091332`。左手の接続を検出できず未書き込みです。
メニューと選択の実機確認が必要です。
この親指キー追加版は`just.sh`で左右US/JISの4構成ビルド成功、静的テスト13件成功。
ログ：`build-parallel-20261002-083607`。2026-10-02、CDC 1200 baudから左手を
ブートローダーへ移行し、Hドライブへ左US版を書き込みました。
CDC復帰とPATの`ready=1 init_res=0 id=31:91`を確認済み。
親指キーの短押し・長押しと円形メニュー操作の実機確認は保留です。
`res-cpi=1275`、`counts-per-revolution=1275`は上流の参考初期値であり、
実際のダイヤル1回転に合わせた校正と、方向・速度の実機確認が必要です。
I²C 0x79、ID_SEL高インピーダンス、MOTION=P1.12は維持しています。

固定中のcormoran ZMKとの互換性のため、EquinoxのCMakeでZMKヘッダ参照と
`zmk_endpoints_selected`→`zmk_endpoint_get_selected`のAPI名対応を追加しています。
上流モジュール自体は変更していません。
Radial Controllerの追加HID用に未使用の標準CDCだけ無効化しています。
Studio CDCとデバッグ/1200 baud起動CDCは維持しますが、COM番号は変わる可能性があります。
BLEではHID構成変更により再ペアリングが必要になる場合があります。
移行版は実機でPAT初期化成功とWindowsの多軸コントローラ認識を確認し、
ユーザーから通常スクロール動作OKの報告を得ています。
Fn＋Enter追加版は`just.sh`で左右US/JISの4構成ビルド成功、静的テスト12件成功。
2026-10-02に左US版をHドライブ経由で書き込み、CDCでhires dialの初期化成功と
`ready=1 init_res=0 id=31:91`を確認しました。円形メニューと回転の操作確認は保留です。
ビルドログ：`build-parallel-20261002-082735`。

## CDCデバッグログ

右手は`CONFIG_EQUINOX_PMW_DIAGNOSTICS=y`で、PMWの非同期初期化状態・
エラー・IRQピン・Central接続状態を5秒ごとに出力します。
2026-10-02の右USビルドは成功（`build-parallel-20261002-075019`）。
書き込み後、CDCで`ready=1 init_error=0 split_connected=1`を確認しました。
続いて左Centralで右TBのY軸だけを反転し、左USをビルド・書き込みしました
（`build-parallel-20261002-075413`）。ユーザーから方向OKの確認済みです。
後続のhires-dial移行時に左右US/JISの4構成ビルドは成功しました。
さらに基板180度回転に合わせ、右TB補正をY反転からX反転へ変更しています。
この後続変更の書き込み・実機確認と、長時間動作は未確認です。

### PAT初期化の切り分け（2026-10-02）

Zephyr内蔵PAT912xでは`ready=0 init_res=5`。起動後のI²C製品ID読み取りは
`id_rc=0 id=31:91`で成功し、初期化を10秒遅らせても失敗しました。
TBENCの参照先である`taichan1113/zmk-driver-pat9125`の固定revision
`17395b89a85b8d4fccbff5d4b53cd39cc3a88961`へ切り替え、左USを書き込みました。
CDCで`ready=1 init_res=0`とXYログを確認済みです。
参照ドライバは標準版と異なりソフトウェアリセットを実行しません。
当初はこれを原因の有力候補としましたが、その後再発しています。
再発時は0x75の製品ID読み取りも失敗し、0x79で31:91が読めました。
この時点の直接原因はアドレス不一致です。ID_SELを高インピーダンス入力に変更し、
0x79に揃えた左US版で`ready=1 init_res=0`とXYログを確認しました。
ログ：`.zmk-workspace/profiles/geacon-equinox/logs/build-parallel-20261002-065940/`。
完全な電源断後の再確認は未実施で、リセット処理だけが原因とは断定しません。
カーソル方向・連続操作の実機確認は別途必要です。

`CONFIG_EQUINOX_PAT_DIAGNOSTICS=y`で独立スレッドから5秒ごとに準備状態・
製品ID・MOTIONピンを表示します。追加の初期化やリセット書き込みは行いません。
この診断出力はログキューとは別の`printk`経路を使います。

左右とも専用USB CDCコンソールでDEBUGログを出力します。CentralのStudio RPC用ポートとは別です。
通常のログ閲覧には115200 baudを使い、1200 baudはブートローダー起動専用にしてください。
LEDアニメーション・電源制御はZMKのDEBUG、左PAT9125はINPUTのDEBUG、
右PMW3610と3-wire SPIはそれぞれのDEBUGレベルを有効にしています。
遅延ログ方式・8 KiBバッファ・起動後8秒のログ処理開始待ちを設定しています。
これはセンサー初期化を8秒遅らせる設定ではなく、起動時ログの保持も保証しません。
USBドライバ自身のログは、USB経由の再帰ログを避けるため無効です。
大量出力によるログ欠落・タイミングへの影響があり得る診断設定です。
キー操作を含む可能性があるため、ログ取得中は機密情報を入力しないでください。

2026-10-02、`just.sh`でDEBUG有効の4構成ビルド成功。
ログ：`.zmk-workspace/profiles/geacon-equinox/logs/build-parallel-20261002-045203/`。
その後、左右ともCDCでセンサー診断ログを受信できることを確認しました。

## LEDの動作

SparAkashaAnantaのLED構成を参照し、左右各4灯のWS2812とXIAO内蔵RGBを有効にしています。

- 起動時：電池残量 → 消灯 → 接続状態。
- USB給電中：接続状態と虹色アニメーション。
- バッテリー駆動中：常時アニメーションなし。復帰時などに電池残量を表示。
- 接続表示：接続済み青、未接続赤、オープン黄、USB緑（左右の役割に応じて表示）。
- 内蔵RGB：電池・接続・レイヤー変更の状態表示。

SPI3はLED専用、右PMW3610はソフトウェア3-wire SPIであり、バスを共有しません。
左右へのレイヤー状態の同期や点灯の見え方は実機未確認です。
2026-10-02に`just.sh`でLED込みの左右×US/JISビルド4件成功。
ログ：`.zmk-workspace/profiles/geacon-equinox/logs/build-parallel-20261002-043407/`。
OLEDは今回の回路図に基づく構成へ追加していません。

ローカルの初期検証用UF2と来歴JSONは `firmware/bringup/` に保存します（リポジトリには含めません）。
最新検証はSolstice由来の5レイヤーとLayout Shiftを含む作業ツリーで実施しました。
入力コミット・未コミット差分の識別情報は各UF2のJSONに記録しています。ログはworkspaceの
`.zmk-workspace/profiles/geacon-equinox/logs/build-parallel-20261001-125625/` です。
StudioのUSB設定は含みますが、接続や各センサーのDYA専用診断を実機確認済みとするものではありません。

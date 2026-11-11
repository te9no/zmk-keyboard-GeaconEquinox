# Equinox nemu-link / Dynamic Settings

US・JISの左右と、専用nemu-linkドングル向けの構成です。
通常版の `config/west.yml` と `build.yaml` はそのまま残しています。

## 構成

- 左XIAO: キー、PAT9125ダイヤル。送信元ID 0。
- 右XIAO: キー、PMW3610トラボ。送信元ID 1。
- nemu-linkドングル: キーマップ、USB出力、Dynamic Settings、トラボ処理。
- この構成は独自2.4GHz専用です。左右のUSBは鍵登録用で、キー入力はドングルから出ます。
- US/JISの物理配列と右トラボの向き、PATのアドレス正規化、PMWガードを継承します。
- ダイヤルは通常スクロール、Fn/DialレイヤーはRadial Controllerとして処理します。
- 4連LEDの状態アニメはこの構成では無効で、電源を切ります。

## 設定

[nemu-link Studio](https://nemu-link-studio.pages.dev/) を使用します。
Dynamic Settingsのトラボ設定はドングルが保持します。感度・スクロール・AMLを変更できます。
初期値は等倍・加速なし・AML無効、Fn（レイヤー1）でスクロールです。
物理的な取付方向の補正はDynamic Settingsの前に適用します。
キーマップと設定はドングルへ保存してください。通常版の独自RPC設定とは共有しません。
センサーCPIとダイヤル割り当てのDynamic Settings化は含みません。

## ビルド

Zephyr SDKとwestを用意し、このリポジトリとは別の作業ディレクトリで実行します。
以下の `/path/to/equinox` はこのチェックアウトの絶対パスへ置き換えてください。

```sh
mkdir equinox-nemu-west
cd equinox-nemu-west
cp -r /path/to/equinox/nemu manifest
west init -l manifest
west update
west zephyr-export
pip install -r zephyr/scripts/requirements.txt
python3 /path/to/equinox/scripts/build_nemu.py --workspace "$PWD" --output "$PWD/firmware" --target all
```

全6ターゲットを `build-nemu.yaml` で定義しています。単体ビルドは `--target equinox_nemu_left_us` などを指定します。
依存元は `nemu/west.yml` のコミットへ固定しています。通常版のwest環境とは混ぜないでください。

## 書き込みと鍵登録

1. US/JISが揃った左・右・ドングルの3ファイルを選びます。
2. 左右は各XIAOのUF2ブートローダーへ、ドングルはnemu-link専用ボードへ書き込みます。
3. 左右とドングルをUSB接続し、nemu-link Studioの管理画面で同一の鍵と通信アドレスを3台へ登録します。
4. 鍵のバックアップを保存し、3台を再起動します。

XIAOはアプリ領域末尾の1ページ（0xeb000）を鍵保存に予約します。既存settingsとブートローダーは変更しません。
一般のXIAOやHolyiotへ **ドングル用UF2をコピーしないでください**。専用ドングルとフラッシュ配置が異なります。

## 検証範囲

実機の通信・USB列挙・鍵登録・Dynamic Settings保存復元・ダイヤル・トラボは未確認です。
書き込み前にビルド結果と利用するボードを確認してください。省電力と長時間安定性も実機での確認が必要です。

### 開発時の確認

- SDK 0.16.9、固定したZMK/Zephyr/nemu-link依存でUS/JIS × 左/右/ドングルの6ターゲットをビルド。
- `scripts/verify_nemu_builds.py` で生成済みDevicetree/Kconfigを検査。63/64キーの行列共有、右側オフセット、送信元ID、入力デバイス、US/JIS方向補正、鍵保存領域、Dynamic Settings有効化を確認。
- `python3 -m unittest discover -s tests -v`: 26件成功。電池換算は全uint16電圧範囲で単調性と0〜100%を検査。
- 専用ワークフローは追加済み。GitHub上での実行は未実施。
- 上流のperipheral用Studioバッファ設定、非推奨KSCAN、未使用変数の警告は残ります。ビルド成功を実機動作の保証とは扱いません。

## CDC経由のブートローダー起動

左右・ドングルとも `Equinox bootloader` の専用CDCポートを追加しています。
そのポートを **1200 baud、DTR有効で開き、0.5秒程度待って閉じる**とUF2ブートローダーへ移ります。
単に開いたままでは移行しません。ログ出力用ポートではありません。

左右はCDCが各1つ、ドングルはDynamic Settings用とブートローダー用の2つです。
ブートローダートリガーは専用ポートだけを監視し、鍵登録用HIDとStudio RPC用CDCは対象にしません。
COM番号は接続先PCで確認してください。この版を初めて書き込むときは既存のブートローダー起動方法を使います。

通常版と同じ固定版のCDCトリガーモジュールを使用します。ポート状態の監視は100ms間隔のため、
短すぎる開閉は検出されない場合があります。実機での自動再起動と再列挙は未確認です。

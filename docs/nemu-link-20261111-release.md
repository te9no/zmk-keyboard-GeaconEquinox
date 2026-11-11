# GeaconEquinox nemu-link — 2026-11-11

GeaconEquinox向けの独自2.4GHz・専用ドングル構成です。開発ブランチは `Nemu-link`。通常版とは別系統で、Dynamic Settingsに対応します。

## ダウンロード

同じ配列の左・右・ドングルの3ファイルを使用してください。

| 配列 | 左手 | 右手 | 専用ドングル |
|---|---|---|---|
| JIS | `equinox_nemu_left_jis.uf2` | `equinox_nemu_right_jis.uf2` | `equinox_nemu_dongle_jis.uf2` |
| US | `equinox_nemu_left_us.uf2` | `equinox_nemu_right_us.uf2` | `equinox_nemu_dongle_us.uf2` |

ドングル用はnemu-link専用ボード向けです。XIAOや他のレシーバーへ書き込まないでください。

## 対応内容

- 左右のキー、右トラボ、左ダイヤルを専用ドングルへ転送。
- Dynamic Settingsでトラボの感度・スクロール・AMLを設定。初期状態は加速なし・AML無効。
- US/JISの配列・トラボ方向補正、PATアドレス正規化、PMWガード、NiMH電池換算を継承。
- 全3台に1200 baudのCDCブートローダートリガー。専用CDCをDTR有効・1200 baudで開き、0.5秒程度待って閉じると起動します。
- ドングルの設定用CDCとブートローダー用CDCは別ポートです。

## 導入

初回書き込み後は、[nemu-link Studio](https://nemu-link-studio.pages.dev/)で3台へ同じ鍵・通信アドレスを登録してください。
[導入手順](https://github.com/te9no/zmk-keyboard-GeaconEquinox/blob/Nemu-link/docs/nemu-link.md)にビルド方法と設定範囲を記載しています。

この構成は独自2.4GHz専用で、左右のUSBは鍵登録・書き込み用です。4連LEDアニメは無効にし、LED電源を遮断します。通常版の独自RPC設定とは共有しません。

## 検証範囲

- JIS版は左右・ドングルに適用し、利用者から動作確認を得ています。
- 3台の書き込み内容を読み戻してUF2との一致を確認。1200 baudでのブートローダー起動とUSB再列挙も確認しました。
- US/JIS全6ターゲットをビルドし、生成された配列・送信元ID・方向補正・フラッシュ領域・CDC分離を検査。
- 回帰テスト26件成功。
- US版の実機動作、Dynamic Settingsの保存復元、各入力機能の網羅試験、長時間安定性・消費電力は未確認です。

各UF2の証跡JSONと `SHA256SUMS` を添付します。通常版のLatestは変更しません。

# GeaconEquinox 配線・検証メモ

2026-10-01にEasyEDA APIでGeaconSolstice3の左右回路図を読み取り。
EasyEDAの回路図やプロジェクト名自体は変更していません。

| 用途 | ネット | GPIO |
| --- | --- | --- |
| キースキャン | S0 / S1 / S2 | P0.15 / P0.19 / P1.01 |
| キースキャン | S3 / S4 / S5 / S6 | P0.09 / P0.10 / P1.03 / P1.05 |
| キー割り込み | INT | P0.28 |
| 左PAT9125EL I²C | SDA / SCL | P0.04 / P0.05 |
| 左PAT9125EL | NCS (ID_SEL) / MOTION | P1.11 / P1.12 |
| 右J5 pin 1 / pin 2 | EXT_1 / EXT_2 | P1.11 / P1.12 |
| 右J5 pin 3 / pin 4 | AD_Y1 / AD_X1 | P0.04 / P0.03 |
| 右J5 pin 5 / pin 6 | VCC / POWER_GND | 3.3 V / GND |
| LED DATA / 電源ゲート | LED_L / LED_EN_L | P0.29 / P1.13 |

右ページでもネット名に `_L` が含まれるため、ネット名ではなくページとU103のピン番号で区別。
MCU記号の名称は `mcu_xiao-ble` ですが、拡張端子を使っています。
標準XIAOの外周端子だけではこのピン割り当てを再現できません。

PAT9125ELはID_SELをGPIO hogでlowにして0x75を指定。
この接続は回路図で確認済みですが、起動時のID_SELのサンプリングタイミングは実機確認が必要です。
TBENC実装のX反転・Y反転を初期値として使い、搭載方向の正しさは未確認です。

右PMW3610は既存共用モジュールとのユーザー申告に基づき、J5を
CS / MOTION / SDIO / SCLK / VCC / GND の順として実装しています。
本体回路図は信号の用途をEXT_1等と表記しているため、モジュール内部との対応は実機で再確認してください。

各キーはD4xx側のSネットがcolumn、キーダイオードのSネットがrow。
左29キー、右35スイッチの接続を取得。US配列は右の1位置を使用しません。
右のmatrix column offsetは8。配列は左右共通なので、US/JISを変えるときは左右を揃えます。

未使用UART・ハードウェアSPI・右I²Cを無効化し、NFCピンをGPIOへ解放。
LEDはPチャネルFETゲートをhighにしてOFF。LED動作は未実装です。
ボード標準のバッテリー読み取りは維持し、外部INPUT_VOLTAGE_Aは未使用です。

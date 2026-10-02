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

PAT9125ELはID_SEL（P1.11）をpullなし入力の高インピーダンスに保ち、0x79を指定。
旧設定はGPIO hogでlowにして0x75を指定していましたが、再発時の実機では
0x75がI/Oエラー、0x79が製品ID31:91を返すことを確認しました。
センサー起動時はMCUがまだID_SELを駆動できず、NC相当のアドレスを選んだ可能性があります。
0x79版で初期化成功・XYログを確認済み。完全な電源断後の再現性は未確認です。
TBENC実装のX反転・Y反転を初期値として使い、搭載方向の正しさは未確認です。

右PMW3610の実機確認済み設定は、J5の順に
CS / SCLK / MOTION / SDIO / VCC / GNDです。
SCLK=P1.12、SDIO=P0.03、CS=P1.11、MOTION=P0.04。
本体回路図の接続はEasyEDAで照合済みですが、モジュール内部の回路図は今回の確認対象外です。
2026-10-02、右US版を書き込み、CDCで`ready=1 init_error=0 split_connected=1`を確認しました。
左Centralの右TB専用リスナーでY軸のみ反転し、ポインターとスクロールの両経路へ適用。
左US版の書き込み後、ユーザーから方向OKの確認を得ました。長時間動作は未確認です。

各キーはD4xx側のSネットがcolumn、キーダイオードのSネットがrow。
左29キー、右35スイッチの接続を取得。US配列は右の1位置を使用しません。
右のmatrix column offsetは8。配列は左右共通なので、US/JISを変えるときは左右を揃えます。

未使用UART・ハードウェアSPI・右I²Cを無効化し、NFCピンをGPIOへ解放。
LEDはSparAkashaAnantaのアニメーション構成を参照し、左右各4灯のWS2812をSPI3/P0.29で駆動。
PチャネルFETゲートP1.13はactive-lowで、ext-power-transientモジュールが管理します。
従来の電源OFF固定GPIO hogは削除し、電源制御の二重所有を避けています。
XIAO内蔵RGBはP0.26（赤）・P0.30（緑）・P0.06（青）を使用します。
LEDの色・順序・点灯タイミングは実機未確認です。
ボード標準のバッテリー読み取りは維持し、外部INPUT_VOLTAGE_Aは未使用です。

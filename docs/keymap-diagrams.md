# キーマップ図の更新

`scripts/draw_keymaps.py`は、`config/GeaconEquinox_*.keymap`の全レイヤーと
`snippets/equinox-*/equinox-*.overlay`の物理キー位置からSVGを生成します。
追加のDialレイヤーも読み取り、各レイヤーのキー数が物理配列と違う場合は失敗します。
独自ビヘイビアの表示名はスクリプトの`aliases`で定義しています。

描画には[zmk-workspace](https://github.com/te9no/zmk-workspace)の共通ツールを使います。
再現性のため、CIでは`a49f67f5ab5392d45bb3209d68f0f17594f62d9a`に固定しています。

Python 3で、リポジトリ直下から実行します（追加パッケージ不要）。

```sh
git clone https://github.com/te9no/zmk-workspace /tmp/equinox-keymap-tools
git -C /tmp/equinox-keymap-tools checkout a49f67f5ab5392d45bb3209d68f0f17594f62d9a
python3 scripts/draw_keymaps.py --tools-dir /tmp/equinox-keymap-tools/scripts
python3 scripts/draw_keymaps.py --tools-dir /tmp/equinox-keymap-tools/scripts --check
```

GitHub Actionsは関連ソースのpushまたは手動実行時だけ動きます。
SVGの内容が変わった場合だけ同じブランチへコミットし、日次実行はしません。
保護ブランチなどで書き込みが許可されない場合は、ローカルで生成したSVGを通常の変更と一緒に反映してください。
ファームウェアのビルド・書き込みは行いません。

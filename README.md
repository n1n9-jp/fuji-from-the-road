# fuji-from-the-road

東名・名神高速道路（東京〜西宮）を走る車から、富士山がどの方向に、どれだけ離れてあるかを見る2つの図です。

- **[まっすぐな道と、動く富士山](https://n1n9-jp.github.io/fuji-from-the-road/)**（平面版）
  地図のままの表示と、道路を直線に伸ばした表示をスイッチで切り替えます。直線化しても各地点から富士山への方向と距離は変えないので、富士山のほうが地点ごとに別の場所へ移ります。
- **[運転席から見る富士山](https://n1n9-jp.github.io/fuji-from-the-road/drive/)**（3D版）
  同じ計算を、フロントガラスとルームミラーの眺めにしたものです。下り・上りを選んで走らせると、道が曲がるたびに富士山が左右へ動きます。

着想は杉浦康平のダイアグラム「右往左往する富士山の地図」です。同じ考え方を公開データから計算し直した習作で、原図を再現したものではありません。

## 構成

| パス | 内容 |
| --- | --- |
| `index.html` | 平面版。SVG を JavaScript で描画。外部ライブラリなし |
| `drive/index.html` | 3D版。three.js r128 を cdnjs から読み込み |
| `data.js` | 2ページ共通のデータ（道路の線形、IC の位置、陸地、湖）。`tools/build_data.py` が生成 |
| `tools/build_data.py` | Natural Earth の GeoJSON から `data.js` を作るスクリプト |
| `.nojekyll` | GitHub Pages に、ファイルをそのまま配信させるための空ファイル |

ビルド工程はありません。リポジトリのルートをそのまま静的サイトとして配信します。

## 計算

- 座標は富士山頂（剣ヶ峰、北緯35.3606度・東経138.7274度）を中心とする正距方位図法で、単位は km です。富士山からの距離と方位がそのまま図上に表れます。
- 道路は 1 km 間隔の点列です。各地点での道路の向きは、前後の点を結ぶ向きで決めています。元の線形に ±2 km の移動平均を2回かけているので、数 km より細かいカーブは反映されません。
- 平面版の直線化は、道路の長さを保ったまま曲がりだけを 0 にする変形です。各地点は、富士山への距離と、道路の向きに対する角度を保ちます。
- 40地点は、東京から西宮まで道のり等間隔です。
- 3D版は見やすさのために誇張しています。視点は路面から 600 m の高さ、道路の幅は 400 m、富士山の高さは2倍です。地面は平らで、地球の丸みは無視しています。

## データの限界

- Natural Earth（1:1000万）の道路は簡略化されています。図の上の道のりは約 500 km で、実際の東京IC〜西宮IC より短く、位置にも数 km のずれがあります。
- IC の位置は概略の経緯度を道路上の最寄りの点に寄せたものです。
- 遠い地点では、実際には富士山は見えません。方向と距離は地図上の計算です。

## データを作り直す

```sh
pip install shapely numpy
# https://github.com/nvkelso/natural-earth-vector/tree/master/geojson から
# ne_10m_roads.geojson, ne_10m_land.geojson, ne_10m_lakes.geojson を取得
python3 tools/build_data.py ne_10m_roads.geojson ne_10m_land.geojson ne_10m_lakes.geojson
```

## 手元で見る

```sh
python3 -m http.server 8000
# http://localhost:8000/ を開く
```

## 利用しているもの

- [Natural Earth](https://www.naturalearthdata.com/)（パブリックドメイン）: 道路、陸地、湖
- [three.js](https://threejs.org/) r128（MIT License）: 3D版の描画
- [Zen Kaku Gothic New](https://fonts.google.com/specimen/Zen+Kaku+Gothic+New)、[Zen Old Mincho](https://fonts.google.com/specimen/Zen+Old+Mincho)（SIL Open Font License）: Google Fonts から読み込み

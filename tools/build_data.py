#!/usr/bin/env python3
"""data.js を作り直すスクリプト。

Natural Earth (1:10m) の GeoJSON から、東京IC〜西宮IC の高速道路の線形と
周辺の陸地・湖を取り出し、富士山頂を中心とする正距方位図法 (km) に投影して
../data.js に書き出す。

使い方:
    pip install shapely numpy
    python3 tools/build_data.py ne_10m_roads.geojson ne_10m_land.geojson ne_10m_lakes.geojson

入力ファイルの入手先:
    https://github.com/nvkelso/natural-earth-vector/tree/master/geojson
"""
import heapq
import json
import math
import os
import sys

import numpy as np
from shapely.geometry import Polygon, box, shape

FUJI = (138.7274, 35.3606)  # 経度, 緯度（剣ヶ峰）
R = 6371.0

# 名前, 経度, 緯度（概略位置）, ラベルの優先度, 地図ビューでのラベルの向き
IC = [
    ('東京', 139.6268, 35.6265, 1, 'n'), ('横浜町田', 139.4670, 35.5083, 3, 's'),
    ('厚木', 139.3620, 35.4283, 2, 's'), ('御殿場', 138.9480, 35.3040, 1, 'e'),
    ('沼津', 138.8600, 35.1390, 3, 's'), ('富士', 138.6722, 35.1801, 1, 's'),
    ('静岡', 138.4060, 34.9560, 1, 's'), ('浜松', 137.7830, 34.7720, 1, 's'),
    ('岡崎', 137.1900, 34.9330, 2, 's'), ('名古屋', 137.0110, 35.1790, 1, 'e'),
    ('小牧', 136.9360, 35.2890, 3, 'n'), ('岐阜羽島', 136.6860, 35.3180, 2, 'n'),
    ('彦根', 136.2720, 35.2500, 1, 'e'), ('大津', 135.8690, 34.9930, 2, 's'),
    ('京都南', 135.7470, 34.9400, 3, 's'), ('吹田', 135.5330, 34.7930, 2, 'n'),
    ('西宮', 135.3690, 34.7220, 1, 's'),
]
# 経路探索で必ず通す IC（Natural Earth の線に近いものだけ）
VIA = ['東京', '厚木', '御殿場', '富士', '静岡', '浜松', '小牧', '岐阜羽島', '大津', '京都南', '吹田', '西宮']


def aeqd(lon, lat, lon0=FUJI[0], lat0=FUJI[1]):
    """富士山頂を中心とする正距方位図法。戻り値は (東向き km, 北向き km)。"""
    lam, phi = math.radians(lon), math.radians(lat)
    lam0, phi0 = math.radians(lon0), math.radians(lat0)
    cosc = math.sin(phi0) * math.sin(phi) + math.cos(phi0) * math.cos(phi) * math.cos(lam - lam0)
    c = math.acos(max(-1, min(1, cosc)))
    k = 1.0 if c < 1e-12 else c / math.sin(c)
    x = R * k * math.cos(phi) * math.sin(lam - lam0)
    y = R * k * (math.cos(phi0) * math.sin(phi) - math.sin(phi0) * math.cos(phi) * math.cos(lam - lam0))
    return (x, y)


def hav(a, b):
    la1, p1, la2, p2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin((la2 - la1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def load_segments(path):
    """東京〜西宮を含む範囲の道路。種別 Unknown（一般道）は使わない。"""
    def inbox(c):
        return 134.8 < c[0] < 140.2 and 34.2 < c[1] < 36.2
    segs = []
    for f in json.load(open(path))['features']:
        g = f['geometry']
        if g is None or f['properties']['type'] == 'Unknown':
            continue
        lines = [g['coordinates']] if g['type'] == 'LineString' else g['coordinates']
        for ln in lines:
            if any(inbox(c) for c in ln):
                segs.append((f['properties']['type'], ln))
    return segs


def find_route(segs):
    """IC を順につないだ最短経路（東京 → 西宮）の経度緯度列。"""
    nodes, adj, coords = {}, {}, {}

    def nid(c):
        k = (round(c[0], 4), round(c[1], 4))
        if k not in nodes:
            nodes[k] = len(nodes)
            adj[nodes[k]] = []
        return nodes[k]

    for typ, ln in segs:
        w = 1.0 if typ == 'Major Highway' else 1.5
        for a, b in zip(ln[:-1], ln[1:]):
            ia, ib = nid(a), nid(b)
            coords[ia], coords[ib] = a, b
            d = hav(a, b)
            adj[ia].append((ib, d * w))
            adj[ib].append((ia, d * w))
    # ほぼ同じ位置で途切れている線の端どうしをつなぐ
    ends = list({nid(c) for _, ln in segs for c in (ln[0], ln[-1])})
    for i in ends:
        for j in ends:
            if i < j:
                d = hav(coords[i], coords[j])
                if d < 1.5:
                    adj[i].append((j, d))
                    adj[j].append((i, d))

    def nearest(pt):
        return min(coords, key=lambda i: hav(coords[i], pt))

    def dijkstra(a, b):
        dist, prev, pq = {a: 0}, {}, [(0, a)]
        while pq:
            d, u = heapq.heappop(pq)
            if u == b:
                break
            if d > dist.get(u, 1e18):
                continue
            for v, w in adj[u]:
                nd = d + w
                if nd < dist.get(v, 1e18):
                    dist[v], prev[v] = nd, u
                    heapq.heappush(pq, (nd, v))
        path = [b]
        while path[-1] != a:
            path.append(prev[path[-1]])
        return path[::-1]

    way = [nearest((lo, la)) for n, lo, la, _, _ in IC if n in VIA]
    path = [way[0]]
    for a, b in zip(way[:-1], way[1:]):
        if a != b:
            path += dijkstra(a, b)[1:]
    return [coords[i] for i in path]


def resample(p, step):
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
    n = int(round(d[-1] / step))
    t = np.linspace(0, d[-1], n + 1)
    return np.c_[np.interp(t, d, p[:, 0]), np.interp(t, d, p[:, 1])]


def smooth(p, half):
    """移動平均。両端の点は動かさない。"""
    out = p.copy()
    for i in range(len(p)):
        h = min(half, i, len(p) - 1 - i)
        out[i] = p[i - h:i + h + 1].mean(axis=0)
    return out


def polygons(path, bbox, min_area):
    def proj(poly):
        def ring(r):
            return [aeqd(x, y) for x, y in r.coords]
        return Polygon(ring(poly.exterior), [ring(h) for h in poly.interiors])
    out = []
    for f in json.load(open(path))['features']:
        g = shape(f['geometry'])
        if not g.intersects(bbox):
            continue
        g = g.intersection(bbox)
        for poly in (g.geoms if hasattr(g, 'geoms') else [g]):
            if poly.geom_type != 'Polygon' or poly.is_empty:
                continue
            q = proj(poly).simplify(0.9, preserve_topology=True)
            if q.area > min_area:
                out.append(q)
    return out


def rings(polys):
    return [[[round(x, 1), round(y, 1)] for x, y in q.exterior.coords] for q in polys]


def main(roads, land, lakes):
    ll = find_route(load_segments(roads))
    raw_km = sum(hav(a, b) for a, b in zip(ll[:-1], ll[1:]))
    xy = np.array([aeqd(*c) for c in ll])[::-1]        # 西（西宮）→ 東（東京）
    p = resample(xy, 0.5)
    p = smooth(smooth(p, 4), 4)                         # ±2 km の移動平均を2回
    p = resample(p, 1.0)
    u = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
    print('route: %.1f km raw, %.1f km smoothed, %d points' % (raw_km, u[-1], len(p)))

    ics = []
    for n, lo, la, pr, side in IC:
        q = np.array(aeqd(lo, la))
        i = int(np.argmin(np.hypot(*(p - q).T)))
        ics.append({'n': n, 'u': round(float(u[i]), 1), 'p': pr, 'side': side,
                    'off': round(float(np.hypot(*(p[i] - q))), 1)})

    bbox = box(132.6, 32.4, 142.2, 38.2)
    data = {
        'route': [[round(float(x), 2), round(float(y), 2)] for x, y in p],
        'ics': ics,
        'land': rings(polygons(land, bbox, 12)),
        'lakes': rings(polygons(lakes, bbox, 40)),
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data.js')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('// tools/build_data.py が生成するファイル。手で編集しない。\n')
        f.write('// 単位は km。x が東、y が北。原点は富士山頂。route は西宮 → 東京の順。\n')
        f.write('window.FUJI_DATA = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')
    print('wrote', os.path.normpath(out), os.path.getsize(out), 'bytes')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])

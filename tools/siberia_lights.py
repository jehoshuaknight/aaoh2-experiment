"""Add Siberian cities (cities.tsv) and their 2240 night lights (Earth_lights.jpg).
usage: python3 -I siberia_lights.py <src AstraNovum> <dst AstraNovum>
"""
import sys, os
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
SRC, DST = sys.argv[1], sys.argv[2]
TB = 'bin/game/textures/bodies/'

# Real Siberian and Far Eastern cities: name, lat, lon, population today (approx., 2020s)
CITIES = [
 ("Omsk",54.9885,73.3242,1110000),("Krasnoyarsk",56.0153,92.8932,1190000),("Tyumen",57.1522,65.5272,850000),
 ("Barnaul",53.3561,83.7636,630000),("Irkutsk",52.2896,104.2806,620000),("Tomsk",56.4977,84.9744,570000),
 ("Kemerovo",55.3547,86.0873,550000),("Novokuznetsk",53.7596,87.1216,540000),("Khabarovsk",48.4802,135.0719,620000),
 ("Ulan-Ude",51.8335,107.5841,440000),("Surgut",61.2500,73.4167,400000),("Chita",52.0340,113.4994,350000),
 ("Yakutsk",62.0355,129.6755,360000),("Kurgan",55.4410,65.3411,300000),("Nizhnevartovsk",60.9344,76.5531,280000),
 ("Komsomolsk-on-Amur",50.5500,137.0000,240000),("Blagoveshchensk",50.2667,127.5333,240000),("Angarsk",52.5448,103.8885,220000),
 ("Bratsk",56.1514,101.6340,220000),("Biysk",52.5414,85.2196,190000),("Abakan",53.7212,91.4424,190000),
 ("Norilsk",69.3535,88.2027,180000),("Petropavlovsk-Kamchatsky",53.0167,158.6500,180000),("Rubtsovsk",51.5147,81.2061,140000),
 ("Novy Urengoy",66.0833,76.6333,120000),("Kyzyl",51.7191,94.4378,120000),("Achinsk",56.2694,90.4993,105000),
 ("Noyabrsk",63.1994,75.4507,105000),("Tobolsk",58.1981,68.2645,100000),("Khanty-Mansiysk",61.0042,69.0019,100000),
 ("Berdsk",54.7581,83.1072,100000),("Prokopyevsk",53.8833,86.7167,190000),("Magadan",59.5638,150.8030,90000),
 ("Minusinsk",53.7104,91.6872,70000),("Kansk",56.2050,95.7197,90000),("Ust-Ilimsk",57.9573,102.7301,80000),
 ("Nerungri",56.6600,124.7200,57000),("Belogorsk",50.9214,128.4739,65000),("Usolye-Sibirskoye",52.7500,103.6500,75000),
 ("Lesosibirsk",58.2333,92.4833,60000),("Svobodny",51.4000,128.1333,55000),("Mirny",62.5353,113.9611,35000),
 ("Salekhard",66.5300,66.6019,50000),("Lensk",60.7253,114.9278,24000),("Ust-Kut",56.7930,105.7710,40000),
 ("Severobaykalsk",55.6333,109.3167,24000),("Tynda",55.1542,124.7469,30000),("Kirensk",57.7853,108.1119,11000),
 ("Igarka",67.4667,86.5833,5000),("Dudinka",69.4058,86.1778,20000),("Turukhansk",65.7930,87.9500,5000),
 ("Olyokminsk",60.3744,120.4264,9000),("Vilyuysk",63.7553,121.6247,10000),("Aldan",58.6031,125.3894,20000),
]

# Corridors where 2240 growth strings small towns along (rail, rivers): polylines of (lat, lon)
CORRIDORS = [
 [(56.8,60.6),(57.15,65.5),(55.0,73.3),(55.03,82.96),(56.0,92.9),(56.2,95.7),(54.5,100.0),(52.3,104.3),(51.8,107.6),(52.0,113.5),(53.0,119.0),(51.0,128.0),(48.5,135.0)],  # Trans-Siberian
 [(56.15,101.6),(56.8,105.8),(55.6,109.3),(56.4,115.0),(55.15,124.7),(51.5,136.0),(50.55,137.0)],                                                  # BAM
 [(53.35,83.8),(55.03,82.96),(56.5,85.0),(58.0,82.0),(60.9,76.6),(61.25,73.4),(61.0,69.0),(63.0,67.0),(66.5,66.6)],                                 # Ob
 [(53.7,91.4),(56.0,92.9),(58.2,92.5),(61.6,90.1),(65.8,88.0),(67.5,86.6),(69.4,86.2)],                                                           # Yenisei
 [(56.8,105.8),(57.8,108.1),(60.7,114.9),(60.4,120.4),(62.0,129.7),(63.8,121.6)],                                                                 # Lena
 [(55.15,124.7),(56.66,124.7),(58.6,125.4),(62.0,129.7)],                                                                                          # AYaM / Amur-Yakutsk
 [(57.15,65.5),(58.2,68.3),(61.0,69.0)],                                                                                                           # Irtysh
 [(53.76,87.1),(53.7,91.4),(51.7,94.4)],                                                                                                           # Kuzbass-Tuva
]

def main():
    lp = os.path.join(SRC, TB + 'Earth_lights.jpg')
    L = np.array(Image.open(lp).convert('L'), np.float32)
    H, W = L.shape
    water = np.array(Image.open(os.path.join(SRC, TB + 'Earth_water.png')).convert('L').resize((W, H), Image.NEAREST)) > 127

    def px(lat, lon): return (lon + 180) / 360 * W, (90 - lat) / 180 * H

    # calibrate against Novosibirsk (1.39 M today), already lit in the map
    nx, ny = px(55.0319, 82.9581)
    ref = L[int(ny) - 6:int(ny) + 7, int(nx) - 6:int(nx) + 7].max()
    print('Novosibirsk peak', ref)

    add = np.zeros_like(L)
    rng = np.random.default_rng(2240)

    def blob(lat, lon, pop, growth):
        x, y = px(lat, lon)
        p = pop * growth
        r = 1.2 + 2.6 * (p / 1e6) ** 0.45                        # core radius, px
        peak = min(255.0, ref * (0.35 + 0.65 * min(1, (p / 1.4e6) ** 0.35)))
        n = int(8 + 60 * (p / 1e6) ** 0.6)
        # core plus scattered districts (organic, not a perfect disk)
        pts = [(x, y, peak, r)]
        for _ in range(n):
            a = rng.uniform(0, 2 * np.pi); d = abs(rng.normal(0, r * 1.6))
            pts.append((x + d * np.cos(a), y + d * np.sin(a) * 0.9, peak * rng.uniform(0.25, 0.8), r * rng.uniform(0.25, 0.6)))
        for cx, cy, pk, rr in pts:
            R = int(rr * 3) + 2
            x0, x1 = max(0, int(cx) - R), min(W, int(cx) + R + 1)
            y0, y1 = max(0, int(cy) - R), min(H, int(cy) + R + 1)
            yy, xx = np.mgrid[y0:y1, x0:x1]
            g = pk * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * rr * rr))
            add[y0:y1, x0:x1] = np.maximum(add[y0:y1, x0:x1], g)

    # 2240: Siberia ~3 C warmer and the destination of climate migration; bigger in the south and along rivers
    kept = []
    for name, lat, lon, pop in CITIES:
        x, y = px(lat, lon)
        if water[int(y), int(x)]:
            print('under the 2240 sea, skipped:', name); continue
        growth = 2.6 if lat < 58 else 2.0 if lat < 64 else 1.5
        blob(lat, lon, pop, growth); kept.append((name, lat, lon, pop))

    # towns along corridors, Zipf-like sizes
    for line in CORRIDORS:
        for (a1, o1), (a2, o2) in zip(line, line[1:]):
            seg = max(1, int(np.hypot(a2 - a1, (o2 - o1) * np.cos(np.radians((a1 + a2) / 2))) / 1.1))
            for t in rng.uniform(0, 1, seg):
                bend = np.sin(t * np.pi) * rng.normal(0, 0.25)
                lat = a1 + (a2 - a1) * t + bend + rng.normal(0, 0.3)
                lon = o1 + (o2 - o1) * t + rng.normal(0, 0.5)
                x, y = px(lat, lon)
                if water[int(y) % H, int(x) % W]: continue
                pop = 4000 * (1 / rng.uniform(0.04, 1)) ** 1.1
                blob(lat, lon, min(pop, 120000), 1.0)

    # villages: scattered farm settlements of the warmer south, thicker near the corridors
    pts = [(a, o) for line in CORRIDORS for (a, o) in line]
    for _ in range(900):
        a0, o0 = pts[rng.integers(len(pts))]
        lat = a0 + rng.normal(0, 1.6); lon = o0 + rng.normal(0, 3.0)
        if lat > 62 and rng.random() < 0.7: continue
        x, y = px(lat, lon)
        if water[int(y) % H, int(x) % W]: continue
        blob(lat, lon, 1500 * (1 / rng.uniform(0.1, 1)), 1.0)

    add[water] = 0
    out = np.maximum(L, add)
    dp = os.path.join(DST, TB + 'Earth_lights.jpg')
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'L').save(dp, quality=90, optimize=True)
    print('lights written', os.path.getsize(lp) // 1024, '->', os.path.getsize(dp) // 1024, 'KB')

    # cities.tsv: append the Siberian cities not already listed (today's populations, like the rest of the file)
    cp = os.path.join(DST, 'bin/game/data/earth/cities.tsv')
    raw = open(cp, 'rb').read().decode('utf-8')
    nl = '\r\n' if '\r\n' in raw else '\n'
    have = {l.split('\t')[0] for l in raw.splitlines() if l and not l.startswith('#')}
    new = [c for c in kept if c[0] not in have]
    body = raw.rstrip('\r\n') + nl + nl.join(f'{n}\t{a:.4f}\t{o:.4f}\t{p}\t0' for n, a, o, p in new) + nl
    open(cp, 'wb').write(body.encode('utf-8'))
    print('cities added', len(new))

main()

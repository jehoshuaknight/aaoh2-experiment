"""Build Astra Novum 2240 ethnicity maps and per-province mixes.
usage: python3 -I build_ethnicity.py <src AstraNovum dir> <dst AstraNovum dir>
"""
import sys, os, colorsys
import numpy as np
from PIL import Image, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from groups import EARTH, MARS

SRC, DST = sys.argv[1], sys.argv[2]
TB = 'bin/game/textures/bodies/'
GW, GH = 1024, 512          # compute grid
OW, OH = 2048, 1024         # output map

FAMILY_HUE = {
 'Slavic':215,'Germanic':265,'Celtic':150,'Finnic':190,'Baltic':200,'Romance':12,'Ugric':180,'Hellenic':200,
 'Albanian':0,'Kartvelian':330,'Armenian':345,'Caucasian':300,'Turkic':40,'Iranian':95,'Semitic':55,'Berber':30,
 'Mongolic':75,'Uralic':175,'Tungusic':160,'2240 hybrid':320,'Indo-Aryan':25,'Dravidian':350,'Austroasiatic/Dravidian':120,
 'Sinitic':0,'Tibeto-Burman':280,'Tai':140,'Koreanic':230,'Japonic':335,'Austroasiatic':110,'Austronesian':170,
 'Papuan':85,'Pama-Nyungan':20,'Polynesian':185,'Chadic':45,'Atlantic':60,'Saharan':35,'Volta-Niger':300,
 'Benue-Congo':280,'Kwa':150,'Mande':80,'Gur':105,'Bantu':125,'Nilotic':250,'Cushitic':20,'Afro-American':290,
 'Eskimo-Aleut':195,'Indo-Aryan/Tibeto-Burman':300,'Indigenous American':100,'Martian':15,
}

def group_colors(groups):
    fam = {}
    for g in groups: fam.setdefault(g[2], []).append(g[0])
    cols = {}
    for f, keys in fam.items():
        base = FAMILY_HUE.get(f, (hash(f) % 360))
        n = len(keys)
        for i, k in enumerate(keys):
            h = (base + (i - (n - 1) / 2) * min(24, 130 / max(n, 1))) % 360
            s = 0.55 + 0.35 * ((i * 0.618) % 1)
            v = 0.72 + 0.25 * (((i + 1) * 0.381) % 1)
            cols[k] = colorsys.hsv_to_rgb(h / 360, s, v)
    for k, hx in MARTIAN.items():
        cols[k] = tuple(int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return cols

MARTIAN = {'m_tharsian': '#d8433a', 'm_marineris': '#3fb5c9', 'm_arabian': '#e0a33a', 'm_hellasian': '#8d5bd6',
           'm_elysian': '#62c46a', 'm_boreal': '#4d7fe0', 'm_austral': '#c9c06a'}

def unit(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], -1)

def smooth_noise(h, w, scale, seed):
    rng = np.random.default_rng(seed)
    small = rng.standard_normal((max(2, h // scale), max(2, w // scale))).astype(np.float32)
    im = Image.fromarray(small).resize((w, h), Image.BICUBIC)
    a = np.array(im); return a / (a.std() + 1e-6)

def grid(seed, amp=1.0):
    lat = 90 - (np.arange(GH) + 0.5) / GH * 180
    lon = -180 + (np.arange(GW) + 0.5) / GW * 360
    LON, LAT = np.meshgrid(lon, lat)
    # domain warp: organic, ecology-like edges, no straight lines
    warp = sum(smooth_noise(GH, GW, s, seed + s) * a for s, a in ((64, 2.2 * amp), (16, 0.9 * amp), (6, 0.35)))
    warp2 = sum(smooth_noise(GH, GW, s, seed + 100 + s) * a for s, a in ((64, 2.2 * amp), (16, 0.9 * amp), (6, 0.35)))
    return unit(LAT + warp, LON + warp2 / np.maximum(np.cos(np.radians(LAT)), 0.25))

def scores(groups, P):
    S = np.zeros((len(groups),) + P.shape[:2], np.float32)
    for gi, g in enumerate(groups):
        for lat, lon, w, r in g[4]:
            c = unit(lat, lon)
            d = np.degrees(np.arccos(np.clip(P @ c, -1, 1)))
            S[gi] += w * np.exp(-(d / r) ** 2)
    return S

def load_l(path, size):
    return np.array(Image.open(path).convert('L').resize(size, Image.BILINEAR), np.float32) / 255

def province_ids(path, size):
    a = np.array(Image.open(path).convert('RGB').resize(size, Image.NEAREST)).astype(np.int64)
    return a[..., 0] + a[..., 1] * 256 + a[..., 2] * 65536

def render(body, groups, density, land_big, height_big, colors, sea_rgb):
    keys = [g[0] for g in groups]
    P = grid(7 if body == 'Earth' else 11, 1.0 if body == 'Earth' else 5.0)
    S = scores(groups, P)
    # map colours: sharp-ish soft blend (p=4) so cores read clearly, edges blend
    W4 = S ** 4 + 1e-12; W4 /= W4.sum(0)
    C = np.array([colors[k] for k in keys], np.float32)
    rgb = np.tensordot(W4, C, axes=(0, 0))                       # GH,GW,3
    # empty land (no group near): fade to neutral
    total = S.sum(0)
    empt = np.clip(total / (0.35 if body == 'Earth' else 0.12), 0, 1)[..., None]
    rgb = rgb * empt + np.array([0.42, 0.40, 0.36]) * (1 - empt)
    img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).resize((OW, OH), Image.BICUBIC)
    rgb = np.array(img, np.float32) / 255
    # brightness from population density, plus relief shading, like the ecology map
    dens = np.array(Image.fromarray((density * 255).astype(np.uint8)).resize((OW, OH), Image.BILINEAR), np.float32) / 255
    shade = 0.28 + 0.72 * dens ** 0.7
    if height_big is not None:
        hb = np.array(Image.fromarray((height_big * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.5)), np.float32) / 255
        gy, gx = np.gradient(hb)
        hs = np.clip(1 - (gx - gy) * 18, 0.82, 1.15)
        shade = shade * hs
    fine = smooth_noise(OH, OW, 4, 5) * 0.015
    rgb = np.clip(rgb * shade[..., None] + fine[..., None], 0, 1)
    lat = 90 - (np.arange(OH) + 0.5) / OH * 180
    sea = np.array(sea_rgb, np.float32) * (0.8 + 0.2 * np.cos(np.radians(lat)))[:, None, None]
    sea = np.broadcast_to(sea, rgb.shape)
    # soft coast: blur the land mask slightly so nothing reads as a border line
    lm = np.array(Image.fromarray((land_big * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32)[..., None] / 255
    out = rgb * lm + sea * (1 - lm)
    # shares use true positions (no visual warp), so small islands get their own groups
    S_true = scores(groups, grid(0, 0.0))
    return Image.fromarray((out * 255).astype(np.uint8)), S_true

def province_mix(S, ids, density, keys):
    W2 = S ** 1.5 + 1e-12; W2 /= W2.sum(0)
    wt = density + 0.02
    res = {}
    for pid in np.unique(ids):
        if pid == 0: continue
        m = ids == pid
        if not m.any(): continue
        sh = (W2[:, m] * wt[m]).sum(1); sh /= sh.sum()
        order = np.argsort(-sh)
        mix, acc = [], 0
        for i in order[:6]:
            p = round(float(sh[i]) * 100)
            if p < 2: break
            mix.append((keys[i], p)); acc += p
        if acc < 100 and mix:
            mix.append(('other', 100 - acc))
        elif acc > 100:
            k, p = mix[0]; mix[0] = (k, p - (acc - 100))
        res[int(pid)] = mix
    return res

def read_provinces(path):
    out = {}
    for line in open(path, encoding='utf-8'):
        if line.startswith('#') or not line.strip(): continue
        f = line.rstrip('\r\n').split('\t'); out[int(f[0])] = f[2]
    return out

def write_mix(path, body, mix, names):
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(f'# {body} 2240: ethnic mix of each province, percent of people. Built by tools/build_ethnicity.py.\n')
        fh.write('# id\tname\tmix (group:percent; keys in data/ethnicity/groups.tsv)\n')
        for pid in sorted(mix):
            fh.write(f'{pid}\t{names.get(pid, "?")}\t' + ';'.join(f'{k}:{p}' for k, p in mix[pid]) + '\n')

def main():
    os.makedirs(os.path.join(DST, 'bin/game/data/ethnicity'), exist_ok=True)
    allg = {}
    for g in EARTH + MARS: allg.setdefault(g[0], g)
    colors = group_colors(list(allg.values()))

    # ---- Earth
    water = load_l(os.path.join(SRC, TB + 'Earth_water.png'), (GW, GH))
    land = water < 0.5
    lights = load_l(os.path.join(DST, TB + 'Earth_lights.jpg'), (GW, GH))   # uses the Siberia-updated lights
    lights = np.array(Image.fromarray((lights * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
    dens = np.clip(np.log1p(lights * 40) / np.log1p(40 * 0.35), 0, 1) * land
    landB = load_l(os.path.join(SRC, TB + 'Earth_water.png'), (OW, OH)) < 0.5
    hB = load_l(os.path.join(SRC, TB + 'Earth_height.png'), (OW, OH))
    img, S = render('Earth', EARTH, dens, landB.astype(np.float32), hB, colors, (0.05, 0.09, 0.15))
    img.save(os.path.join(DST, TB + 'Earth_ethnicity.png'), optimize=True)
    ids = province_ids(os.path.join(SRC, TB + 'Earth_provinces.png'), (GW, GH))
    mix = province_mix(S, ids, dens, [g[0] for g in EARTH])
    write_mix(os.path.join(DST, 'bin/game/data/earth/ethnicity.tsv'), 'Earth', mix,
              read_provinces(os.path.join(SRC, 'bin/game/data/earth/provinces.tsv')))

    # ---- Mars (no night-lights map: density from low ground near the sea and the equator)
    mw = load_l(os.path.join(SRC, TB + 'Mars_water.png'), (GW, GH))
    mland = mw < 0.5
    mh = load_l(os.path.join(SRC, TB + 'Mars_height.png'), (GW, GH))
    lat = 90 - (np.arange(GH) + 0.5) / GH * 180
    coast = np.array(Image.fromarray((mland * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(10)), np.float32) / 255
    near_sea = 1 - np.abs(coast - 0.5) * 2
    mdens = np.clip(0.35 + 0.5 * near_sea + 0.3 * np.cos(np.radians(lat))[:, None] - 0.5 * mh, 0, 1) * mland
    mlandB = load_l(os.path.join(SRC, TB + 'Mars_water.png'), (OW, OH)) < 0.5
    mhB = load_l(os.path.join(SRC, TB + 'Mars_height.png'), (OW, OH))
    img, S = render('Mars', MARS, mdens, mlandB.astype(np.float32), mhB, colors, (0.05, 0.10, 0.16))
    img.save(os.path.join(DST, TB + 'Mars_ethnicity.png'), optimize=True)
    ids = province_ids(os.path.join(SRC, TB + 'Mars_provinces.png'), (GW, GH))
    mix = province_mix(S, ids, mdens, [g[0] for g in MARS])
    write_mix(os.path.join(DST, 'bin/game/data/mars/ethnicity.tsv'), 'Mars', mix,
              read_provinces(os.path.join(SRC, 'bin/game/data/mars/provinces.tsv')))

    # ---- group table
    with open(os.path.join(DST, 'bin/game/data/ethnicity/groups.tsv'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('# Ethnic groups of 2240 (Earth and Mars). Built by tools/build_ethnicity.py.\n')
        fh.write('# Real groups are placed at their real homelands, then shifted for the 2240 setting (sea +70 m, 3 C warmer,\n')
        fh.write('# migration north into Siberia, Canada and the ice-free poles). "2240 hybrid" and "Martian" groups are fictional.\n')
        fh.write('# key\tname\tfamily\tcolour\tbodies\thomeland and 2240 notes\n')
        earth_keys = {g[0] for g in EARTH}; mars_note = {g[0]: g[3] for g in MARS}
        for k, g in allg.items():
            c = '#%02x%02x%02x' % tuple(int(x * 255) for x in colors[k])
            bodies = ','.join(b for b, ok in (('Earth', k in earth_keys), ('Mars', k in mars_note)) if ok)
            note = g[3] if k in earth_keys else mars_note[k]
            if k in earth_keys and k in mars_note: note += '. ' + mars_note[k]
            fh.write(f'{k}\t{g[1]}\t{g[2]}\t{c}\t{bodies}\t{note}\n')
    print('earth groups', len(EARTH), 'mars groups', len(MARS), 'total', len(allg))

main()

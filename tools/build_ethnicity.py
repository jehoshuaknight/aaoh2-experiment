"""Build Astra Novum 2240 ethnicity maps and per-province mixes.
usage: python3 -I build_ethnicity.py <src AstraNovum dir> <dst AstraNovum dir>
"""
import sys, os, colorsys
import numpy as np
from PIL import Image, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from groups import EARTH, MARS, FUSION_PARENTS

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
 'Eskimo-Aleut':195,'Chukotko-Kamchatkan':205,'Hmong-Mien':60,'Nilo-Saharan':270,'Ubangian':230,'Bantoid':140,'Khoe/Bantu':40,'Songhai':75,'Basque':355,'Ainu':190,'Afro-Indigenous':300,'Mixed':200,'2240 fusion':300,'Indo-Aryan/Tibeto-Burman':300,'Indigenous American':100,'Martian':15,
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
            s = 0.38 + 0.30 * ((i * 0.618) % 1)
            v = 0.62 + 0.26 * (((i + 1) * 0.381) % 1)
            cols[k] = colorsys.hsv_to_rgb(h / 360, s, v)
    for k, hx in MARTIAN.items():
        cols[k] = tuple(int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return cols

MARTIAN = {'m_tharsian': '#b9564a', 'm_marineris': '#4f9aa6', 'm_arabian': '#c09048', 'm_hellasian': '#7d64b0',
           'm_elysian': '#6aa06a', 'm_boreal': '#5674b0', 'm_austral': '#a9a46c'}

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

def seed_table(groups):
    rows = [(gi, lat, lon, w, r) for gi, g in enumerate(groups) for lat, lon, w, r in g[4]]
    gi = np.array([r[0] for r in rows]); C = unit(np.array([r[1] for r in rows]), np.array([r[2] for r in rows]))
    return gi, C.astype(np.float32), np.array([r[3] for r in rows], np.float32), np.array([r[4] for r in rows], np.float32)

def scores_chunk(P, table, G):
    gi, C, w, r = table
    d = np.degrees(np.arccos(np.clip(P.reshape(-1, 3) @ C.T, -1, 1)))      # n, seeds
    contrib = w * np.exp(-(d / r) ** 2)
    S = np.zeros((G, d.shape[0]), np.float32)
    np.add.at(S, gi, contrib.T)
    return S                                                                  # G, n

def urban_boost(S, groups, dens_flat):
    # Fusion peoples are city peoples: strong where the night lights are bright, faint in the country.
    fu = np.array([g[0] in FUSION_PARENTS for g in groups])
    if fu.any():
        S[fu] *= (0.45 + 2.2 * dens_flat)[None, :]
    return S

CH = 32   # rows per chunk

def render(body, groups, density, land_big, height_big, colors, sea_rgb, ids):
    keys = [g[0] for g in groups]; G = len(keys)
    table = seed_table(groups)
    amp = 1.0 if body == 'Earth' else 5.0
    Pw = grid(7 if body == 'Earth' else 11, amp)       # warped: the picture
    Pt = grid(0, 0.0)                                   # true: the numbers
    # mosaic noise: in mixed zones groups interleave in patches, as on real ethnographic maps
    NF = 8
    mos = np.stack([smooth_noise(GH, GW, 5, 900 + k) * 0.6 + smooth_noise(GH, GW, 14, 950 + k) * 0.5 for k in range(NF)])
    C = np.array([colors[k] for k in keys], np.float32)
    rgb = np.zeros((GH, GW, 3), np.float32); total = np.zeros((GH, GW), np.float32)
    npv = int(ids.max()) + 1
    acc = np.zeros((G, npv), np.float64)
    wt = (density + 0.02).ravel()
    for y0 in range(0, GH, CH):
        y1 = min(GH, y0 + CH); n = (y1 - y0) * GW
        dch = density[y0:y1].ravel()
        S = urban_boost(scores_chunk(Pw[y0:y1], table, G), groups, dch)
        # Cities mix more: the mosaic noise grows with the night lights.
        L = np.log(S + 1e-6) + mos[np.arange(G) % NF][:, y0:y1].reshape(G, n) * ((np.arange(G) % 3 + 1) / 2.5)[:, None] * (1.0 + 0.9 * dch)[None, :]
        L -= L.max(0); W = np.exp(4.0 * L); W /= W.sum(0)
        rgb[y0:y1] = (W.T @ C).reshape(y1 - y0, GW, 3)
        total[y0:y1] = S.sum(0).reshape(y1 - y0, GW)
        St = urban_boost(scores_chunk(Pt[y0:y1], table, G), groups, dch)
        W2 = St ** 1.5 + 1e-12; W2 /= W2.sum(0)
        idc = ids[y0:y1].ravel(); wc = wt[y0 * GW:y1 * GW]
        for g in range(G):
            acc[g] += np.bincount(idc, weights=W2[g] * wc, minlength=npv)
    empt = np.clip(total / (0.35 if body == 'Earth' else 0.12), 0, 1)[..., None]
    rgb = rgb * empt + np.array([0.40, 0.38, 0.34]) * (1 - empt)
    img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).resize((OW, OH), Image.BICUBIC)
    rgb = np.array(img, np.float32) / 255
    dens = np.array(Image.fromarray((density * 255).astype(np.uint8)).resize((OW, OH), Image.BILINEAR), np.float32) / 255
    shade = 0.32 + 0.68 * dens ** 0.6
    if height_big is not None:
        hb = np.array(Image.fromarray((height_big * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.0)), np.float32) / 255
        gy, gx = np.gradient(hb)
        hs = np.clip(1 - (gx - gy) * 22, 0.78, 1.18)
        shade = shade * hs
    fine = smooth_noise(OH, OW, 4, 5) * 0.012
    rgb = np.clip(rgb * shade[..., None] + fine[..., None], 0, 1)
    lat = 90 - (np.arange(OH) + 0.5) / OH * 180
    sea = np.array(sea_rgb, np.float32) * (0.8 + 0.2 * np.cos(np.radians(lat)))[:, None, None]
    sea = np.broadcast_to(sea, rgb.shape)
    lm = np.array(Image.fromarray((land_big * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32)[..., None] / 255
    out = rgb * lm + sea * (1 - lm)
    return Image.fromarray((out * 255).astype(np.uint8)), acc

def province_mix(acc, keys):
    res = {}
    for pid in range(1, acc.shape[1]):
        col = acc[:, pid]
        if col.sum() <= 0: continue
        sh = col / col.sum(); order = np.argsort(-sh)
        mix, tot = [], 0
        for i in order[:6]:
            p = round(float(sh[i]) * 100)
            if p < 2: break
            mix.append((keys[i], p)); tot += p
        if tot < 100 and mix: mix.append(('other', 100 - tot))
        elif tot > 100: k, p = mix[0]; mix[0] = (k, p - (tot - 100))
        res[pid] = mix
    return res

def load_l(path, size):
    return np.array(Image.open(path).convert('L').resize(size, Image.BILINEAR), np.float32) / 255

def province_ids(path, size):
    a = np.array(Image.open(path).convert('RGB').resize(size, Image.NEAREST)).astype(np.int64)
    return a[..., 0] + a[..., 1] * 256 + a[..., 2] * 65536

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

def contrast_colors(groups, colors, land, seed, amp):
    """Recolour so neighbouring groups contrast, keeping each near its language family's hue."""
    global GW, GH
    keep = (GW, GH); GW, GH = 512, 256
    try:
        P = grid(seed, amp); table = seed_table(groups); G = len(groups)
        lm = np.array(Image.fromarray(land.astype(np.uint8) * 255).resize((GW, GH), Image.NEAREST)) > 0
        S = scores_chunk(P, table, G)
        top = S.argmax(0).reshape(GH, GW); top[~lm] = -1
    finally:
        GW, GH = keep
    adj = np.zeros((G, G))
    for a, b in ((top[:, :-1], top[:, 1:]), (top[:-1], top[1:])):
        m = (a != b) & (a >= 0) & (b >= 0)
        np.add.at(adj, (a[m], b[m]), 1); np.add.at(adj, (b[m], a[m]), 1)
    size = np.bincount(top[top >= 0], minlength=G)
    out = dict(colors)
    done = []
    for gi in np.argsort(-size):
        k = groups[gi][0]
        if k in MARTIAN: done.append(gi); continue
        h0, s0, v0 = colorsys.rgb_to_hsv(*colors[k])
        best, bc = -1, None
        for dh in range(-60, 61, 6):
            for sat in (0.32, 0.45, 0.58):
                for val in (0.6, 0.72, 0.85):
                    c = np.array(colorsys.hsv_to_rgb(((h0 * 360 + dh) % 360) / 360, sat, val))
                    nb = [(adj[gi, j], np.array(out[groups[j][0]])) for j in done if adj[gi, j] > 0]
                    md = min([np.linalg.norm(c - cj) for _, cj in nb], default=1.0)
                    score = min(md, 0.45) - abs(dh) / 600
                    if score > best: best, bc = score, tuple(c)
        out[k] = bc; done.append(gi)
    return out

def main():
    os.makedirs(os.path.join(DST, 'bin/game/data/ethnicity'), exist_ok=True)
    allg = {}
    for g in EARTH + MARS: allg.setdefault(g[0], g)
    colors = group_colors(list(allg.values()))
    # A fusion people starts from the blend of its two parents' colours (the contrast pass then keeps it
    # apart from its neighbours while staying near that hue).
    for k, (a, b) in FUSION_PARENTS.items():
        ca, cb = np.array(colors[a]), np.array(colors[b])
        colors[k] = tuple(np.clip((ca + cb) / 2 * 1.08 + 0.03, 0, 1))

    # ---- Earth
    water = load_l(os.path.join(SRC, TB + 'Earth_water.png'), (GW, GH))
    land = water < 0.5
    lights = load_l(os.path.join(DST, TB + 'Earth_lights.jpg'), (GW, GH))   # uses the Siberia-updated lights
    colors.update({k: v for k, v in contrast_colors(EARTH, colors, land, 7, 1.0).items() if k in {g[0] for g in EARTH}})
    lights = np.array(Image.fromarray((lights * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
    dens = np.clip(np.log1p(lights * 40) / np.log1p(40 * 0.35), 0, 1) * land
    landB = load_l(os.path.join(SRC, TB + 'Earth_water.png'), (OW, OH)) < 0.5
    hB = load_l(os.path.join(SRC, TB + 'Earth_height.png'), (OW, OH))
    ids = province_ids(os.path.join(SRC, TB + 'Earth_provinces.png'), (GW, GH))
    img, acc = render('Earth', EARTH, dens, landB.astype(np.float32), hB, colors, (0.05, 0.09, 0.15), ids)
    img.save(os.path.join(DST, TB + 'Earth_ethnicity.png'), optimize=True)
    mix = province_mix(acc, [g[0] for g in EARTH])
    write_mix(os.path.join(DST, 'bin/game/data/earth/ethnicity.tsv'), 'Earth', mix,
              read_provinces(os.path.join(SRC, 'bin/game/data/earth/provinces.tsv')))

    # ---- Mars (no night-lights map: density from low ground near the sea and the equator)
    mw = load_l(os.path.join(SRC, TB + 'Mars_water.png'), (GW, GH))
    mland = mw < 0.5
    mh = load_l(os.path.join(SRC, TB + 'Mars_height.png'), (GW, GH))
    mcol = contrast_colors(MARS, colors, mland, 11, 5.0)
    colors.update({k: v for k, v in mcol.items() if k in {g[0] for g in MARS} and k not in {g[0] for g in EARTH}})
    lat = 90 - (np.arange(GH) + 0.5) / GH * 180
    coast = np.array(Image.fromarray((mland * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(10)), np.float32) / 255
    near_sea = 1 - np.abs(coast - 0.5) * 2
    mdens = np.clip(0.35 + 0.5 * near_sea + 0.3 * np.cos(np.radians(lat))[:, None] - 0.5 * mh, 0, 1) * mland
    mlandB = load_l(os.path.join(SRC, TB + 'Mars_water.png'), (OW, OH)) < 0.5
    mhB = load_l(os.path.join(SRC, TB + 'Mars_height.png'), (OW, OH))
    ids = province_ids(os.path.join(SRC, TB + 'Mars_provinces.png'), (GW, GH))
    img, acc = render('Mars', MARS, mdens, mlandB.astype(np.float32), mhB, colors, (0.05, 0.10, 0.16), ids)
    img.save(os.path.join(DST, TB + 'Mars_ethnicity.png'), optimize=True)
    mix = province_mix(acc, [g[0] for g in MARS])
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

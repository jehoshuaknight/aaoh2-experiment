"""Write shaders/ethnicity_tables.slang: the 2240 ethnic mix of every province as shader constants,
so the planet shader can draw the ethnicity map in game (map style 2, "Peoples of 2240").

Per province, four uints:
  A = lat (10 bits, -90..90) | lon (11 bits, -180..180) << 10 | share1 (7 bits) << 21
  B = group1 (9 bits) | group2 (9 bits) << 9 | share2 (7 bits) << 18
  C = group3 (9 bits) | share3 (7 bits) << 9
  D = group4 (9 bits) | share4 (7 bits) << 9 | group5 << 16 | share5 << 25
Provinces are sorted by region; REGION_START[r]..REGION_START[r+1] are region r's provinces.
The shader knows the region exactly (the province data texture's g channel), and picks the
province inside it by the nearest centre.

usage: python3 -I eth_tables.py <AstraNovum dir> <out .slang>
"""
import sys, os

A, OUT = sys.argv[1], sys.argv[2]
D = os.path.join(A, 'bin/game/data')

def tsv(p):
    for l in open(p, encoding='utf-8'):
        if l.startswith('#') or not l.strip():
            continue
        yield l.rstrip('\n').split('\t')

keys, colour = [], {}
for f in tsv(os.path.join(D, 'ethnicity/groups.tsv')):
    keys.append(f[0]); colour[f[0]] = f[3]
index = {k: i for i, k in enumerate(keys)}
assert len(keys) < 512

def province_weights(low):
    if low != 'earth':
        return {f[0]: float(f[5]) for f in tsv(os.path.join(D, low, 'province_facts.tsv')) if f[0] != 'id'}
    import numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    T = os.path.join(A, 'bin/game/textures/bodies/')
    L = np.asarray(Image.open(T + 'Earth_lights.jpg').convert('L').resize((2048, 1024), Image.BOX), np.float32) / 255
    ids = np.asarray(Image.open(T + 'Earth_provinces.png').convert('RGB').resize((2048, 1024), Image.NEAREST)).astype(np.int64)
    ids = ids[..., 0] + ids[..., 1] * 256 + ids[..., 2] * 65536
    lat = np.radians(90 - (np.arange(1024) + 0.5) / 1024 * 180)[:, None]
    wl = np.clip(L - 0.10, 0, None) ** 1.3 * np.cos(lat)
    wc = np.zeros_like(wl)
    for f in tsv(os.path.join(D, 'earth/cities.tsv')):
        y = min(1023, int((90 - float(f[1])) / 180 * 1024)); x = min(2047, int((float(f[2]) + 180) / 360 * 2048))
        wc[y, x] += float(f[3])
    w = 0.6 * wc / wc.sum() + 0.4 * wl / wl.sum()
    sums = np.bincount(ids.ravel(), weights=w.ravel(), minlength=ids.max() + 1)
    return {str(i): float(sums[i]) + 1e-9 for i in range(1, len(sums))}

def body(low):
    region = {f[0]: int(f[1]) for f in tsv(os.path.join(D, low, 'provinces.tsv'))}
    centre = {}
    for f in tsv(os.path.join(D, low, 'province_facts.tsv')):
        if f[0] == 'id':
            continue
        centre[f[0]] = (float(f[3]), float(f[4]))
    mix = {f[0]: [(kv.split(':')[0], int(kv.split(':')[1])) for kv in f[2].split(';') if kv] for f in tsv(os.path.join(D, low, 'ethnicity.tsv'))}
    nreg = max(region.values()) + 1
    rows = []
    for pid, r in region.items():
        if pid not in centre or pid not in mix:
            continue
        m = [(k, v) for k, v in mix[pid] if k in index][:5]
        tot = sum(v for _, v in m) or 1
        m = [(k, round(v * 100 / tot)) for k, v in m] + [(m[0][0] if m else keys[0], 0)] * (5 - len(m))
        lat, lon = centre[pid]
        rows.append((r, pid, lat, lon, m))
    rows.sort(key=lambda t: (t[0], int(t[1])))
    start, data = [0] * (nreg + 1), []
    for r in range(nreg + 1):
        start[r] = next((i for i, t in enumerate(rows) if t[0] >= r), len(rows))
    ids = []
    for r, pid, lat, lon, m in rows:
        ids.append(int(pid))
        la = max(0, min(1023, round((lat + 90) / 180 * 1023)))
        lo = max(0, min(2047, round((lon + 180) / 360 * 2047)))
        (g1, s1), (g2, s2), (g3, s3), (g4, s4), (g5, s5) = m
        data += [la | lo << 10 | min(127, s1) << 21,   # (centre word is rebuilt below with the id)
                 index[g1] | index[g2] << 9 | min(127, s2) << 18,
                 index[g3] | min(127, s3) << 9,
                 index[g4] | min(127, s4) << 9 | index[g5] << 16 | min(127, s5) << 25]
    # Region mixes, weighted by where people live (the game's city list for 60 %, city light for 40 % on
    # Earth; land area on Mars): the fallback fill when the shader cannot tell the exact province.
    weight = province_weights(low)
    rmix = []
    for r in range(nreg):
        acc = {}
        for pid, rr in region.items():
            if rr != r or pid not in mix:
                continue
            w = weight.get(pid, 0.0)
            for k, v in mix[pid]:
                if k in index:
                    acc[k] = acc.get(k, 0.0) + w * v
        top = sorted(acc.items(), key=lambda kv: -kv[1])[:2]
        tot = sum(v for _, v in top) or 1
        (k1, v1), (k2, v2) = (top + [(keys[0], 0.0)] * 2)[:2]
        s1, s2 = round(v1 * 100 / tot), round(v2 * 100 / tot)
        rmix.append(f'uint2({index[k1] | index[k2] << 9 | min(127, s2) << 18}u, {min(127, s1)}u)')
    return nreg, start, data, len(rows), ids, rmix

def sw(fn, vals, default='0u', ret='uint'):
    # A switch, not an array: constant arrays indexed at run time become per-pixel copies in SPIR-V.
    body = '\n'.join(f'    case {i}u: return {v};' for i, v in enumerate(vals))
    return f'{ret} {fn}(uint i)\n{{\n    switch (i)\n    {{\n{body}\n    default: return {default};\n    }}\n}}\n\n'

en, es, ed, ec, eids, ermix = body('earth')
mn, ms, md, mc, mids, mrmix = body('mars')
pids = eids + mids
# One table for both planets: Mars's regions follow Earth's, Mars's provinces follow Earth's.
starts = es[:-1] + [ec + x for x in ms]
words = ed + md
# centre: lat 10 bits | lon 11 bits << 10 | (province id & 255) << 21 (to match the engine's province value)
centre = [f'{(words[i] & 0x1FFFFF) | (pids[i // 4] & 255) << 21}u' for i in range(0, len(words), 4)]
mix = []
for i in range(0, len(words), 4):
    a, b, c, d = words[i:i + 4]
    s1 = (a >> 21) & 127
    mix.append(f'uint3({b}u, {c | s1 << 16}u, {d}u)')
ranges = [f'uint2({starts[r]}u, {starts[r + 1]}u)' for r in range(len(starts) - 1)]
cols = [f'{int(colour[k][1:], 16)}u' for k in keys]
with open(OUT, 'w', newline='\n') as fh:
    fh.write('// Generated by tools/eth_tables.py from data/ethnicity and data/<body>/ethnicity.tsv. Do not edit.\n')
    fh.write(f'// {len(keys)} groups; Earth {ec} provinces in {en} regions; Mars {mc} provinces in {mn} regions (after Earth\'s).\n')
    fh.write('// provinceCentre: lat 10 bits | lon 11 bits << 10 | (id & 255) << 21.  provinceMix: x = g1 | g2 << 9 | s2 << 18, y = g3 | s3 << 9 | s1 << 16, z = g4 | s4 << 9 | g5 << 16 | s5 << 25.\n\n')
    fh.write(f'static const uint ETH_GROUPS = {len(keys)}u;\nstatic const uint EARTH_REGIONS = {en}u;\nstatic const uint MARS_REGIONS = {mn}u;\n\n')
    fh.write(sw('ethColourHex', cols, '7829367u'))
    fh.write(sw('regionRange', ranges, 'uint2(0u, 0u)', 'uint2'))
    fh.write(sw('provinceCentre', centre))
    fh.write(sw('provinceMix', mix, 'uint3(0u, 0u, 0u)', 'uint3'))
    # regionMix(r): x = g1 | g2 << 9 | s2 << 18, y = s1 (Earth regions, then Mars regions)
    fh.write(sw('regionMix', ermix + mrmix, 'uint2(0u, 100u)', 'uint2'))
print(f'groups {len(keys)}, Earth {ec} provinces / {en} regions, Mars {mc} / {mn}')

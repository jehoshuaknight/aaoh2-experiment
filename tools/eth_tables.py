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

# ---- language families for the language layer of the Peoples map
fam = {f[0]: f[2] for f in tsv(os.path.join(D, 'ethnicity/groups.tsv'))}
SPEAKS = {  # peoples whose language belongs to another family than their ancestry
    'african_am': 'Germanic', 'jamaican': 'Germanic', 'afro_carib': 'Germanic', 'ndyuka': 'Germanic', 'guyanese': 'Germanic',
    'haitian': 'Romance', 'afro_brazilian': 'Romance', 'afro_colombian': 'Romance', 'esmeraldeno': 'Romance', 'cuban': 'Romance',
    'hisp_carib': 'Romance', 'metis': 'Romance', 'garifuna': 'Indigenous American',
    'sibiryak': 'Slavic', 'ob_exiles': 'Slavic', 'reacher': 'Germanic', 'greenlander': 'Germanic', 'lowlander': 'Germanic',
    'austral': 'Romance', 'delta_diaspora': 'Indo-Aryan', 'indo_trini': 'Germanic',
}
sys.path.insert(0, os.environ.get('ASTRA_TOOLS', os.path.join(os.path.dirname(os.path.abspath(__file__)))))
try:
    from groups import FUSION_PARENTS
except Exception:
    FUSION_PARENTS = {}
def lang_of(k):
    if k in SPEAKS: return SPEAKS[k]
    if k in FUSION_PARENTS: return lang_of(FUSION_PARENTS[k][0])
    f = fam.get(k, 'Other')
    if k.startswith('m_'): return 'Martian creoles'
    return f.split('/')[0]
LANG_HEX = {  # hand-picked, muted, distinct for neighbours that meet on the map
    'Germanic': 0x7c8fc9, 'Romance': 0xd98b6c, 'Slavic': 0x6fb5a8, 'Celtic': 0x59a36b, 'Finnic': 0x9fd0c8, 'Uralic': 0x8fbfa8,
    'Baltic': 0xb7c97a, 'Ugric': 0xa7d6b0, 'Hellenic': 0x5f8fd6, 'Albanian': 0xc76b7a, 'Armenian': 0xb0617f, 'Kartvelian': 0xd1a35a,
    'Caucasian': 0x9b7cb8, 'Turkic': 0xd4b25e, 'Iranian': 0x8bb35e, 'Semitic': 0xe0c98a, 'Berber': 0xc79a63, 'Mongolic': 0xc2c46b,
    'Tungusic': 0x7fb0c8, 'Chukotko-Kamchatkan': 0x95a8b8, 'Indo-Aryan': 0xe0a070, 'Dravidian': 0xc9727a, 'Austroasiatic': 0x7dbf8e,
    'Sinitic': 0xd16a6a, 'Tibeto-Burman': 0xa98fd0, 'Tai': 0x6fc49a, 'Hmong-Mien': 0xb5d17a, 'Koreanic': 0x6a8fe0, 'Japonic': 0xe08fb0,
    'Austronesian': 0x5fbfc0, 'Papuan': 0x8f9f5a, 'Pama-Nyungan': 0xc48a5a, 'Polynesian': 0x4fa8d0, 'Chadic': 0xd8c070,
    'Atlantic': 0xb4d080, 'Saharan': 0xe0b080, 'Volta-Niger': 0xc070a0, 'Benue-Congo': 0xa070c0, 'Kwa': 0x70c0a0, 'Mande': 0x90b050,
    'Gur': 0xd0a050, 'Bantu': 0x6aa86a, 'Bantoid': 0x88c078, 'Nilotic': 0x7f8fd0, 'Nilo-Saharan': 0x9a7fc0, 'Cushitic': 0xd0907a,
    'Ubangian': 0xb0a0e0, 'Songhai': 0xc0b070, 'Dogon': 0xa08060, 'Ijoid': 0x60b0b0, 'Khoe': 0xc8a878, 'Eskimo-Aleut': 0xa0c8e0,
    'Indigenous American': 0xb6845a, 'Afro-Indigenous': 0x9a6a8a, 'Mixed': 0x9a9a9a, 'Basque': 0xe05a5a, 'Ainu': 0x90b0d0,
    'Isolate': 0xb0b0b0, 'Central Sudanic': 0xa890b8, 'Mande': 0x90b050, 'Martian creoles': 0xc0604a, '2240 hybrid': 0xb070c0,
}
langs = sorted({lang_of(k) for k in keys})
lang_index_of = {l: i for i, l in enumerate(langs)}
lang_index = {k: lang_index_of[lang_of(k)] for k in keys}
import colorsys, hashlib
def auto(l):
    h = int(hashlib.md5(l.encode()).hexdigest(), 16) % 360 / 360
    r, g, b = colorsys.hsv_to_rgb(h, 0.45, 0.78); return int(r * 255) << 16 | int(g * 255) << 8 | int(b * 255)
lang_cols = [LANG_HEX.get(l, auto(l)) for l in langs]

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
    # Language families (0.1.19): which family each people speaks, and the family's map colour.
    fh.write(sw('groupLang', [f'{lang_index[k]}u' for k in keys], '0u'))
    fh.write(sw('langColourHex', [f'{c}u' for c in lang_cols], '7829367u'))
    # regionMix(r): x = g1 | g2 << 9 | s2 << 18, y = s1 (Earth regions, then Mars regions)
    fh.write(sw('regionMix', ermix + mrmix, 'uint2(0u, 100u)', 'uint2'))
print(f'groups {len(keys)}, Earth {ec} provinces / {en} regions, Mars {mc} / {mn}')

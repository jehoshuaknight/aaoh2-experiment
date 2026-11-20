"""data/ethnicity/peoples_info.tsv: everything known about every people of 2240.
Population: each province's people (Earth 8.6 billion, Mars 410 million, from the campaign) spread by
area x night lights (Earth) or by area (Mars), then split by the province's ethnic mix.
usage: python3 -I build_peoples_info.py <AstraNovum dir>
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peoples_info import INFO
from groups_fusion import FUSION

A = sys.argv[1]; D = os.path.join(A, 'bin/game/data')
from groups import FUSION_PARENTS as PARENTS
TOTAL = {'earth': 8.6e9, 'mars': 410e6}

def tsv(p):
    for l in open(p, encoding='utf-8'):
        if l.startswith('#') or not l.strip():
            continue
        yield l.rstrip('\n').split('\t')

groups = {f[0]: f for f in tsv(os.path.join(D, 'ethnicity/groups.tsv'))}
pop = {k: 0.0 for k in groups}; where = {k: [] for k in groups}; nprov = {k: 0 for k in groups}
# 0.1.23: who lives beside whom (people shared in the same provinces), and where each people is the majority
share = {k: {} for k in groups}; major = {k: 0 for k in groups}
for low in ('earth', 'mars'):
    names = {f[0]: f[2] for f in tsv(os.path.join(D, low, 'provinces.tsv'))}
    weight = {}
    if low == 'earth':
        # People live where the lights are: city light above the faint background glow the lights map
        # has over ice and desert, summed per province (cos-latitude for pixel area).
        import numpy as np
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        T = os.path.join(A, 'bin/game/textures/bodies/')
        L = np.asarray(Image.open(T + 'Earth_lights.jpg').convert('L').resize((2048, 1024), Image.BOX), np.float32) / 255
        ids = np.asarray(Image.open(T + 'Earth_provinces.png').convert('RGB').resize((2048, 1024), Image.NEAREST)).astype(np.int64)
        ids = ids[..., 0] + ids[..., 1] * 256 + ids[..., 2] * 65536
        lat = np.radians(90 - (np.arange(1024) + 0.5) / 1024 * 180)[:, None]
        # People by the game's own city list (real populations, every big city on the 2240 coast) for 60 %,
        # and by city light above the background glow for 40 % (towns and villages the list misses).
        cl = np.cos(lat)
        wl = np.clip(L - 0.10, 0, None) ** 1.3 * cl
        wc = np.zeros_like(wl)
        for f in tsv(os.path.join(D, 'earth/cities.tsv')):
            y = min(1023, int((90 - float(f[1])) / 180 * 1024)); x = min(2047, int((float(f[2]) + 180) / 360 * 2048))
            wc[y, x] += float(f[3])
        w = 0.6 * wc / wc.sum() + 0.4 * wl / wl.sum()
        sums = np.bincount(ids.ravel(), weights=w.ravel(), minlength=ids.max() + 1)
        weight = {str(i): float(sums[i]) for i in range(1, len(sums))}
    else:
        for f in tsv(os.path.join(D, low, 'province_facts.tsv')):
            if f[0] != 'id':
                weight[f[0]] = float(f[5])
    tot = sum(weight.values())
    for f in tsv(os.path.join(D, low, 'ethnicity.tsv')):
        p = TOTAL[low] * weight.get(f[0], 0) / tot
        mix = [(kv.split(':')[0], int(kv.split(':')[1])) for kv in f[2].split(';') if kv.split(':')[0] in groups]
        if mix and max(mix, key=lambda m: m[1])[1] >= 50:
            major[max(mix, key=lambda m: m[1])[0]] += 1
        for a, va in mix:
            for b, vb in mix:
                if a != b:
                    share[a][b] = share[a].get(b, 0.0) + p * min(va, vb) / 100
        for kv in f[2].split(';'):
            k, v = kv.split(':')
            if k in pop:
                n = p * int(v) / 100
                pop[k] += n; nprov[k] += 1; where[k].append((n, names.get(f[0], f[0])))

def fmt(n):
    return f'{n / 1e9:.2f} billion' if n >= 1e9 else (f'{n / 1e6:.1f} million' if n >= 1e6 else f'{n / 1e3:.0f} thousand')

def lang_faith(k):
    if k in INFO:
        return INFO[k]
    a, b = PARENTS[k]
    la, fa = INFO[a], INFO[b]
    l1, l2 = la[0].split(',')[0].strip(), INFO[b][0].split(',')[0].strip()
    lang = f'{l1} and {l2} (a bilingual 2240 creole)' if l1 != l2 else f'{l1} (a 2240 city dialect)'
    f1, f2 = la[1].split(',')[0].strip(), INFO[b][1].split(',')[0].strip()
    faith = (f'{f1} and {f2} families; many secular' if f1 != f2 else f'{f1}; many secular')
    return lang, faith

from peoples_story import describe
import groups as _G
# Each people's centre: its strongest seed (where its homeland lies).
CENTRE = {g[0]: max(g[4], key=lambda s: s[2])[:2] for g in _G.EARTH + _G.MARS}
out = os.path.join(D, 'ethnicity/peoples_info.tsv')
with open(out, 'w', encoding='utf-8', newline='\n') as fh:
    fh.write('# Every people of 2240: language, faith, population and where they live. Built by tools/build_peoples_info.py.\n')
    fh.write('# Populations are estimates: each province\'s share of its planet (Earth 8.6 bn, Mars 410 m) by area x night lights, split by its ethnic mix.\n')
    fh.write('# key\tname\tfamily\tcolour\tparents\tlanguage\tfaith\tpopulation\tprovinces\tstrongholds\thistory\tdescription\n')
    rows = []
    for k, g in groups.items():
        lang, faith = lang_faith(k)
        par = ' + '.join(groups[p][1] for p in PARENTS[k]) if k in PARENTS else ''
        strong = ', '.join(n for _, n in sorted(where[k], reverse=True)[:3])
        rows.append((pop[k], k, g[1], g[2], g[3], par, lang, faith, strong, g[5]))
    for p, k, name, fam, col, par, lang, faith, strong, hist in sorted(rows, reverse=True):
        la, lo = CENTRE.get(k, (0.0, 0.0))
        # Enclaves too small to show in any province mix still hold a town or two.
        p = max(p, 150000.0 if k in PARENTS else 60000.0)
        nb = [groups[b][1] for b, _ in sorted(share[k].items(), key=lambda kv: -kv[1])[:3] if b not in PARENTS.get(k, ())]
        ctx = {'neighbours': nb, 'majority': major[k], 'provinces': nprov[k],
               'parent_keys': list(PARENTS.get(k, ()))}
        desc = describe(k, name, fam, hist, lang, faith, p, strong, par, la, lo, 'Mars' if k.startswith('m_') else 'Earth', ctx)
        desc = desc.replace('\n', '\\n')   # paragraphs, escaped for the TSV
        fh.write(f'{k}\t{name}\t{fam}\t{col}\t{par}\t{lang}\t{faith}\t{int(round(p, -3))}\t{nprov[k]}\t{strong}\t{hist}\t{desc}\n')
print('written', out, len(rows), 'peoples; largest:', ', '.join(f'{r[2]} {fmt(r[0])}' for r in sorted(rows, reverse=True)[:6]))

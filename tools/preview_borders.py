"""CPU preview of the 0.1.4 border shader (Realistic and Strategic styles), old vs new, flat map.
Approximates mesh.slang: same formulas, daylight only, no relief, 1 data texel = 1 pixel at zoom 1.
usage: python3 -I preview_borders.py <AstraNovum dir> <out dir> <body> <x0 y0 x1 y1 (fractions)> <zoom 0..1> <name>
"""
import sys, os
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
A, OUT, BODY = sys.argv[1], sys.argv[2], sys.argv[3]
fx0, fy0, fx1, fy1 = map(float, sys.argv[4:8]); ZOOM = float(sys.argv[8]); NAME = sys.argv[9]
TB = os.path.join(A, 'bin/game/textures/bodies/')
W, H = 4096, 2048

def lum(c): return c[..., 0] * 0.299 + c[..., 1] * 0.587 + c[..., 2] * 0.114

ids = np.array(Image.open(TB + f'{BODY}_provinces.png').convert('RGB')).astype(np.int64)
ids = ids[..., 0] + ids[..., 1] * 256 + ids[..., 2] * 65536
Hs, Ws = ids.shape
reg = {}
for l in open(os.path.join(A, f'bin/game/data/{BODY.lower()}/provinces.tsv'), encoding='utf-8'):
    if l.startswith('#') or not l.strip(): continue
    f = l.split('\t'); reg[int(f[0])] = int(f[1])
lut = np.zeros(ids.max() + 1, np.int64)
for k, v in reg.items(): lut[k] = v
water = np.array(Image.open(TB + f'{BODY}_water.png').convert('L').resize((Ws, Hs), Image.NEAREST)) > 127
land = (~water) & (ids > 0)
G = np.where(land, 128 + lut[ids], 0)            # g channel x 255
R = ids
base_name = 'Earth.jpg' if BODY == 'Earth' else 'Mars_terraformed.jpg'
albedo = np.array(Image.open(TB + base_name).convert('RGB').resize((Ws, Hs), Image.BILINEAR), np.float32) / 255

# crop with a margin for the taps
x0, x1, y0, y1 = int(fx0 * Ws), int(fx1 * Ws), int(fy0 * Hs), int(fy1 * Hs)
m = 12
sl = (slice(max(0, y0 - m), min(Hs, y1 + m)), slice(max(0, x0 - m), min(Ws, x1 + m)))
G, R, land, albedo = G[sl], R[sl], land[sl], albedo[sl]
h, w = G.shape

def shifted(a, dy, dx):
    return np.roll(np.roll(a, dy, 0), dx, 1)

def line(mask_diff, width):
    # distance in pixels to a texel where the value changes, as an anti-aliased line of `width`
    d = np.full(mask_diff.shape, 9.0, np.float32)
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            dd = np.hypot(dy, dx)
            if dd == 0 or dd > 3: continue
            d = np.where(shifted(mask_diff, dy, dx), np.minimum(d, dd), d)
    d = np.where(mask_diff, 0.5, d)
    return np.clip(1 - (d - width / 2) / 1.0, 0, 1)

def edge_of(a):
    e = np.zeros(a.shape, bool)
    for dy, dx in ((0, 1), (1, 0)):
        e |= (a != shifted(a, dy, dx))
    return e

prov_edge = edge_of(R) & land & shifted(land, 0, 1) & shifted(land, 1, 0)
reg_edge = edge_of(G) & land & shifted(land, 0, 1) & shifted(land, 1, 0)
coast_edge = edge_of(land.astype(np.int8))
provE = line(prov_edge, 0.8)
regE = line(reg_edge, 2.6)
coastE = line(coast_edge, 1.2)

def region_tint(g):
    idn = g.astype(np.float32) - 128.0
    hh = np.mod(idn * 0.61803398875 + 0.07, 1.0)
    c = np.clip(np.abs(np.mod(hh[..., None] + np.array([0, 2 / 3, 1 / 3]), 1.0) * 6 - 3) - 1, 0, 1)
    return 0.55 + (c - 0.55) * 0.62

def vivid(g):
    c = (region_tint(g) - 0.55) / 0.62 + 0.55; return 0.5 + (c - 0.5) * 0.92

def region_field(radius):
    differ = np.zeros(G.shape, np.float32); pdiffer = np.zeros(G.shape, np.float32)
    total = 0.0; ptotal = 0.0
    for k in range(16):
        a = k * 2.39996323; r = radius * np.sqrt((k + 0.5) / 16)
        dy, dx = int(np.floor(np.sin(a) * r + 0.5)), int(np.floor(np.cos(a) * r + 0.5))
        tg = shifted(G, -dy, -dx); tr = shifted(R, -dy, -dx)
        wt = 1 - r / (radius + 1); total += wt
        differ += ((tg > 0) & (tg != G)) * wt
        pw = wt if r < radius * 0.45 else 0.0; ptotal += pw
        pdiffer += ((tg > 0) & (tr != R)) * pw
    glow = np.where(G > 0, differ / total, 0)
    pglow = np.where(G > 0, np.clip(pdiffer / max(ptotal, 1e-4) * 2.0, 0, 1), 0)
    return glow, pglow

owner = np.array([0.20, 0.36, 0.78], np.float32)   # the Terran Union's colour (preview stand-in)
shade = (np.mod(R * 0.37, 1.0) * 0.75 + 0.25).astype(np.float32)
lw = np.array([0.299, 0.587, 0.114], np.float32)

def paint(new):
    col = albedo.copy()
    lc = owner
    ink = (lc @ lw) + (lc - (lc @ lw)) * 0.65
    ink = ink + (ink / max(ink.max(), 0.2) * 0.60 - ink) * 0.7
    ink = ink[None, None, :] * (0.85 + 0.30 * ((shade - 0.25) / 0.75))[..., None]
    if new:
        ink = ink + (ink * region_tint(G) * 1.35 - ink) * 0.22
    ground = lum(col)[..., None]
    relief = np.clip(ground / 0.30, 0.75, 1.35)
    pt = ink / np.maximum(lum(ink)[..., None], 0.05) * ground * relief / 1.05
    out = col + (col * 0.95 + (pt - col * 0.95) * 0.58 - col) * 0.42
    return np.where(land[..., None], out, col)

def realistic(new):
    lit = paint(new) ** 2.2 * 0.9                        # to linear, a flat sun
    ctryE = np.maximum(coastE * 0, regE)
    camK = 0.35 + (0.9 - 0.35) * (1 - ZOOM)
    lit = lit + (lit * 0.45 - lit) * (provE * (1 - ctryE) * camK)[..., None]
    if new:
        glow, pglow = region_field(3.0 + 7.0 * ZOOM)
        rt = vivid(G)
        band = np.clip(glow * 3.2, 0, 1) * (1 - regE); t = np.clip((glow - 0.24) / 0.22, 0, 1); rim = t * t * (3 - 2 * t) * (1 - regE)
        bright = np.maximum(lum(lit), 0.0005)[..., None]
        pt = rt / np.maximum(lum(rt), 0.05)[..., None] * np.minimum(bright, 0.35)
        lit = lit + (pt * 1.3 - lit) * (band * (0.40 + 0.25 * ZOOM))[..., None]
        lit = lit + (pt * 1.7 - lit) * (rim * (0.30 + 0.25 * ZOOM))[..., None]
        lit = lit + (pt * 1.15 - lit) * (pglow * 0.12 * (1 - ZOOM) * (1 - ctryE))[..., None]
        lit = np.where(land[..., None], lit, lit)
    bk = 0.88 if new else 0.82
    lit = lit + (np.array([0.0002, 0.0002, 0.0003]) - lit) * (regE * bk)[..., None]
    lit = lit + (np.array([0.0002, 0.0002, 0.0003]) - lit) * (coastE * 0.3)[..., None]
    out = np.clip(lit / 0.9, 0, 1) ** (1 / 2.2)
    return out

def strategic(new):
    lumS = lum(albedo ** 1.55 * 0.76)
    rel = np.clip(0.70 + lumS * 1.1, 0.75, 1.18)
    ink = (np.array([0.7, 0.7, 0.7]) + (owner / owner.max() - 0.7) * 0.45) * 0.20
    S = np.where(land[..., None], ink * rel[..., None], np.array([0.006, 0.009, 0.016]))
    hu = (owner - owner.min()) / max(owner.max() - owner.min(), 0.1)
    hsh = (shade - 0.25) / 0.75
    Sl = S + (S * (0.62 + 0.76 * hsh)[..., None] + 0.035 * hsh[..., None] - S) * 0.40
    Ls = lum(Sl)[..., None]
    Sl = Sl + (hu * np.maximum(Ls, 0.03) * 1.5 - Sl) * 0.30
    o = np.where(land[..., None], Sl, S)
    lineP = np.array([0.22, 0.62, 0.66]); lineC = np.array([0.40, 0.95, 0.98]); coastC = np.array([0.30, 0.80, 0.86])
    zP = 0.10 + 0.65 * (1 - ZOOM)
    ctryE = regE
    o = o + (lineP - o) * (provE * (1 - ctryE) * zP * 0.6)[..., None]
    if new:
        glow, pglow = region_field(3.0 + 7.0 * ZOOM)
        rt = lineC + (region_tint(G) * lineC.max() - lineC) * 0.55
        g = np.clip(glow * 3.0, 0, 1) ** 1.3 * (1 - ctryE)
        o = o + rt * (g * 0.55 * (0.6 + 0.4 * ZOOM))[..., None]
        o = o + lineP * (pglow * 0.10 * zP * 0.6 * (1 - ctryE))[..., None]
    o = o + (lineC - o) * (ctryE * 0.9)[..., None]
    o = o + (coastC - o) * (coastE * 0.7)[..., None]
    a = o * 1.02
    disp = np.clip((a * (2.51 * a + 0.03)) / (a * (2.43 * a + 0.59) + 0.14), 0, 1)
    return disp

crop = (slice(y0 - sl[0].start, y1 - sl[0].start), slice(x0 - sl[1].start, x1 - sl[1].start))
rows = []
for f in (realistic, strategic):
    a = (f(False)[crop] * 255).astype(np.uint8); b = (f(True)[crop] * 255).astype(np.uint8)
    sep = np.full((a.shape[0], 6, 3), 20, np.uint8)
    rows.append(np.concatenate([a, sep, b], 1))
img = np.concatenate([rows[0], np.full((6, rows[0].shape[1], 3), 20, np.uint8), rows[1]], 0)
Image.fromarray(img).save(os.path.join(OUT, NAME))
print('saved', NAME, img.shape)

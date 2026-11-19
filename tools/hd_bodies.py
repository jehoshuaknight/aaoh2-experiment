"""HD surface maps for the solar system (0.1.6).
Real mission mosaics (USGS Astrogeology / NASA, public domain) and Solar System Scope maps (CC BY 4.0),
resampled to equirectangular 2:1, longitude -180..180 left to right, north up (the game's layout).
Greyscale mosaics take their colour from the game's existing map (its large-scale tint), so each body
keeps the palette the game already gives it. A mild cinematic grade (contrast, saturation) on top.
usage: python3 -I hd_bodies.py <game textures/bodies dir> <download dir> <original game bodies dir> [names...]
Areas a probe never imaged (no data) are filled from the game's original map, feathered; maps whose
original is a real mosaic are aligned in longitude to it by cross-correlation.
"""
import sys, os, subprocess
import numpy as np
from PIL import Image, ImageFilter
Image.MAX_IMAGE_PIXELS = None

BODIES, DL, ORIG = sys.argv[1], sys.argv[2], sys.argv[3]
ONLY = set(sys.argv[4:])
ALIGN = {'Io', 'Europa', 'Ganymede', 'Callisto', 'Enceladus', 'Phobos'}
# Known layouts (USGS 0..360 products), set by landmarks: Pluto's Sputnik Planitia at 175E, Ceres's Occator at 239E.
ROLL = {'Pluto': 180, 'Charon': 180, 'Ceres': 180}
# New Horizons colour (enhanced-colour releases, toned down): Pluto dark red-brown to cream; Charon grey, red north cap.
PALETTE = {
 'pluto': [(0.0, (0.09, 0.05, 0.035)), (0.22, (0.30, 0.15, 0.08)), (0.45, (0.62, 0.43, 0.29)), (0.7, (0.86, 0.75, 0.60)), (1.0, (0.98, 0.95, 0.90))],
 'charon': [(0.0, (0.10, 0.095, 0.09)), (0.5, (0.50, 0.48, 0.46)), (1.0, (0.86, 0.85, 0.83))],
}
S3 = 'https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/'
SSS = 'https://www.solarsystemscope.com/textures/download/'

# name: (url, size W, colour source: 'own' (colour map) or 'game' (grey, colour from the game map), lon0)
# lon0: the longitude at the source's left edge (USGS global mosaics run -180..180 or 0..360).
SPEC = {
 'Mercury':  (SSS + '8k_mercury.jpg', 4096, 'own', -180),
 'Luna':     (SSS + '8k_moon.jpg', 4096, 'own', -180),
 'Venus':    (SSS + '8k_venus_surface.jpg', 4096, 'own', -180),
 'Venus_clouds': (SSS + '4k_venus_atmosphere.jpg', 4096, 'own', -180),
 'Jupiter':  (SSS + '8k_jupiter.jpg', 4096, 'own', -180),
 'Saturn':   (SSS + '8k_saturn.jpg', 4096, 'own', -180),
 'Io':       (S3 + 'Io_GalileoSSI-Voyager_Global_Mosaic_ClrMerge_1km.tif', 4096, 'own', -180),
 'Europa':   (S3 + 'Europa_Voyager_GalileoSSI_global_mosaic_500m.tif', 4096, 'game', -180),
 'Ganymede': (S3 + 'Ganymede_Voyager_GalileoSSI_Global_ClrMosaic_1435m.tif', 4096, 'own', -180),
 'Callisto': (S3 + 'Callisto_Voyager_GalileoSSI_global_mosaic_1km.tif', 4096, 'game', -180),
 'Enceladus': (S3 + 'Enceladus_Cassini_mosaic_global_110m.tif', 2048, 'game', -180),
 'Titan':    (S3 + 'Titan_ISS_P19658_Mosaic_Global_4km.tif', 2048, 'game', -180),
 'Triton':   (S3 + 'Triton_Voyager2_ClrMosaic_GlobalFill_600m.tif', 2048, 'own', -180),   # colour kept, desaturated; fill tinted
 'Pluto':    (S3 + 'Pluto_NewHorizons_Global_Mosaic_300m_Jul2017_8bit.tif', 2048, 'pluto', 0),    # 0..360 source
 'Charon':   (S3 + 'Charon_NewHorizons_Global_Mosaic_300m_Jul2017_8bit.tif', 2048, 'charon', 0),  # 0..360 source
 'Ceres':    (S3 + 'Ceres_Dawn_FC_DLR_global_20ppd_Oct2015.tif', 2048, 'game', -180),
 'Phobos':   (S3 + 'Phobos_ME_SRC_Mosaic_Global_16ppd.tif', 2048, 'game', -180),
}

def fetch(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return
    subprocess.run(['curl', '-sS', '-L', '-A', 'Mozilla/5.0', '--max-time', '900', '--retry', '3', '-o', path, url], check=True)

def to_float(im):
    a = np.asarray(im)
    if a.dtype == np.uint16:
        lo, hi = np.percentile(a[a > 0], (0.2, 99.8)) if (a > 0).any() else (0, 65535)
        return np.clip((a.astype(np.float32) - lo) / max(hi - lo, 1), 0, 1)
    if a.dtype in (np.float32, np.float64):
        v = a[np.isfinite(a)]
        lo, hi = np.percentile(v, (0.2, 99.8))
        return np.clip((np.nan_to_num(a, nan=lo) - lo) / max(hi - lo, 1e-6), 0, 1).astype(np.float32)
    return a.astype(np.float32) / 255.0

def load_source(path, W):
    im = Image.open(path)
    im.draft('RGB', (W, W // 2)) if im.format == 'JPEG' else None
    H = W // 2
    raw = np.asarray(im)
    valid = (raw.reshape(raw.shape[0], raw.shape[1], -1).max(-1) > 0).astype(np.float32)
    valid = np.asarray(Image.fromarray(valid).resize((W, H), Image.BOX), np.float32)
    del raw
    if im.mode in ('I;16', 'I;16B', 'I', 'F'):
        a = to_float(im)
        if a.ndim == 2:
            img = Image.fromarray((a * 255).astype(np.uint8), 'L')
        else:
            img = Image.fromarray((a * 255).astype(np.uint8))
    elif im.mode not in ('RGB', 'L'):
        img = im.convert('RGB') if len(im.getbands()) >= 3 else im.convert('L')
    else:
        img = im
    return img.resize((W, H), Image.LANCZOS), valid

def grade(rgb, contrast=1.08, sat=1.12):
    a = rgb.astype(np.float32) / 255
    m = a.mean()
    a = (a - m) * contrast + m
    l = (a * [0.299, 0.587, 0.114]).sum(-1, keepdims=True)
    a = l + (a - l) * sat
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)

def colour_from_game(grey, game_path, valid):
    W, H = grey.size
    g = np.asarray(grey.convert('L'), np.float32) / 255
    old = Image.open(game_path).convert('RGB').resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(W / 256))
    o = np.asarray(old, np.float32) / 255
    ol = (o * [0.299, 0.587, 0.114]).sum(-1, keepdims=True)
    tint = o / np.maximum(ol, 0.04)
    # keep the old map's overall brightness level, the new map's detail
    m = valid > 0.99
    g = g / max(float(g[m].mean()) if m.any() else g.mean(), 1e-3) * float(ol[..., 0][m].mean() if m.any() else ol.mean())
    return Image.fromarray((np.clip(g[..., None] * tint, 0, 1) * 255).astype(np.uint8))

def palette(img, valid, which, opath):
    W, H = img.size
    g = np.asarray(img.convert('L'), np.float32) / 255
    m = valid > 0.99
    lo, hi = np.percentile(g[m], (1, 99)) if m.any() else (0, 1)
    t = np.clip((g - lo) / max(hi - lo, 1e-3), 0, 1)
    stops = PALETTE[which]
    xs = [s[0] for s in stops]
    rgb = np.stack([np.interp(t, xs, [s[1][c] for s in stops]) for c in range(3)], -1)
    if which == 'charon':
        lat = 90 - (np.arange(H) + 0.5) / H * 180
        cap = np.clip((lat - 55) / 20, 0, 1)[:, None, None]   # Mordor Macula
        rgb = rgb * (1 + cap * (np.array([0.25, -0.12, -0.28])))
    return Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))

def best_shift(img, valid, opath):
    W, H = img.size
    w, h = 512, 256
    new = np.asarray(img.convert('L').resize((w, h), Image.BOX), np.float32)
    vm = np.asarray(Image.fromarray(valid).resize((w, h), Image.BOX)) > 0.99
    old = np.asarray(Image.open(opath).convert('L').resize((w, h), Image.BOX), np.float32)
    def blur(a, r):
        for _ in range(3):   # three box passes ~ a Gaussian; wraps in longitude
            k = 2 * r + 1
            c = np.cumsum(np.concatenate([a[:, -r - 1:], a, a[:, :r]], 1), 1)
            a = (c[:, k:] - c[:, :-k]) / k
            p = np.pad(a, ((r + 1, r), (0, 0)), mode='edge'); c = np.cumsum(p, 0)
            a = (c[k:] - c[:-k]) / k
        return a
    def prep(a):
        a = a - blur(a, 12)
        return blur(a, 1)
    n, o = prep(new) * vm, prep(old) * vm
    rows = slice(h // 6, h - h // 6)
    F = np.fft.rfft(n[rows], axis=1) * np.conj(np.fft.rfft(o[rows], axis=1))
    corr = np.fft.irfft(F, n=w, axis=1).sum(0)
    k = int(np.argmax(corr)); score = corr[k] / (np.abs(corr).mean() + 1e-6)
    shift = (w - k) % w
    if shift > w // 2: shift -= w
    print(f'  correlation peak {score:.1f} at {shift * 360 / w:.0f} deg (0 = already aligned)', flush=True)
    if score < 3.0 or abs(shift) < 3:
        return 0
    return int(round(shift * W / w))

def main():
    os.makedirs(DL, exist_ok=True)
    for name, (url, W, colour, lon0) in SPEC.items():
        if ONLY and name not in ONLY:
            continue
        src = os.path.join(DL, url.rsplit('/', 1)[1])
        fetch(url, src)
        img, valid = load_source(src, W)
        gpath = os.path.join(BODIES, name + '.jpg')
        opath = os.path.join(ORIG, name + '.jpg')
        H = W // 2
        if name in ALIGN:
            shift = best_shift(img, valid, opath)
            if shift:
                img = Image.fromarray(np.roll(np.asarray(img), shift, 1)); valid = np.roll(valid, shift, 1)
                print(f'{name}: aligned by {shift * 360 / W:.0f} deg', flush=True)
        if name in ROLL:
            sh = int(round(ROLL[name] / 360 * W))
            img = Image.fromarray(np.roll(np.asarray(img), sh, 1)); valid = np.roll(valid, sh, 1)
        if colour in PALETTE:
            img = palette(img, valid, colour, opath)
        elif colour == 'game' or img.mode == 'L':
            img = colour_from_game(img, opath, valid)
        rgb = grade(np.asarray(img.convert('RGB')), sat=0.75 if name == 'Triton' else 1.12).astype(np.float32)
        # Fill what the probe never saw from the game's original map, feathered.
        if (valid < 0.99).any():
            old = np.asarray(Image.open(opath).convert('RGB').resize((W, H), Image.BICUBIC), np.float32)
            if colour in PALETTE or name == 'Triton':
                # the fill keeps the old map's texture, in the new map's colour
                ol = (old * [0.299, 0.587, 0.114]).sum(-1, keepdims=True)
                vm = valid > 0.99
                mc = rgb[vm].mean(0); ml = float((mc * [0.299, 0.587, 0.114]).sum())
                old = ol / max(float(ol.mean()), 1) * mc * (ml / max(ml, 1))
            a = np.asarray(Image.fromarray((np.clip(valid, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(W / 400)), np.float32)[..., None] / 255
            # match the old map's brightness to the new one along the seam
            band = (a[..., 0] > 0.2) & (a[..., 0] < 0.8)
            if band.any():
                old = old * (rgb[band].mean(0) / np.maximum(old[band].mean(0), 1))
            rgb = rgb * a + old * (1 - a)
            print(f'{name}: filled {100 * (1 - valid.mean()):.0f} % from the original map', flush=True)
        out = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
        before = Image.open(gpath).size if os.path.exists(gpath) else None
        out.save(gpath, quality=90, optimize=True, subsampling=0)
        print(f'{name}: {before} -> {out.size}, {os.path.getsize(gpath) // 1024} KB', flush=True)
        if src.endswith('.tif') and not os.environ.get('KEEP'):
            os.remove(src)

main()

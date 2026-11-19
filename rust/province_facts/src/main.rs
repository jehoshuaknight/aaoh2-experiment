//! Bakes per-province facts for Astra Novum from the planet maps the game ships:
//! area, centre, coastline, relief, terrain class, rivers, night lights (urban share),
//! ecology, a 2240 climate class and the neighbours with the length of each shared border.
//!
//! usage: province_facts <AstraNovum dir> <Earth|Mars> <out.tsv>
//!
//! The work is a few passes over 8 M pixels and ~500 provinces, done in parallel row bands
//! (rayon); it takes well under a second in release mode.

use image::{GenericImageView, ImageReader};
use rayon::prelude::*;
use std::collections::BTreeMap;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

struct Map {
    w: usize,
    h: usize,
    data: Vec<u8>, // one channel
}

impl Map {
    fn load(path: &Path, channel: usize) -> Option<Map> {
        let img = ImageReader::open(path).ok()?.with_guessed_format().ok()?.decode().ok()?;
        let (w, h) = img.dimensions();
        let rgba = img.to_rgba8();
        let data = rgba.pixels().map(|p| p.0[channel]).collect();
        Some(Map { w: w as usize, h: h as usize, data })
    }
    /// Value at the province map's pixel (x, y) of a map of size (pw, ph), nearest sample.
    fn at(&self, x: usize, y: usize, pw: usize, ph: usize) -> u8 {
        let sx = (x * self.w) / pw;
        let sy = (y * self.h) / ph;
        self.data[sy.min(self.h - 1) * self.w + sx.min(self.w - 1)]
    }
}

#[derive(Default, Clone)]
struct Acc {
    pixels: u64,
    area: f64,
    vx: f64,
    vy: f64,
    vz: f64,
    height: f64,
    height_max: u8,
    rugged: f64,
    river: f64,
    lights: f64,
    ecology: f64,
    coast_km: f64,
    neighbours: BTreeMap<u32, f64>,
}

impl Acc {
    fn merge(mut self, o: Acc) -> Acc {
        self.pixels += o.pixels;
        self.area += o.area;
        self.vx += o.vx;
        self.vy += o.vy;
        self.vz += o.vz;
        self.height += o.height;
        self.height_max = self.height_max.max(o.height_max);
        self.rugged += o.rugged;
        self.river += o.river;
        self.lights += o.lights;
        self.ecology += o.ecology;
        self.coast_km += o.coast_km;
        for (k, v) in o.neighbours {
            *self.neighbours.entry(k).or_default() += v;
        }
        self
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 4 {
        eprintln!("usage: province_facts <AstraNovum dir> <Earth|Mars> <out.tsv>");
        std::process::exit(2);
    }
    let root = PathBuf::from(&args[1]);
    let body = args[2].as_str();
    let tex = root.join("bin/game/textures/bodies");
    let radius_km = if body == "Mars" { 3389.5 } else { 6371.0 };

    // Province ids: R + 256 G + 65536 B.
    let pimg = ImageReader::open(tex.join(format!("{body}_provinces.png")))
        .expect("provinces map")
        .decode()
        .expect("decode provinces")
        .to_rgb8();
    let (pw, ph) = (pimg.width() as usize, pimg.height() as usize);
    let ids: Vec<u32> = pimg.pixels().map(|p| p.0[0] as u32 + ((p.0[1] as u32) << 8) + ((p.0[2] as u32) << 16)).collect();
    let max_id = *ids.iter().max().unwrap_or(&0) as usize;

    let water = Map::load(&tex.join(format!("{body}_water.png")), 0).expect("water map");
    let height = Map::load(&tex.join(format!("{body}_height.png")), 0).expect("height map");
    let rivers = Map::load(&tex.join("Earth_rivers.png"), 0).filter(|_| body == "Earth");
    let lights = Map::load(&tex.join("Earth_lights.jpg"), 0).filter(|_| body == "Earth");
    let ecology = Map::load(&tex.join("Earth_ecology.png"), 1).filter(|_| body == "Earth");

    // Names and regions from the provinces table.
    let mut names: BTreeMap<u32, (String, String)> = BTreeMap::new();
    let table = fs::read_to_string(root.join(format!("bin/game/data/{}/provinces.tsv", body.to_lowercase()))).unwrap_or_default();
    for line in table.lines().filter(|l| !l.starts_with('#') && !l.trim().is_empty()) {
        let f: Vec<&str> = line.split('\t').collect();
        if f.len() >= 3 {
            if let Ok(id) = f[0].parse() {
                names.insert(id, (f[2].to_string(), f[1].to_string()));
            }
        }
    }

    let px_deg = 360.0 / pw as f64;
    let rad = std::f64::consts::PI / 180.0;
    let is_water = |x: usize, y: usize| water.at(x, y, pw, ph) > 127;

    // Parallel pass over row bands; each band keeps its own accumulators.
    let accs: Vec<Acc> = (0..ph)
        .into_par_iter()
        .fold(
            || vec![Acc::default(); max_id + 1],
            |mut acc, y| {
                let lat = 90.0 - (y as f64 + 0.5) * 180.0 / ph as f64;
                let coslat = (lat * rad).cos();
                let pix_area = (radius_km * px_deg * rad).powi(2) * coslat; // km2
                let edge_ew = radius_km * (180.0 / ph as f64) * rad; // a vertical pixel edge, km
                let edge_ns = radius_km * px_deg * rad * coslat; // a horizontal pixel edge, km
                for x in 0..pw {
                    let id = ids[y * pw + x];
                    if id == 0 || is_water(x, y) {
                        continue;
                    }
                    let a = &mut acc[id as usize];
                    let lon = -180.0 + (x as f64 + 0.5) * px_deg;
                    a.pixels += 1;
                    a.area += pix_area;
                    a.vx += coslat * (lon * rad).cos() * pix_area;
                    a.vy += coslat * (lon * rad).sin() * pix_area;
                    a.vz += (lat * rad).sin() * pix_area;
                    let hgt = height.at(x, y, pw, ph);
                    a.height += hgt as f64;
                    a.height_max = a.height_max.max(hgt);
                    // Slope to land neighbours only: the height map drops to 0 at the sea.
                    let (xr, yd) = ((x + 1) % pw, (y + 1).min(ph - 1));
                    let hx = if is_water(xr, y) { hgt as f64 } else { height.at(xr, y, pw, ph) as f64 };
                    let hy = if is_water(x, yd) { hgt as f64 } else { height.at(x, yd, pw, ph) as f64 };
                    a.rugged += ((hx - hgt as f64).abs() + (hy - hgt as f64).abs()) * 0.5;
                    if let Some(r) = &rivers {
                        a.river += (r.at(x, y, pw, ph) > 100) as u8 as f64;
                    }
                    if let Some(l) = &lights {
                        a.lights += l.at(x, y, pw, ph) as f64 / 255.0;
                    }
                    if let Some(e) = &ecology {
                        a.ecology += e.at(x, y, pw, ph) as f64 / 255.0;
                    }
                    // Right and lower neighbours (the map wraps in longitude).
                    for (nx, ny, len) in [((x + 1) % pw, y, edge_ew), (x, y + 1, edge_ns)] {
                        if ny >= ph {
                            continue;
                        }
                        let nid = ids[ny * pw + nx];
                        if is_water(nx, ny) || nid == 0 {
                            a.coast_km += len;
                        } else if nid != id {
                            *a.neighbours.entry(nid).or_default() += len;
                        }
                    }
                }
                acc
            },
        )
        .reduce(
            || vec![Acc::default(); max_id + 1],
            |a, b| a.into_iter().zip(b).map(|(x, y)| x.merge(y)).collect(),
        );

    // Borders found from one side only: make them symmetric. Coasts found from the left/above
    // only are doubled, as a pixel's left and upper edges were not visited.
    let mut accs = accs;
    let mut sym: Vec<BTreeMap<u32, f64>> = vec![BTreeMap::new(); max_id + 1];
    for (id, a) in accs.iter().enumerate() {
        for (&n, &len) in &a.neighbours {
            *sym[id].entry(n).or_default() += len;
            *sym[n as usize].entry(id as u32).or_default() += len;
        }
    }
    for (id, a) in accs.iter_mut().enumerate() {
        a.neighbours = std::mem::take(&mut sym[id]);
        a.coast_km *= 2.0;
    }

    // Terrain thresholds from this planet's own spread of relief.
    let mut rug: Vec<f64> = accs.iter().filter(|a| a.pixels > 0).map(|a| a.rugged / a.pixels as f64).collect();
    rug.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let q = |f: f64| rug.get(((rug.len() as f64 - 1.0) * f) as usize).copied().unwrap_or(0.0);
    let (r_hills, r_mount) = (q(0.55), q(0.85));
    let mut rel: Vec<f64> = accs.iter().filter(|a| a.pixels > 0).map(|a| a.height / a.pixels as f64 / 255.0).collect();
    rel.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let qr = |f: f64| rel.get(((rel.len() as f64 - 1.0) * f) as usize).copied().unwrap_or(1.0);
    let (h_hills, h_mount) = (qr(0.75), qr(0.93));

    let mut out = fs::File::create(&args[3]).expect("output");
    writeln!(out, "# {body}: facts per province, baked by rust/province_facts from the game's maps. Areas and lengths in km.").unwrap();
    writeln!(out, "# relief and ruggedness are on the height map's own 0..1 scale; lights = mean night-light brightness (Earth); ecology = mean of Earth_ecology.png (Earth).").unwrap();
    writeln!(out, "# climate: a 2240 estimate from latitude, relief and ecology (Earth: +3 C world).").unwrap();
    writeln!(out, "id\tname\tregion\tlat\tlon\tarea_km2\tcoast_km\trelief\truggedness\tterrain\triver_share\tlights\tecology\tclimate\tneighbours (id:shared_km)").unwrap();
    for (id, a) in accs.iter().enumerate() {
        if a.pixels == 0 {
            continue;
        }
        let n = a.pixels as f64;
        let lat = a.vz.atan2((a.vx * a.vx + a.vy * a.vy).sqrt()) / rad;
        let lon = a.vy.atan2(a.vx) / rad;
        let relief = a.height / n / 255.0;
        let rugged = a.rugged / n;
        let river = a.river / n;
        let lights_m = a.lights / n;
        let eco = a.ecology / n;
        let terrain = if rugged >= r_mount || relief > h_mount {
            "mountains"
        } else if rugged >= r_hills || relief > h_hills {
            "hills"
        } else if body == "Earth" && eco < 0.12 && lat.abs() < 45.0 {
            "desert"
        } else if river > 0.06 {
            "river plain"
        } else {
            "plains"
        };
        let alat = lat.abs();
        let climate = if body == "Mars" {
            if alat > 65.0 { "polar" } else if relief > h_mount { "highland cold" } else if alat < 30.0 { "temperate arid" } else { "cold steppe" }
        } else if alat > 72.0 {
            "polar"
        } else if relief > h_mount && rugged >= r_mount {
            "alpine"
        } else if alat < 20.0 {
            if eco < 0.15 { "hot desert" } else { "tropical" }
        } else if alat < 38.0 {
            if eco < 0.15 { "hot desert" } else if eco < 0.3 { "semi-arid" } else { "subtropical" }
        } else if alat < 55.0 {
            if eco < 0.2 { "cold steppe" } else { "temperate" }
        } else if alat < 66.0 {
            "boreal (warming)"
        } else {
            "subarctic (thawing)"
        };
        let (name, region) = names.get(&(id as u32)).cloned().unwrap_or_default();
        let neigh: Vec<String> = a.neighbours.iter().map(|(k, v)| format!("{k}:{v:.0}")).collect();
        writeln!(
            out,
            "{id}\t{name}\t{region}\t{lat:.3}\t{lon:.3}\t{:.0}\t{:.0}\t{relief:.3}\t{rugged:.2}\t{terrain}\t{river:.3}\t{lights_m:.3}\t{eco:.3}\t{climate}\t{}",
            a.area,
            a.coast_km,
            neigh.join(";")
        )
        .unwrap();
    }
    eprintln!("{body}: {} provinces written", accs.iter().filter(|a| a.pixels > 0).count());
}

// Mesh shading: one sun, ambient light, a shadow map and an optional
// atmosphere term. Used for terrain, structures and every other opaque mesh,
// plus the additive atmosphere shell around planets.

#include "frame.slang"

[[vk::binding(1, 0)]] Sampler2D shadowMap;
[[vk::binding(0, 1)]] Sampler2D baseColorTexture;
// Planet surfaces: province data (r = province line, g = frontier line, b = nearness to the
// frontier, a = owned land: 0.25 + 0.75 * the province's own shade). White when there is none.
[[vk::binding(1, 1)]] Sampler2D dataTexture;
// Planet surfaces: rgb = surface normal in planet space (0.5 + 0.5 n), a = river on land and, with
// surface flag 16, sea life (plankton) on water. White when none.
[[vk::binding(2, 1)]] Sampler2D reliefTexture;
// Planet surfaces: the body's cloud density, equirectangular in the UV sphere's layout (red).
[[vk::binding(3, 1)]] Sampler2D cloudTexture;
// The air's precomputed tables (rust/astra_bake atmosphere.rs, Hillaire 2020): rows 0..63 the
// transmittance to the top of the air, 64..127 the multiple-scattering factor (sqrt(psi * 20)).
// Column: cosine of the zenith -1..1; row: sqrt(height / thickness). White when there is none.
[[vk::binding(4, 1)]] Sampler2D airTables;

struct DrawData
{
    float4x4 model;
    float4 baseColor;
    float4 params;   // x = emissive, y = atmosphere rim (0 or 1), z = planet surface flags (see surfaceFlags), w = layer opacity
    float4 pointLight; // xyz world position; w = 1: light from this point instead of the sun, no shadows
    float4 extra;      // planet surfaces: rgb = owner colour, w = camera height; cloud slices: slice, alpha, step, rotation
};

float3 lightDirection(float3 worldPosition)
{
    if (draw.pointLight.w > 0.5)
        return normalize(draw.pointLight.xyz - worldPosition);
    return -frame.sunDirection.xyz;
}
[[vk::push_constant]] ConstantBuffer<DrawData> draw;

// --- The planet's air: physically based scattering (Hillaire 2020) --------------------------
// Units: planet radius 1. Earth's air (Rayleigh 5.802, 13.558, 33.1 per Mm, 8 km; Mie 3.996 /
// 4.40 per Mm, 1.2 km; ozone 0.650, 1.881, 0.085 per Mm at 25 +- 15 km) stretched to the drawn
// thickness with its optical depth kept, times frame.air density, haze and tint. Must match
// atmosphere.rs.
static const float AIR_PI = 3.14159265;
// This planet's air, read from its own table's alpha (atmosphere.rs, bake): x = top radius,
// y = density, z = haze; tint = the Rayleigh multipliers. Per material, so every globe in a
// system keeps its own sky.
static float4 gAir = float4(0.0, 0.0, 0.0, 0.0);
static float3 gAirTint = float3(1.0, 1.0, 1.0);
float airParam(int i) { return airTables.SampleLevel(float2((float(i) + 0.5) / 256.0, 0.5 / 128.0), 0.0).a; }
void airLoad()
{
    gAir = float4(1.0 + airParam(0) * 0.1, airParam(1) * 4.0, airParam(2) * 8.0, 0.0);
    gAirTint = float3(airParam(3), airParam(4), airParam(5));
}
// The globe's scale in the world (the planet view draws radius 1; the system view, small globes).
float globeScale() { return length(draw.model[0].xyz); }
float airK() { return (gAir.x - 1.0) / (100000.0 / 6371000.0); }
struct AirMedium
{
    float3 rayleigh;
    float mie;
    float3 extinction;
};
AirMedium airMedium(float h)
{
    float k = airK();
    float perRadius = 6.371 / k * gAir.y; // per Mm -> per planet radius
    float hR = 8000.0 / 6371000.0 * k;
    float hM = 1200.0 / 6371000.0 * k;
    float oc = 25000.0 / 6371000.0 * k;
    float ow = 15000.0 / 6371000.0 * k;
    h = max(h, 0.0);
    float dr = exp(-h / hR);
    float dm = exp(-h / hM);
    float dz = max(0.0, 1.0 - abs(h - oc) / ow);
    AirMedium m;
    m.rayleigh = float3(5.802, 13.558, 33.1) * perRadius * gAirTint * dr;
    m.mie = 3.996 * perRadius * gAir.z * dm;
    m.extinction = m.rayleigh + 4.40 * perRadius * gAir.z * dm + float3(0.650, 1.881, 0.085) * perRadius * dz;
    return m;
}
float2 airUv(float r, float mu, float row0)
{
    float v = sqrt(saturate((r - 1.0) / max(gAir.x - 1.0, 1e-6)));
    return float2((mu * 0.5 + 0.5) * (255.0 / 256.0) + 0.5 / 256.0, (row0 + v * 63.0 + 0.5) / 128.0);
}
// Sunlight left after the air between radius r and the sun at cosine-of-zenith mu.
float3 airTransmittance(float r, float mu) { return airTables.SampleLevel(airUv(r, mu, 0.0), 0.0).rgb; }
float3 airMultiple(float r, float mu)
{
    float3 c = airTables.SampleLevel(airUv(r, mu, 64.0), 0.0).rgb;
    return c * c / 20.0;
}
float airRayleighPhase(float c) { return 3.0 / (16.0 * AIR_PI) * (1.0 + c * c); }
float airMiePhase(float c)
{
    float g = 0.8; // Cornette-Shanks
    float g2 = g * g;
    return 3.0 / (8.0 * AIR_PI) * ((1.0 - g2) * (1.0 + c * c)) / ((2.0 + g2) * pow(1.0 + g2 - 2.0 * g * c, 1.5));
}
// Where a ray (from o, unit d) enters and leaves a sphere of radius rad at the origin; x > y: missed.
float2 airSphere(float3 o, float3 d, float rad)
{
    float b = dot(o, d);
    float c = dot(o, o) - rad * rad;
    float disc = b * b - c;
    if (disc < 0.0)
        return float2(1.0, -1.0);
    float s = sqrt(disc);
    return float2(-b - s, -b + s);
}
// Light the air scatters toward the eye along o + d t, t0..t1 (per unit of sunlight), and how much
// of what lies behind gets through. L = toward the sun.
void airMarch(float3 o, float3 d, float t0, float t1, float3 L, int steps, out float3 inscatter, out float3 transmittance)
{
    inscatter = float3(0.0, 0.0, 0.0);
    transmittance = float3(1.0, 1.0, 1.0);
    if (t1 <= t0)
        return;
    float dt = (t1 - t0) / float(steps);
    float nu = dot(d, L);
    float pR = airRayleighPhase(nu);
    float pM = airMiePhase(nu);
    for (int i = 0; i < steps; i++)
    {
        float3 x = o + d * (t0 + (float(i) + 0.5) * dt);
        float r = length(x);
        float mus = dot(x / r, L);
        AirMedium m = airMedium(r - 1.0);
        float3 sun = airTransmittance(r, mus);
        float3 S = (m.rayleigh * pR + m.mie * pM) * sun + (m.rayleigh + m.mie) * airMultiple(r, mus);
        float3 stepT = exp(-m.extinction * dt);
        // Hillaire's energy-conserving integration over the step.
        float3 Sint = (S - S * stepT) / max(m.extinction, float3(1e-6, 1e-6, 1e-6));
        inscatter += transmittance * Sint;
        transmittance *= stepT;
    }
}

struct VertexInput
{
    [[vk::location(0)]] float3 position;
    [[vk::location(1)]] float3 normal;
    [[vk::location(2)]] float2 uv;
    [[vk::location(3)]] float4 color;
};

struct VertexOutput
{
    float4 clipPosition : SV_Position;
    float3 worldPosition;
    float3 worldNormal;
    float2 uv;
    float4 color;
};

[shader("vertex")]
VertexOutput vertexMain(VertexInput input)
{
    VertexOutput output;
    float4 world = mul(draw.model, float4(input.position, 1.0));
    output.worldPosition = world.xyz;
    // Uniform scale is assumed, so the model matrix itself transforms normals.
    output.worldNormal = mul(draw.model, float4(input.normal, 0.0)).xyz;
    output.uv = input.uv;
    output.color = input.color;
    output.clipPosition = mul(frame.viewProjection, world);
    return output;
}

// Fraction of sunlight reaching a point: 1 = lit, 0 = in shadow.
float sunVisibility(float3 worldPosition, float3 normal, float nDotL)
{
    if (frame.sunDirection.w < 0.5)
        return 1.0;

    // Offset along the normal to avoid self-shadowing on surfaces facing the light at a slant.
    float texel = frame.misc.x;
    float3 biased = worldPosition + normal * (0.02 * (1.0 - nDotL) + 0.004);
    float4 lightClip = mul(frame.lightViewProjection, float4(biased, 1.0));
    float3 ndc = lightClip.xyz / lightClip.w;
    float2 uv = ndc.xy * 0.5 + 0.5;
    if (ndc.z > 1.0)
        return 1.0;

    // 3x3 percentage-closer filter with a manual depth comparison.
    float lit = 0.0;
    for (int y = -1; y <= 1; ++y)
    {
        for (int x = -1; x <= 1; ++x)
        {
            float stored = shadowMap.SampleLevel(uv + float2(x, y) * texel, 0.0).r;
            lit += (ndc.z - 0.0015 <= stored) ? 1.0 : 0.0;
        }
    }
    return lit / 9.0;
}

// ------------------------------------------------------------------------------------------------
// Planet surface helpers. params.z on a planet surface is 1 + flags: 1 = province data,
// 2 = relief map, 4 = cloud map, 8 = flat (an equirectangular map laid out on a plane).
// ------------------------------------------------------------------------------------------------

// 0.1.9: F6 order is Realistic, Peoples of 2240, Strategic, Holo Table. The engine still counts
// 1 = (old) Strategic slot, 2 = (old) Satellite Night slot; the labels were swapped in the .exe, so
// the shader swaps the looks to match.
float mapStyle(float s)
{
    return s > 0.5 && s < 1.5 ? 2.0 : (s > 1.5 && s < 2.5 ? 1.0 : s);
}

uint surfaceFlags()
{
    return draw.params.z > 0.5 ? uint(draw.params.z + 0.5) - 1u : 0u;
}

// A unit direction from equirectangular texture coordinates (the engine's map layout:
// u = (longitude + pi) / 2pi with longitude = atan2(-z, x), v = (pi/2 - latitude) / pi).
float3 directionFromMap(float2 uv)
{
    float lon = uv.x * 6.2831853 - 3.14159265;
    float lat = 1.5707963 - uv.y * 3.14159265;
    return float3(cos(lat) * cos(lon), sin(lat), -cos(lat) * sin(lon));
}

// The radial "up" of a planet surface point: from the position on a globe, from the map
// coordinates on the flat map.
float3 surfaceUp(VertexOutput input)
{
    if ((surfaceFlags() & 8u) != 0u)
        return directionFromMap(input.uv);
    return normalize(input.worldPosition - draw.model[3].xyz);
}

// Cloud density over a point, from the body's cloud map, drifting as the deck does.
float cloudCover(float3 up)
{
    float u = atan2(up.z, up.x) / 6.2831853;
    float v = acos(clamp(up.y, -1.0, 1.0)) / 3.14159265;
    float rot = frac(frame.misc.y / 480.0);
    return smoothstep(0.08, 0.8, cloudTexture.SampleLevel(float2(frac(u + rot), v), 0.0).r);
}

// Helios's ground flashes (GlobeNukes nukeGround), here for launches and impacts: a white
// flash, a fireball, a ring that runs out, a scorch that stays dark and burns at night.
float3 strikeGround(float3 p, inout float3 col, float night)
{
    float3 add = float3(0.0, 0.0, 0.0);
    for (int i = 0; i < 4; i++)
    {
        float t = frame.strikes[i].w;
        if (t < 0.0)
            continue;
        float d = acos(clamp(dot(p, frame.strikes[i].xyz), -1.0, 1.0)) / max(frame.strikeInfo.x, 1e-4);
        if (d > 12.0)
            continue;
        float flash = exp(-t * 5.0) * 1.0 / (1.0 + d * d * 0.25);
        add += float3(1.0, 0.95, 0.88) * flash * 14.0;
        float fb = exp(-t / 2.5) * exp(-d * d * 1.2);
        add += float3(1.0, 0.55, 0.2) * fb * 4.0;
        float rs = 0.35 + 1.15 * pow(t, 0.6);
        float ring = exp(-pow((d - rs) / 0.08, 2.0)) * exp(-t / 2.2) * step(0.2, t);
        add += float3(0.9, 0.85, 0.8) * ring * 0.9;
        float scorch = (1.0 - smoothstep(0.35, 1.1, d)) * smoothstep(0.0, 1.5, t);
        col = lerp(col, col * 0.18, scorch * 0.85);
        float fireN = frac(sin(dot(floor(p * 9000.0), float3(12.9898, 78.233, 37.719))) * 43758.5453);
        float fires = scorch * step(0.82, fireN) * exp(-t / 45.0);
        add += float3(1.0, 0.42, 0.08) * fires * (0.25 + 1.2 * night);
    }
    return add;
}

// ------------------------------------------------------------------------------------------------
// Project Helios ports (the author's own AoC2 globe mod). Its shaders write display colours; this
// renderer works in linear HDR and tone maps (the same ACES fit) and gamma-encodes afterwards, so
// a Helios colour is turned into the scene value that comes out of the post pass as that colour.
// ------------------------------------------------------------------------------------------------

float3 acesFit(float3 x)
{
    return saturate((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14));
}

// Inverse of acesFit for 0 <= y < 1.
float3 acesInverse(float3 y)
{
    y = clamp(y, 0.0, 0.985);
    float3 a = 2.43 * y - 2.51;
    float3 b = 0.59 * y - 0.03;
    float3 c = 0.14 * y;
    return (-b - sqrt(max(b * b - 4.0 * a * c, 0.0))) / (2.0 * a);
}

// A Helios fragment colour (before its own tone map) as a scene colour for this renderer.
float3 heliosToScene(float3 lit)
{
    float3 display = acesFit(lit * 1.02);
    return acesInverse(pow(display, 2.2));
}

float hl_hash(float2 p) { return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453); }
float hl_noise(float2 p)
{
    float2 i = floor(p);
    float2 f = frac(p);
    f = f * f * (3.0 - 2.0 * f);
    return lerp(lerp(hl_hash(i), hl_hash(i + float2(1.0, 0.0)), f.x), lerp(hl_hash(i + float2(0.0, 1.0)), hl_hash(i + float2(1.0, 1.0)), f.x), f.y);
}
float hl_fbm(float2 p)
{
    float v = 0.0, a = 0.5;
    for (int k = 0; k < 4; k++) { v += a * hl_noise(p); p = p * 2.03 + 17.0; a *= 0.5; }
    return v;
}

// Province borders and the coast from the province data, between texels: the four texels around
// the point are read unfiltered and the point's membership of the nearest texel's province (or of
// the land) is blended bilinearly. A border is where that membership crosses one half, so lines
// are thin (about a pixel) and smooth at any zoom, like contour lines, rather than texel steps.
struct ProvinceEdges
{
    float province; // 0..1, a province border
    float coast;    // 0..1, the coast
    float region;   // 0..1, a border between regions (on land)
};

ProvinceEdges provinceEdges(float2 uv)
{
    uint w, h;
    dataTexture.GetDimensions(w, h);
    float2 p = uv * float2(w, h) - 0.5;
    int2 i0 = int2(floor(p));
    float2 f = p - floor(p);
    int2 hi = int2(int(w) - 1, int(h) - 1);
    float4 t00 = dataTexture.Load(int3(clamp(i0, int2(0, 0), hi), 0));
    float4 t10 = dataTexture.Load(int3(clamp(i0 + int2(1, 0), int2(0, 0), hi), 0));
    float4 t01 = dataTexture.Load(int3(clamp(i0 + int2(0, 1), int2(0, 0), hi), 0));
    float4 t11 = dataTexture.Load(int3(clamp(i0 + int2(1, 1), int2(0, 0), hi), 0));
    float4 wts = float4((1.0 - f.x) * (1.0 - f.y), f.x * (1.0 - f.y), (1.0 - f.x) * f.y, f.x * f.y);
    // The nearest texel's province is the reference.
    float ref = f.x < 0.5 ? (f.y < 0.5 ? t00.r : t01.r) : (f.y < 0.5 ? t10.r : t11.r);
    // Sea texels count as members, so the coast never draws a province border.
    float4 same = float4((abs(t00.r - ref) < 0.002 || t00.g < 0.5) ? 1.0 : 0.0, (abs(t10.r - ref) < 0.002 || t10.g < 0.5) ? 1.0 : 0.0,
                         (abs(t01.r - ref) < 0.002 || t01.g < 0.5) ? 1.0 : 0.0, (abs(t11.r - ref) < 0.002 || t11.g < 0.5) ? 1.0 : 0.0);
    float m = dot(wts, same);
    float landK = dot(wts, float4(t00.g, t10.g, t01.g, t11.g));
    // Regions the same way: g holds 128 + region on land, 0 at sea (sea counts as a member).
    float rref = f.x < 0.5 ? (f.y < 0.5 ? t00.g : t01.g) : (f.y < 0.5 ? t10.g : t11.g);
    float4 rsame = float4((abs(t00.g - rref) < 0.002 || t00.g < 0.5 || rref < 0.5) ? 1.0 : 0.0,
                          (abs(t10.g - rref) < 0.002 || t10.g < 0.5 || rref < 0.5) ? 1.0 : 0.0,
                          (abs(t01.g - rref) < 0.002 || t01.g < 0.5 || rref < 0.5) ? 1.0 : 0.0,
                          (abs(t11.g - rref) < 0.002 || t11.g < 0.5 || rref < 0.5) ? 1.0 : 0.0);
    float mr = dot(wts, rsame);
    ProvinceEdges e;
    float dr = max(fwidth(mr), 1e-4);
    e.region = mr < 0.999 ? saturate(1.0 - abs(mr - 0.5) / dr * 0.26) : 0.0; // thick: regions read over provinces
    float dm = max(fwidth(m), 1e-4);
    e.province = m < 0.999 ? saturate(1.0 - abs(m - 0.5) / dm * 0.9) : 0.0;
    float dc = max(fwidth(landK), 1e-4);
    e.coast = (landK > 0.001 && landK < 0.999) ? saturate(1.0 - abs(landK - 0.5) / dc * 0.7) : 0.0;
    return e;
}

// ------------------------------------------------------------------------------------------------
// Border look (0.1.4): the HOI4 ink hierarchy (hairline provinces, bold regions, heaviest frontier)
// with Stellaris-style light: every region glows in its own colour along its edge, fading inward,
// so neighbouring regions meet as two bands of colour with a dark line between them.
// ------------------------------------------------------------------------------------------------

// How far out the camera is: 0 close to the ground, 1 seeing the whole globe.
float borderZoom()
{
    return smoothstep(0.08, 0.9, abs(draw.extra.w));
}

uint2 dataDims() { uint w, h; dataTexture.GetDimensions(w, h); return uint2(w, h); }

// A region's own colour from its id (g = (128 + region) / 255 on land): muted for fills,
// vivid for the light along its edges.
float3 regionHue(float g)
{
    float id = floor(g * 255.0 + 0.5) - 128.0;
    float h = frac(id * 0.61803398875 + 0.07);
    return saturate(abs(frac(h + float3(0.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0) - 1.0);
}
float3 regionTint(float g) { return lerp(float3(0.55, 0.55, 0.55), regionHue(g), 0.62); }
float3 regionVivid(float g) { return lerp(float3(0.5, 0.5, 0.5), regionHue(g), 0.92); }

struct RegionField
{
    float own;       // the region under this point (g channel of the nearest texel)
    float glow;      // share of the nearby ground that is another region: 0 inside, about 0.5 on the border
    float provGlow;  // the same for the province, narrower
};

// A soft distance to the nearest other region: 16 taps on a golden-angle spiral, weighted toward
// the centre, wrapping around the map in longitude. Cheap (16 loads) and free of the banding a
// ring search gives.
RegionField regionField(float2 uv, float radiusTexels)
{
    uint w, h;
    dataTexture.GetDimensions(w, h);
    float2 p = uv * float2(w, h) - 0.5;
    int2 c = int2(floor(p + 0.5));
    c.x = (c.x % int(w) + int(w)) % int(w);
    c.y = clamp(c.y, 0, int(h) - 1);
    float4 t0 = dataTexture.Load(int3(c, 0));
    RegionField f;
    f.own = t0.g;
    float differ = 0.0, pdiffer = 0.0, total = 0.0, ptotal = 0.0;
    [unroll]
    for (int k = 0; k < 16; k++)
    {
        float a = float(k) * 2.39996323;
        float r = radiusTexels * sqrt((float(k) + 0.5) / 16.0);
        int2 q = int2(floor(p + float2(cos(a), sin(a)) * r + 0.5));
        q.x = (q.x % int(w) + int(w)) % int(w);
        q.y = clamp(q.y, 0, int(h) - 1);
        float4 t = dataTexture.Load(int3(q, 0));
        float wt = 1.0 - r / (radiusTexels + 1.0);
        bool land = t.g > 0.5;
        differ += (land && abs(t.g - t0.g) > 0.002) ? wt : 0.0;
        total += wt;
        float pw = r < radiusTexels * 0.45 ? wt : 0.0;
        pdiffer += (land && abs(t.r - t0.r) > 0.002) ? pw : 0.0;
        ptotal += pw;
    }
    f.glow = t0.g > 0.5 ? differ / max(total, 1e-4) : 0.0;
    f.provGlow = t0.g > 0.5 ? saturate(pdiffer / max(ptotal, 1e-4) * 2.0) : 0.0;
    return f;
}

// Glow width in texels of the province data: wide from orbit, narrow close in.
float regionGlowRadius()
{
    return lerp(3.0, 10.0, borderZoom());
}

// ------------------------------------------------------------------------------------------------
// Peoples of 2240 (0.1.7): map style 2 draws the ethnic map in game. The region comes exactly from the
// province data (g channel); inside it the province is the nearest centre, with a ragged, noisy edge
// between neighbours, and inside the province its peoples interleave in patches by their shares.
// ------------------------------------------------------------------------------------------------
#include "ethnicity_tables.slang"

float3 ethColour(uint g)
{
    uint c = ethColourHex(g);
    return float3(float((c >> 16) & 255u), float((c >> 8) & 255u), float(c & 255u)) / 255.0;
}

// The colour of the people at a point (display values), and how mixed the place is (0..1).
// One octave of value noise at f cycles per degree, faded to its mean where a cycle gets smaller than
// about two pixels (fw = degrees per pixel), so far zooms never alias into streaks.
// Integer lattice hash (no sin(): its precision loss draws stripes along 127x + 311y = const).
float ethHash(int2 c)
{
    uint2 q = uint2(c + int2(1 << 20, 1 << 20));
    uint h = q.x * 1597334677u ^ q.y * 3812015801u;
    h = (h ^ (h >> 16)) * 2246822519u;
    h = (h ^ (h >> 13)) * 3266489917u;
    h ^= h >> 16;
    return float(h & 0xFFFFFFu) / 16777216.0;
}
float ethNoise(float2 p)
{
    float2 i = floor(p);
    float2 f = p - i;
    f = f * f * (3.0 - 2.0 * f);
    int2 c = int2(i);
    return lerp(lerp(ethHash(c), ethHash(c + int2(1, 0)), f.x), lerp(ethHash(c + int2(0, 1)), ethHash(c + int2(1, 1)), f.x), f.y);
}
float ethHash3(int3 c)
{
    uint3 q = uint3(c + int3(1 << 20, 1 << 20, 1 << 20));
    uint h = q.x * 1597334677u ^ q.y * 3812015801u ^ q.z * 2654435769u;
    h = (h ^ (h >> 16)) * 2246822519u;
    h = (h ^ (h >> 13)) * 3266489917u;
    h ^= h >> 16;
    return float(h & 0xFFFFFFu) / 16777216.0;
}
float ethNoise3(float3 p)
{
    float3 i = floor(p);
    float3 f = p - i;
    f = f * f * (3.0 - 2.0 * f);
    int3 c = int3(i);
    float x00 = lerp(ethHash3(c), ethHash3(c + int3(1, 0, 0)), f.x);
    float x10 = lerp(ethHash3(c + int3(0, 1, 0)), ethHash3(c + int3(1, 1, 0)), f.x);
    float x01 = lerp(ethHash3(c + int3(0, 0, 1)), ethHash3(c + int3(1, 0, 1)), f.x);
    float x11 = lerp(ethHash3(c + int3(0, 1, 1)), ethHash3(c + int3(1, 1, 1)), f.x);
    return lerp(lerp(x00, x10, f.y), lerp(x01, x11, f.y), f.z);
}
// One octave of noise on the sphere (no stretching at any latitude or longitude) at f cycles per
// degree, faded to its mean where a cycle shrinks below about two pixels (fw = degrees per pixel).
float aaOct(float3 up, float f, float fw, float seed)
{
    float k = saturate(1.0 - (fw * f - 0.2) / 0.3);
    float3 off = float3(frac(seed * 0.618), frac(seed * 0.377), frac(seed * 0.271)) * 97.0;
    return lerp(0.5, ethNoise3(up * (57.29578 * f) + off), k);
}

// A people's own noise field on the sphere: blobs a few hundred km across, finer where the view is close,
// busier in cities. Seeded by the people, so a people's blobs run on across province borders.
float ethField(float3 up, float fw, float seed, float city)
{
    // Domain warp: the sample point drifts along a slow vector field, so blobs curl and finger into each
    // other like real settlement patterns instead of round spots.
    float3 w = float3(aaOct(up, 0.12, fw, seed + 21.0), aaOct(up, 0.12, fw, seed + 34.0), aaOct(up, 0.12, fw, seed + 55.0)) - 0.5;
    float3 q = normalize(up + w * 0.16);
    return 0.46 * aaOct(q, 0.22, fw, seed) + 0.27 * aaOct(q, 0.60, fw, seed + 3.1) + 0.17 * aaOct(q, 1.70, fw, seed + 7.3)
         + 0.10 * aaOct(q, 4.6, fw, seed + 9.9)                       // fine fringes, only when zoomed in
         + (aaOct(q, 4.5, fw, seed + 1.7) - 0.5) * 0.5 * city;
}

void ethPick(uint g, float sh, float3 up, float fw, float city, float planetSeed,
             inout float best, inout float second, inout uint gb, inout uint gs)
{
    if (sh <= 0.005)
        return;
    float sc = 0.33 * log(sh) + 4.5 * (ethField(up, fw, float(g) * 1.37 + planetSeed, city) - 0.5);
    if (sc > best) { second = best; gs = gb; best = sc; gb = g; }
    else if (sc > second) { second = sc; gs = g; }
}

// The colour of the people at a point (display values), and how mixed the place is (0..1).
// Clean, cartographic look (0.1.13): every province is filled flat with its main people; a province
// whose second people holds 25 % or more gets diagonal stripes of that people's colour (the Paradox
// convention). provR / regionG: the engine's province data at this texel. stripe: 0..1 position across
// a stripe period, stripeW: its screen footprint (for anti-aliasing and the far-zoom blend).
float3 peoplesAt(float provR, float regionG, bool earth, float stripe, float stripeW, out float mixed)
{
    mixed = 0.0;
    int r = int(floor(regionG * 255.0 + 0.5)) - 128;
    uint nreg = earth ? EARTH_REGIONS : MARS_REGIONS;
    if (r < 0 || uint(r) >= nreg)
        return float3(0.45, 0.43, 0.40);
    uint rg = uint(r) + (earth ? 0u : EARTH_REGIONS);
    uint2 range = regionRange(rg);
    // The exact province, if the engine's province value is the id's low byte; otherwise the whole region
    // is filled with the region's own mix (exact region borders, never a guessed split).
    uint r8 = uint(floor(provR * 255.0 + 0.5));
    int exact = -1;
    for (uint i = range.x; i < range.y && i < range.x + 64u; i++)
    {
        if (((provinceCentre(i) >> 21) & 255u) == r8) { exact = int(i); break; }
    }
    uint g1, g2;
    float s1, s2;
    if (exact >= 0)
    {
        uint3 mx = provinceMix(uint(exact));
        g1 = mx.x & 511u; g2 = (mx.x >> 9) & 511u;
        s1 = float((mx.y >> 16) & 127u) / 100.0; s2 = float((mx.x >> 18) & 127u) / 100.0;
    }
    else
    {
        uint2 rm = regionMix(rg);
        g1 = rm.x & 511u; g2 = (rm.x >> 9) & 511u;
        s1 = float(rm.y & 127u) / 100.0; s2 = float((rm.x >> 18) & 127u) / 100.0;
    }
    mixed = 1.0 - s1;
    float3 c1 = ethColour(g1);
    if (s2 < 0.25 || g2 == g1)
        return c1;
    float3 c2 = ethColour(g2);
    // Stripe width follows the minority's weight (a quarter to half of each period).
    float f = clamp(s2 / max(s1 + s2, 1e-3), 0.25, 0.5);
    float aa = max(stripeW, 1e-4);
    float band = smoothstep(f - aa, f + aa, stripe) * (1.0 - smoothstep(1.0 - aa, 1.0, stripe));
    float3 striped = lerp(c2, c1, band);
    // Too far out to draw stripes cleanly: show the blend instead of shimmering lines.
    return lerp(striped, lerp(c1, c2, f), smoothstep(0.18, 0.35, stripeW));
}

// Helios's map styles for a planet surface, from GlobeTerrain's globe shader (u_style branches).
// style 1 = Strategic, 2 = Satellite Night, 3 = Holo Table.
float3 heliosStyledSurface(VertexOutput input, float4 texel, float style)
{
    float3 up = surfaceUp(input);
    float lat = degrees(asin(clamp(up.y, -1.0, 1.0)));
    float lon = degrees(atan2(-up.z, up.x));
    float alat0 = abs(lat);
    float time = frame.misc.y;
    float camH = draw.extra.w;

    // The satellite colour, as Helios grades it.
    float3 sat0 = pow(max(texel.rgb, 0.0), 1.0 / 2.2);
    float3 sat = pow(sat0, 1.55) * 0.76;
    float lum = dot(sat, float3(0.299, 0.587, 0.114));
    sat = lerp(float3(lum, lum, lum), sat, 0.88);
    sat *= float3(0.96, 1.0, 1.02);
    bool water = texel.a < 0.5;
    float ul = water ? 0.0 : saturate((texel.a - 0.5) * 2.0);

    float4 pd = dataTexture.Sample(input.uv);
    bool hasData = (surfaceFlags() & 1u) != 0u && draw.extra.w >= 0.0;
    float4 relief = reliefTexture.Sample(input.uv);
    float river = (surfaceFlags() & 2u) != 0u && texel.a >= 0.5 ? relief.a : 0.0;
    ProvinceEdges edges = provinceEdges(input.uv);
    float provE = hasData ? edges.province : 0.0;
    float coastLine = hasData && pd.b > 0.0 ? edges.coast : 0.0;
    float regionLine = hasData ? edges.region : 0.0;
    float ctryE = max(coastLine, regionLine);
    float coastE = coastLine >= regionLine ? 1.0 : 0.0;
    float ctryN = hasData && !water ? pd.b : 0.0;
    float near = hasData && water ? pd.b : 0.0;
    float own = hasData && !water && pd.a > 0.1 ? 1.0 : 0.0;
    float hsh = saturate((pd.a - 0.25) / 0.75);
    float3 lc = draw.extra.rgb;
    float3 ow = lc / max(max(lc.r, max(lc.g, lc.b)), 0.05);

    float3 vn = (surfaceFlags() & 2u) != 0u ? normalize(relief.rgb * 2.0 - 1.0)
              : ((surfaceFlags() & 8u) != 0u ? up : normalize(input.worldNormal));
    float3 n = water ? up : vn;
    float3 L = lightDirection(input.worldPosition);
    float diff = max(dot(n, L), 0.0);
    float sunH = dot(up, L);
    float dayK = smoothstep(-0.1, 0.25, sunH);

    float lumS = dot(sat, float3(0.299, 0.587, 0.114));
    float rel = clamp(0.70 + lumS * 1.1, 0.75, 1.18);
    float3 S; float3 lineP; float3 lineC; float3 coastC; float3 grid; float gridA; float3 riverC; float3 glowC; float flat_ = 0.0;
    float3 lakeC = float3(-1.0, -1.0, -1.0); float pW = 0.6; float bGlow = 0.0; float scan = 0.0; float dots = 0.0; float dim = 1.0;
    float2 cv = float2(0.0, 0.0);
    if (style < 1.5)
    {
        // Strategic
        float3 ink = lerp(float3(0.7, 0.7, 0.7), ow, 0.45) * 0.20;
        S = water ? float3(0.006, 0.009, 0.016) + float3(0.03, 0.12, 0.14) * near * 0.35 : lerp(float3(lumS, lumS, lumS) * 0.32 + 0.03, ink, own) * rel;
        lineP = float3(0.22, 0.62, 0.66); lineC = float3(0.40, 0.95, 0.98); coastC = float3(0.30, 0.80, 0.86); grid = float3(0.6, 0.65, 0.7); gridA = 0.09; riverC = float3(0.16, 0.42, 0.48); glowC = float3(0.45, 1.0, 1.0); scan = 0.07;
        cv = float2(0.40, 0.30);
    }
    else if (style < 2.5 && hasData)
    {
        // Peoples of 2240 (0.1.7): each people in its own colour over gentle relief, dark ink borders.
        float mixed;
        // The screen footprint in degrees comes from the map uv (no seam jump at the date line).
        float2 duv = fwidth(input.uv) * float2(360.0 * cos(radians(lat)), 180.0);
        float fw = max(max(duv.x, duv.y), 1e-4);
        float4 pdN = dataTexture.Load(int3(int2(clamp(input.uv, 0.0, 0.9999) * float2(dataDims())), 0));
        // Diagonal stripes in map degrees (period 1.5 deg, which divides 360, so no seam at the date line).
        float st = (input.uv.x * 360.0 - (90.0 - input.uv.y * 180.0)) / 1.5;
        float stW = min(fwidth(st), 1.0);
        float3 pc = peoplesAt(pdN.r, pdN.g, (surfaceFlags() & 32u) != 0u, frac(st), stW, mixed);
        // Gentler colours: a touch less saturated, so a map of hundreds of peoples stays easy on the eye.
        float pl = dot(pc, float3(0.299, 0.587, 0.114));
        pc = lerp(float3(pl, pl, pl), pc, 0.86);
        float rel2 = clamp(0.80 + lumS * 0.9, 0.82, 1.12);
        S = water ? float3(0.004, 0.009, 0.018) : pc * pc * 0.62 * rel2;
        lineP = float3(0.03, 0.03, 0.035); lineC = float3(0.004, 0.004, 0.006); coastC = float3(0.30, 0.42, 0.52) * 0.7;
        grid = float3(0.5, 0.5, 0.5); gridA = 0.0; riverC = float3(0.05, 0.10, 0.16); glowC = float3(1.0, 1.0, 1.0);
        flat_ = 1.0; pW = 0.55;
        cv = float2(0.0, 0.0);
    }
    else if (style < 2.5)
    {
        // Satellite Night: always night, city lights leaning toward the owner's colour, thin glowing borders
        float halo = water ? 0.0 : saturate((baseColorTexture.SampleBias(input.uv, 2.5).a - 0.5) * 2.0);
        float3 lcol = lerp(float3(1.0, 0.72, 0.38), ow * 0.85 + 0.15, own * 0.45);
        S = water ? float3(0.004, 0.007, 0.014) : sat * 0.07 + lcol * (pow(ul, 1.4) * 1.25 + 0.12 * smoothstep(0.04, 0.6, halo));
        lineP = float3(0.05, 0.05, 0.06); lineC = float3(0.85, 0.74, 0.50) * 0.55; coastC = float3(0.30, 0.36, 0.46) * 0.6; grid = float3(0.5, 0.5, 0.5); gridA = 0.0; riverC = float3(0.04, 0.06, 0.09); glowC = float3(1.0, 0.85, 0.55); flat_ = 1.0; pW = 0.0;
        cv = float2(0.35, 0.30);
    }
    else
    {
        // Holo Table: a blue war-room hologram, see-through countries, glowing edges, a scan sweep
        float3 hb = float3(0.25, 0.65, 1.0);
        float sw = frac((lat + 90.0) / 180.0 - time * 0.05);
        float sweep = exp(-sw * 30.0) + exp(-(1.0 - sw) * 120.0);
        S = water ? float3(0.0, 0.010, 0.030) + hb * near * 0.03 : (own > 0.5 ? lerp(hb, ow, 0.25) * (0.10 + 0.05 * hsh) : hb * 0.045 * rel);
        S += hb * sweep * (water ? 0.04 : 0.12);
        lineP = hb * 0.30; lineC = hb * 1.15; coastC = hb * 0.75; grid = hb; gridA = 0.08; riverC = hb * 0.20; glowC = float3(0.70, 0.90, 1.0); flat_ = 0.8;
        lakeC = float3(0.0, 0.012, 0.035); bGlow = 0.25; scan = 0.06; dots = 0.06;
        cv = float2(0.70, 0.25);
    }
    // Every province a shade of its own and, where the style allows colour, a tint of the owner's hue.
    if (!water && own > 0.5)
    {
        float Ls = dot(S, float3(0.299, 0.587, 0.114));
        float m1 = max(ow.r, max(ow.g, ow.b)), m0 = min(ow.r, min(ow.g, ow.b));
        float3 hu = (ow - m0) / max(m1 - m0, 0.10);
        S = lerp(S, S * (0.62 + 0.76 * hsh) + 0.035 * hsh, cv.x);
        S = lerp(S, hu * max(Ls, 0.03) * 1.5, cv.y);
    }
    float3 o = S * lerp(lerp(0.62, 1.0, dayK) * (0.9 + 0.15 * diff), 1.0, flat_);
    // Map hill shading (0.1.5): cartographers light relief from the north-west, whatever the sun
    // does, so mountains read on every style.
    if (!water && (surfaceFlags() & 2u) != 0u)
    {
        float3 east = normalize(cross(float3(0.0, 1.0, 0.0), up) + float3(1e-5, 0.0, 0.0));
        float3 north = cross(up, east);
        float3 mapL = normalize(up * 1.1 + north * 0.7 - east * 0.7);
        float hill = dot(vn, mapL) / max(dot(up, mapL), 0.2);
        o *= lerp(1.0, clamp(hill, 0.55, 1.45), style < 2.5 ? 0.75 : 0.5);
    }
    // Sea (0.1.5): a continental shelf from the land nearby (the coverage mips of the surface map),
    // depth contours like a nautical chart, slow wave texture and light along the coasts.
    if (water)
    {
        float l1 = saturate(baseColorTexture.SampleLevel(input.uv, 3.0).a * 2.0);
        float l2 = saturate(baseColorTexture.SampleLevel(input.uv, 5.0).a * 2.0);
        float l3 = saturate(baseColorTexture.SampleLevel(input.uv, 7.0).a * 2.0);
        float shelf = saturate(l1 * 1.6 + l2 * 0.9 + l3 * 0.5);
        float3 deep = style < 1.5 ? float3(0.004, 0.010, 0.020) : (style < 2.5 ? float3(0.003, 0.005, 0.011) : float3(0.0, 0.008, 0.026));
        float3 shallow = style < 1.5 ? float3(0.035, 0.13, 0.16) : (style < 2.5 ? float3(0.010, 0.020, 0.034) : float3(0.03, 0.14, 0.30));
        float3 sea = lerp(deep, shallow, shelf * shelf);
        float2 wp = float2(lon * cos(radians(lat)), lat);
        float waves = hl_fbm(wp * 0.9 + float2(time * 0.012, time * 0.008)) - 0.5;
        sea *= 1.0 + waves * 0.35;
        float iso = abs(frac(shelf * 5.0) - 0.5) / max(fwidth(shelf * 5.0), 1e-4);
        float contour = (1.0 - smoothstep(0.5, 1.5, iso)) * step(0.05, shelf) * (style < 2.5 ? 0.6 : 1.0);
        sea += coastC * contour * 0.10 * lerp(1.0, 0.45, borderZoom());
        sea += coastC * pow(saturate(l1), 2.5) * 0.14; // light along the coast
        o = lerp(o, sea, 0.85);
    }
    o = lerp(o, riverC, river * 0.85); // rivers, in the style's own colour
    float zP = lerp(0.10, 0.75, smoothstep(0.55, 0.08, camH));
    o = lerp(o, lineP, provE * (1.0 - ctryE) * zP * pW);
    if (bGlow > 0.0 && !water)
        o += lineC * bGlow * smoothstep(0.10, 0.90, ctryN) * (1.0 - ctryE); // soft glow along the frontier
    // Region light (0.1.4): each region's edge glows in its own colour pulled toward the style's
    // line colour, fading inward; a faint animated shimmer runs along it from orbit.
    if (hasData && !water && !(style > 1.5 && style < 2.5))
    {
        RegionField rf = regionField(input.uv, regionGlowRadius());
        float3 rt = lerp(lineC, regionTint(rf.own) * max(max(lineC.r, lineC.g), lineC.b), 0.55);
        float shimmer = 0.85 + 0.15 * sin(time * 1.3 + (lon + lat) * 0.35);
        float g = pow(saturate(rf.glow * 3.0), 1.3) * (1.0 - ctryE);
        o += rt * g * (style < 2.5 ? 0.55 : 0.70) * lerp(0.6, 1.0, borderZoom()) * shimmer;
        o += lineP * rf.provGlow * 0.10 * zP * pW * (1.0 - ctryE);
    }
    o = lerp(o, coastE > 0.5 ? coastC : lineC, ctryE * (coastE > 0.5 ? 0.7 : 0.9));
    float2 gl = float2(lon, lat) / 15.0;
    float2 gd = abs(frac(gl + 0.5) - 0.5) / max(fwidth(gl), float2(1e-4, 1e-4));
    o += grid * max(1.0 - smoothstep(0.0, 1.3, gd.y), (1.0 - smoothstep(0.0, 1.3, gd.x)) * (1.0 - smoothstep(70.0, 84.0, alat0))) * gridA;
    if (scan > 0.0)
        o *= 1.0 - scan + scan * step(0.5, frac(input.clipPosition.y * 0.5));
    if (dots > 0.0)
    {
        float2 dg = float2(lon * cos(radians(lat)), lat) / 2.5;
        dg.x += 0.5 * fmod(floor(dg.y) + 1000.0, 2.0);
        float2 df = (frac(dg) - 0.5) / max(fwidth(dg.y), 1e-4);
        o += grid * dots * (1.0 - smoothstep(0.7, 1.5, length(df))) * (1.0 - smoothstep(70.0, 84.0, alat0)); // a hex dot grid
    }
    float3 dummy = o;
    o += strikeGround(up, dummy, 1.0) * 0.08;
    return heliosToScene(o * dim);
}

// Helios's "Realistic" treatment of provinces over this renderer's own lighting: the owner's
// colour painted over the land, province lines darkened, a tint along the inside of the frontier,
// a frontier line that is dark by day and bright at night.
float3 heliosRealisticPaint(float3 albedo, float4 texel, float4 pd, float sunP)
{
    bool water = texel.a < 0.5;
    if (water || pd.a < 0.1)
        return albedo;
    float3 lc = pow(max(draw.extra.rgb, 0.0), 1.0 / 2.2); // Helios's colours are display values
    float3 lw = float3(0.299, 0.587, 0.114);
    float3 col = pow(max(albedo, 0.0), 1.0 / 2.2);
    float relief = clamp(dot(col, lw) / 0.30, 0.75, 1.35);
    float3 ink = lerp(float3(dot(lc, lw), dot(lc, lw), dot(lc, lw)), lc, 0.65);
    ink = lerp(ink, ink / max(max(ink.r, max(ink.g, ink.b)), 0.2) * 0.60, 0.7);
    ink *= 0.85 + 0.30 * saturate((pd.a - 0.25) / 0.75); // a shade per province
    // Regions read as a political map: each takes a light tint of its own colour (0.1.4).
    ink = lerp(ink, ink * (regionTint(pd.g) * 1.35), 0.22);
    // Helios paints the owner's colour at the land's own brightness (relief kept). Here the paint
    // is held at the brightness of the ground under it, so the world stays photographic.
    float ground = dot(col, lw);
    float3 paint = ink / max(dot(ink, lw), 0.05) * ground * relief / 1.05;
    float k = 0.42;
    col = lerp(col, lerp(col * 0.95, paint, 0.58 * lerp(0.65, 1.0, sunP)), k);
    return pow(col, 2.2);
}

float3 heliosRealisticLines(float3 lit, float4 texel, float4 pd, float nightK, float2 uv)
{
    bool water = texel.a < 0.5;
    float camH = draw.extra.w;
    ProvinceEdges edges = provinceEdges(uv);
    float provE = edges.province;
    float coastLine = pd.b > 0.0 ? edges.coast : 0.0;
    float ctryE = max(coastLine, edges.region);
    float ctryN = water ? 0.0 : pd.b;
    float owned = !water && pd.a > 0.1 ? 1.0 : 0.0;
    float3 myC = draw.extra.rgb;
    lit = lerp(lit, lit * 0.45, provE * (1.0 - ctryE) * lerp(0.35, 0.9, smoothstep(0.60, 0.08, camH)));
    lit = lerp(lit, myC * max(dot(lit, float3(0.333, 0.333, 0.333)), 0.002) * 2.2 + lit * 0.45, ctryN * owned * (1.0 - ctryE) * 0.24);
    float ovK = 0.65;
    lit += myC * 0.004 * nightK * ovK * owned;
    lit += float3(0.010, 0.016, 0.020) * provE * (1.0 - ctryE) * nightK * 0.35 * lerp(0.3, 1.0, smoothstep(0.60, 0.08, camH));
    lit += myC * 0.02 * ctryN * owned * (1.0 - ctryE) * nightK * ovK;
    // Region light (0.1.4): a band of the region's own colour along its edge, fading inward, painted
    // at the ground's brightness by day and glowing faintly by night; a bright rim just inside the
    // dark border line, so two neighbours meet as two coloured bands with ink between.
    if (!water && pd.g > 0.5)
    {
        RegionField rf = regionField(uv, regionGlowRadius());
        float3 rt = regionVivid(rf.own);
        float zoom = borderZoom();
        float band = saturate(rf.glow * 3.2) * (1.0 - edges.region);
        float rim = smoothstep(0.24, 0.46, rf.glow) * (1.0 - edges.region);
        float bright = max(dot(lit, float3(0.299, 0.587, 0.114)), 0.0005);
        float3 paint = rt / max(dot(rt, float3(0.299, 0.587, 0.114)), 0.05) * min(bright, 0.35);
        lit = lerp(lit, paint * 1.3, band * lerp(0.40, 0.65, zoom) * (1.0 - nightK * 0.5));
        lit = lerp(lit, paint * 1.7, rim * lerp(0.30, 0.55, zoom) * (1.0 - nightK * 0.5));
        lit += rt * (band * 0.010 + rim * 0.020) * nightK * lerp(0.6, 1.0, zoom);
        // Province edges get a whisper of the same light from up close (HOI4's light province grid).
        lit = lerp(lit, paint * 1.15, rf.provGlow * 0.12 * (1.0 - zoom) * (1.0 - ctryE));
    }
    float bk = coastLine >= edges.region ? 0.3 : 0.88; // coasts lighter than region borders
    float3 bc = lerp(float3(0.0002, 0.0002, 0.0003), float3(0.31, 0.38, 0.42) * 0.25, nightK);
    lit = lerp(lit, bc, ctryE * lerp(bk, 0.75, nightK));
    return lit;
}

// How smoggy the air over a texel is (0..1): the night lights' alpha averaged over a wide area
// (a coarse mip), so smog spreads beyond the cities that make it; over the sea it thins out.
float smoggy(float2 uv, float water)
{
    float wide = baseColorTexture.SampleLevel(uv, 5.0).a;
    float wider = baseColorTexture.SampleLevel(uv, 7.0).a;
    float industry = saturate((max(wide, wider * 1.15) - 0.5) * 2.0);
    return saturate(smoothstep(0.02, 0.35, industry) * (1.0 - 0.6 * water));
}

// Close-up detail: value noise on the unit sphere, so ground seen from low orbit keeps
// variation finer than the baked surface map (the "detail texture" trick of terrain engines).
float detailHash(float3 p)
{
    p = frac(p * 0.3183099 + 0.1);
    p *= 17.0;
    return frac(p.x * p.y * p.z * (p.x + p.y + p.z));
}
float detailNoise(float3 x)
{
    float3 i = floor(x);
    float3 f = frac(x);
    f = f * f * (3.0 - 2.0 * f);
    return lerp(lerp(lerp(detailHash(i), detailHash(i + float3(1, 0, 0)), f.x),
                     lerp(detailHash(i + float3(0, 1, 0)), detailHash(i + float3(1, 1, 0)), f.x), f.y),
                lerp(lerp(detailHash(i + float3(0, 0, 1)), detailHash(i + float3(1, 0, 1)), f.x),
                     lerp(detailHash(i + float3(0, 1, 1)), detailHash(i + float3(1, 1, 1)), f.x), f.y), f.z);
}


// ------------------------------------------------------------------------------------------------
// Solar system bodies seen as plain globes (0.1.6): living gas giants, crater relief, ice glints,
// volcanic hot spots, haze rims. A plain globe is a sphere mesh: its normal points from the centre.
// ------------------------------------------------------------------------------------------------
bool isGlobe(VertexOutput input)
{
    float3 radial = input.worldPosition - draw.model[3].xyz;
    return dot(normalize(input.worldNormal), normalize(radial)) > 0.995 && draw.params.x < 2.95;
}

// How banded the map is around this latitude (gas giants, Venus's and Titan's cloud decks): colour
// changes far more north-south than east-west at a coarse mip.
float bandedness(float2 uv)
{
    float3 c = baseColorTexture.SampleLevel(uv, 5.0).rgb;
    float h = 0.0, v = 0.0;
    [unroll] for (int k = 1; k <= 3; k++)
    {
        h += length(baseColorTexture.SampleLevel(uv + float2(0.11 * k, 0.0), 5.0).rgb - c);
        v += length(baseColorTexture.SampleLevel(uv + float2(0.0, 0.012 * k), 5.0).rgb - c);
    }
    return smoothstep(1.4, 2.6, v / (h + 0.01));
}

// Gas giant weather: zonal bands sway east and west at alternating speeds (a slow oscillation, so the
// map never smears), and the clouds boil gently along them.
float2 giantFlow(float2 uv, float banded, float time)
{
    float lat = (0.5 - uv.y) * 3.14159265;
    float jets = sin(lat * 14.0) * 0.6 + sin(lat * 31.0 + 1.3) * 0.4;
    float sway = jets * 0.010 * sin(time * 0.011 + lat * 3.0);
    float2 p = float2(uv.x * 40.0, uv.y * 20.0);
    float boil = (hl_fbm(p + float2(time * 0.010, 0.0)) - 0.5) * 0.0025;
    float boil2 = (hl_fbm(p * 2.3 - float2(0.0, time * 0.013)) - 0.5) * 0.0012;
    return uv + float2(sway + boil, boil2) * banded;
}

// The map's whole-planet colour (the top mip): rims and haze take it.
float3 globeAverage()
{
    return baseColorTexture.SampleLevel(float2(0.5, 0.5), 12.0).rgb;
}

// Relief from the map's own shading: a bump from its brightness slope, strongest where the
// terminator rakes across craters and ridges.
float3 globeBump(float2 uv, float3 n)
{
    uint w, h, mips;
    baseColorTexture.GetDimensions(0, w, h, mips);
    float2 d = float2(1.5 / float(w), 1.5 / float(h));
    float3 lw = float3(0.299, 0.587, 0.114);
    float l0 = dot(baseColorTexture.SampleLevel(uv, 0.0).rgb, lw);
    float lx = dot(baseColorTexture.SampleLevel(uv + float2(d.x, 0.0), 0.0).rgb, lw);
    float ly = dot(baseColorTexture.SampleLevel(uv + float2(0.0, d.y), 0.0).rgb, lw);
    float3 east = normalize(cross(float3(0.0, 1.0, 0.0), n) + float3(1e-5, 0.0, 0.0));
    float3 north = cross(n, east);
    float k = 2.2;
    return normalize(n - (east * (lx - l0) - north * (ly - l0)) * k);
}

[shader("fragment")]
float4 fragmentLit(VertexOutput input) : SV_Target
{
    float4 texel = baseColorTexture.Sample(input.uv);
    // A star's photosphere (emissive >= 3: the system view's sun). Self-lit granulation in the
    // star's colour, limb-darkened as real stars are (I(mu) = 1 - u(1 - mu), u about 0.6 for
    // the Sun), and slightly redder toward the limb, where the light leaves cooler layers.
    if (draw.params.x >= 2.95)
    {
        float3 n = normalize(input.worldNormal);
        float mu = saturate(dot(n, normalize(frame.cameraPosition.xyz - input.worldPosition)));
        float limb = 1.0 - 0.62 * (1.0 - mu) - 0.12 * (1.0 - mu * mu);
        float3 tint = draw.baseColor.rgb * lerp(float3(1.0, 0.72, 0.5), float3(1.0, 1.0, 1.0), sqrt(mu));
        // 0.1.6: a boiling photosphere. Granules (small, fast), supergranules (large, slow), a few
        // sunspots with penumbrae, and bright faculae toward the limb.
        float t = frame.misc.y;
        float gran = detailNoise(n * 180.0 + float3(t * 0.15, -t * 0.11, t * 0.07)) * 0.6
                   + detailNoise(n * 420.0 - float3(t * 0.21, t * 0.17, 0.0)) * 0.4;
        float sup = detailNoise(n * 22.0 + t * 0.01);
        float spotN = detailNoise(n * 9.0 + float3(3.1, 7.7, 1.3) + t * 0.002);
        float umbra = smoothstep(0.80, 0.86, spotN) * smoothstep(0.55, 0.0, abs(n.y) - 0.1);
        float penumbra = smoothstep(0.74, 0.80, spotN) * smoothstep(0.55, 0.0, abs(n.y) - 0.1);
        float fac = smoothstep(0.62, 0.75, detailNoise(n * 40.0 + 11.0)) * pow(1.0 - mu, 2.0);
        float surf = (0.86 + 0.22 * gran) * (0.94 + 0.12 * sup);
        surf *= 1.0 - 0.45 * penumbra - 0.45 * umbra;
        surf += fac * 0.35;
        return float4(tint * texel.rgb * limb * 2.2 * surf, 1.0);
    }
    uint flags = surfaceFlags();
    bool surface = draw.params.z > 0.5;
    // Planet surfaces in one of the Helios map styles are shaded entirely by the style.
    if (surface && frame.misc.z > 0.5)
        return float4(heliosStyledSurface(input, texel, mapStyle(frame.misc.z)), 1.0);

    // Plain globes in the system view (0.1.6).
    bool globe = !surface && isGlobe(input);
    bool airyGlobe = globe && draw.params.y > 1.5;
    float banded = globe ? bandedness(input.uv) : 0.0;
    if (globe && banded > 0.0)
    {
        // Wrap in longitude by hand (the sampler may clamp) and keep the unshifted derivatives,
        // so the seam picks no wrong mip level.
        float2 fuv = giantFlow(input.uv, banded, frame.misc.y);
        fuv = float2(frac(fuv.x), clamp(fuv.y, 0.0, 1.0));
        texel = baseColorTexture.SampleGrad(fuv, ddx(input.uv), ddy(input.uv));
    }

    float3 toSun = lightDirection(input.worldPosition);
    float3 toCamera = normalize(frame.cameraPosition.xyz - input.worldPosition);
    float3 up = surface ? surfaceUp(input) : float3(0.0, 1.0, 0.0);
    float4 relief = reliefTexture.Sample(input.uv);
    // Relief: the baked planet-space normal (heights at texel scale), else the mesh normal.
    float3 normal = normalize(input.worldNormal);
    if ((flags & 8u) != 0u)
        normal = up;
    if ((flags & 2u) != 0u)
    {
        // The baked relief, eased toward the smooth surface so slopes read as terrain and not
        // as an embossed ripple (strongest from far out, softer close in).
        float3 baked = normalize(relief.rgb * 2.0 - 1.0);
        float camHeight = length(frame.cameraPosition.xyz - draw.model[3].xyz) / length(draw.model[0].xyz) - 1.0;
        normal = normalize(lerp(up, baked, lerp(0.45, 0.75, saturate(camHeight / 2.0))));
    }
    bool flat = (flags & 8u) != 0u;
    if (flat)
        toSun = -frame.sunDirection.xyz; // the flat map is lit as the globe would be
    // Close-up detail, the terrain-engine way: below about one planet radius the ground gains
    // texture finer than the map, chosen by what the map shows (green: field parcels and
    // woods; dry: dune ridges and gravel; steep or high: ridged rock), with a matching bump.
    float closeLand = 0.0;
    float closeTone = 1.0;
    if (surface && !flat && texel.a >= 0.5)
    {
        float camH = length(frame.cameraPosition.xyz - draw.model[3].xyz) / length(draw.model[0].xyz) - 1.0;
        closeLand = saturate((0.9 - camH) / 0.75);
        if (closeLand > 0.0)
        {
            float3 c = texel.rgb;
            float veg = saturate((c.g - 0.5 * (c.r + c.b)) * 9.0 + 0.15);
            float arid = saturate((c.r - c.b) * 3.0 - 0.15) * (1.0 - veg);
            float snow = saturate((min(c.r, min(c.g, c.b)) - 0.62) * 5.0);
            float steep = saturate((1.0 - dot(normal, up)) * 6.0);
            float3 tA = normalize(cross(up, abs(up.y) < 0.95 ? float3(0, 1, 0) : float3(1, 0, 0)));
            float3 tB = cross(up, tA);
            // Height of the micro-relief at a point: rock ridges, dunes, gentle rolling ground.
            float fields = detailHash(floor(up * 2600.0 + detailNoise(up * 700.0) * 1.5));
            float rough = detailNoise(up * 1400.0) * 0.55 + detailNoise(up * 4200.0) * 0.3 + detailNoise(up * 12000.0) * 0.15;
            float ridge = 1.0 - abs(detailNoise(up * 1800.0) * 2.0 - 1.0);
            float dune = sin(dot(up, tA) * 26000.0 + detailNoise(up * 900.0) * 9.0) * 0.5 + 0.5;
            closeTone = 1.0;
            closeTone *= lerp(1.0, 0.86 + 0.28 * fields, veg * 0.8);                // parcels
            closeTone *= lerp(1.0, 0.9 + 0.2 * dune, arid * (1.0 - steep) * 0.7);   // dunes
            closeTone *= lerp(1.0, 0.78 + 0.44 * ridge * rough, max(steep, snow * 0.4)); // rock
            closeTone *= 0.9 + 0.2 * rough;
            closeTone = lerp(1.0, closeTone, closeLand);
            // Bump: the same micro-relief tilting the normal (finite differences on the sphere).
            float e = 1.0 / 6000.0;
            float h0 = rough + ridge * steep * 0.8 + dune * arid * 0.3;
            float hx = detailNoise((up + tA * e) * 1400.0) * 0.55 + detailNoise((up + tA * e) * 4200.0) * 0.3 + detailNoise((up + tA * e) * 12000.0) * 0.15;
            float hy = detailNoise((up + tB * e) * 1400.0) * 0.55 + detailNoise((up + tB * e) * 4200.0) * 0.3 + detailNoise((up + tB * e) * 12000.0) * 0.15;
            hx += ridge * steep * 0.8 + dune * arid * 0.3;
            hy += ridge * steep * 0.8 + dune * arid * 0.3;
            float bumpK = closeLand * (0.35 + 0.65 * max(steep, arid * 0.5));
            normal = normalize(normal - (tA * (hx - h0) + tB * (hy - h0)) * 2.2 * bumpK);
        }
    }
    // Crater and ridge relief on airless globes (0.1.6), raking at the terminator.
    if (globe && !airyGlobe && banded < 0.5)
        normal = globeBump(input.uv, normal);
    float nDotL = saturate(dot(normal, toSun));

    float3 albedo = draw.baseColor.rgb * input.color.rgb * texel.rgb;
    if (closeLand > 0.0)
    {
        // Land seen from low orbit: the map's own colour carries the micro-texture of what it
        // shows (see closeDetail), so a 5 km texel breaks into fields, dunes and rock.
        albedo *= closeTone;
    }
    float4 provinceData = dataTexture.Sample(input.uv);
    bool provinces = (flags & 1u) != 0u && draw.extra.w >= 0.0;
    float water = surface ? saturate((0.5 - texel.a) * 8.0) : 0.0;
    float sunUp = dot(up, toSun);
    if (surface)
    {
        // Rivers (Earth): dark water threads, clearer up close.
        float river = (flags & 2u) != 0u ? relief.a * (1.0 - water) : 0.0;
        albedo = lerp(albedo, float3(0.012, 0.026, 0.045), river * lerp(0.35, 0.85, smoothstep(0.6, 0.05, abs(draw.extra.w))));
        // Built-up land by day (Helios city lights): dense lights read as grey city.
        float li = saturate((texel.a - 0.5) * 2.0) * (1.0 - water);
        float dens = smoothstep(0.08, 0.9, li);
        albedo = lerp(albedo, float3(0.13, 0.125, 0.115) * (0.8 + 0.4 * dens), dens * 0.45);
        // Pollution (surface flag 32, Earth in 2240): a brown-grey haze over all the day side,
        // thick smog over the industrial belts (where the lights, blurred, are densest), dull
        // grey-green coastal water.
        if ((flags & 32u) != 0u)
        {
            float smog = smoggy(input.uv, water);
            float3 haze = float3(0.115, 0.098, 0.072);
            albedo = lerp(albedo * float3(0.92, 0.90, 0.86), haze, 0.20 + 0.60 * smog);
            albedo = lerp(albedo, albedo * float3(0.88, 0.98, 0.68), water * 0.8); // murky seas
        }
        if (provinces)
            albedo = heliosRealisticPaint(albedo, texel, provinceData, smoothstep(-0.12, 0.15, sunUp));
        // Plankton blooms: slow green-teal swirls over living water, drifting with time.
        float life = (flags & 16u) != 0u ? relief.a * water : 0.0;
        if (life > 0.0)
        {
            float2 sp = float2(atan2(up.z, up.x) * 9.0, up.y * 14.0);
            float drift = frame.misc.y * 0.004;
            float swirl = hl_fbm(sp + float2(drift, drift * 0.7) + hl_fbm(sp * 0.5 - drift) * 2.5);
            float bloom = smoothstep(0.45, 0.72, swirl) * life;
            albedo = lerp(albedo, float3(0.030, 0.105, 0.075), bloom * 0.55);
        }
    }

    float visibility = draw.pointLight.w > 0.5 || flat ? 1.0 : sunVisibility(input.worldPosition, normal, nDotL);
    // A planet with air (surface flag 64): sunlight reaches the ground through it, reddened and
    // dimmed toward the terminator (the transmittance table), and the land is seen through it.
    // Tables on a surface (flag 64) or on a plain globe (params.y >= 2: gas giants, Venus, Titan).
    bool hasAir = surface ? (flags & 64u) != 0u : draw.params.y > 1.5;
    if (hasAir && !flat)
        airLoad();
    bool airy = hasAir && !flat && gAir.x > 1.0;
    float airUp = surface ? sunUp : dot(normalize(input.worldPosition - draw.model[3].xyz), toSun);
    float3 sunAir = airy ? airTransmittance(1.0002, airUp) : float3(1.0, 1.0, 1.0);
    // Terminator: relief cannot light ground the sun has set on.
    float terminator = surface ? (airy ? smoothstep(-0.03, 0.02, sunUp) : smoothstep(-0.06, 0.08, sunUp)) : 1.0;
    // Cloud shadows on the ground, from the same deck that drifts overhead.
    float shade = 1.0;
    if ((flags & 4u) != 0u)
        shade = 1.0 - 0.55 * cloudCover(normalize(up + toSun * 0.012));
    // Skylight: the blue of the sky lighting the ground from every side (multiple scattering).
    float3 sky = airy ? airMultiple(1.0002, airUp) * AIR_PI * 3.0 : float3(0.0, 0.0, 0.0);
    float3 color = albedo * (frame.ambient.rgb + frame.sunColor.rgb * (sunAir * nDotL * visibility * terminator * shade + sky));
    color += albedo * draw.params.x;

    if (globe)
    {
        float3 gn = normalize(input.worldNormal);
        float mu = saturate(dot(gn, toCamera));
        float sunG = dot(gn, toSun);
        float3 avg = globeAverage();
        float t = frame.misc.y;
        if (banded > 0.3 || airyGlobe)
        {
            // Gas giants and hazy worlds: limb darkening, and a haze rim lit by the sun.
            color *= lerp(1.0, pow(max(mu, 0.02), 0.32), max(banded, 0.5));
            float rim = pow(1.0 - mu, 3.5) * smoothstep(-0.25, 0.35, sunG);
            float3 haze = lerp(avg, float3(dot(avg, float3(0.333, 0.333, 0.333)), dot(avg, float3(0.333, 0.333, 0.333)), dot(avg, float3(0.333, 0.333, 0.333))), -0.4);
            color += saturate(haze) * frame.sunColor.rgb * rim * 0.55;
        }
        else
        {
            // Ice: bright, pale ground glints (Europa, Enceladus, Triton's caps).
            float lum = dot(albedo, float3(0.3, 0.59, 0.11));
            float sat = max(albedo.r, max(albedo.g, albedo.b)) - min(albedo.r, min(albedo.g, albedo.b));
            float ice = smoothstep(0.35, 0.7, lum) * (1.0 - smoothstep(0.08, 0.25, sat));
            float3 hv = normalize(toSun + toCamera);
            color += frame.sunColor.rgb * (pow(saturate(dot(normal, hv)), 70.0) * 0.20 + pow(1.0 - mu, 4.0) * 0.03) * ice * step(0.0, sunG);
            // Io: dark volcanic paterae on sulphur-yellow ground glow on the night side and flicker.
            float3 wide = baseColorTexture.SampleLevel(input.uv, 5.0).rgb;
            float sulphur = smoothstep(0.15, 0.30, wide.r - wide.b) * smoothstep(0.08, 0.18, wide.g - wide.b * 1.2);
            float wl = dot(wide, float3(0.3, 0.59, 0.11));
            float tl = dot(texel.rgb, float3(0.3, 0.59, 0.11));
            float dark = smoothstep(0.30, 0.12, tl) * smoothstep(0.75, 0.5, tl / max(wl, 0.02)); // small spots, darker than around
            float night = 1.0 - smoothstep(-0.1, 0.1, sunG);
            float flicker = 0.75 + 0.25 * sin(t * 2.3 + input.uv.x * 400.0) * sin(t * 1.7 + input.uv.y * 300.0);
            color += float3(1.0, 0.36, 0.08) * sulphur * dark * (0.4 + 0.6 * night) * flicker * 0.35;
        }
    }

    // Planet surfaces carry a mask in the texture's alpha channel:
    // below 0.5 is water, 0.5..1 is land with city-light brightness.
    if (surface)
    {
        float3 h = normalize(toSun + toCamera);
        float lit = step(0.0, sunUp) * visibility * shade;
        float3 wn = up;
        float nh = saturate(dot(wn, h));
        float nv = max(dot(wn, toCamera), 1e-3);
        float fresnel = 0.02 + 0.98 * pow(1.0 - saturate(dot(wn, toCamera)), 5.0);
        float3 waterLight;
        if (airy)
        {
            // Water as the films and AAA engines shade it: a GGX microfacet sun glint, Schlick
            // Fresnel (2% head-on, a mirror at grazing angles) and Smith shadowing, roughened by
            // wind (a slow ripple of the roughness), and the sky's colour reflected.
            float ripple = hl_fbm(float2(atan2(up.z, up.x) * 60.0, up.y * 80.0) + frame.misc.y * 0.02);
            float a = lerp(0.045, 0.11, ripple);
            float a2 = a * a;
            float nl = max(sunUp, 0.0);
            float dd = nh * nh * (a2 - 1.0) + 1.0;
            float D = a2 / (AIR_PI * dd * dd);
            float k = a * 0.5;
            float G = (nl / (nl * (1.0 - k) + k)) * (nv / (nv * (1.0 - k) + k));
            float F = 0.02 + 0.98 * pow(1.0 - saturate(dot(h, toCamera)), 5.0);
            float spec = D * G * F / max(4.0 * nl * nv, 1e-3) * nl * AIR_PI; // x pi: the diffuse here is albedo * E
            waterLight = frame.sunColor.rgb * sunAir * spec;
            waterLight += frame.sunColor.rgb * airMultiple(1.0002, sunUp) * AIR_PI * 9.0 * fresnel * float3(0.55, 0.75, 1.0);
        }
        else
        {
            // Water: a sharp sun glint, a broad sheen, and the sky reflected at grazing angles.
            waterLight = frame.sunColor.rgb * (pow(nh, 900.0) * 0.45 + pow(nh, 80.0) * 0.02) * fresnel * 6.0;
            waterLight += frame.atmosphere.rgb * frame.atmosphere.w * fresnel * 0.6 * smoothstep(-0.1, 0.3, sunUp);
        }
        color += waterLight * water * lit;
        // Ice and snow: bright, pale ground gets a soft sheen.
        float lum = dot(albedo, float3(0.3, 0.59, 0.11));
        float sat = max(albedo.r, max(albedo.g, albedo.b)) - min(albedo.r, min(albedo.g, albedo.b));
        float ice = (1.0 - water) * smoothstep(0.35, 0.6, lum) * (1.0 - smoothstep(0.05, 0.18, sat));
        color += frame.sunColor.rgb * pow(saturate(dot(normal, h)), 120.0) * 0.12 * ice * lit;

        // City lights at night (Helios): amber where sparse, paler where dense.
        float li = saturate((texel.a - 0.5) * 2.0) * (1.0 - water);
        float night = 1.0 - smoothstep(-0.15, 0.05, sunUp);
        float dens = smoothstep(0.03, 0.7, li);
        float3 gc = lerp(float3(1.0, 0.50, 0.16), float3(1.0, 0.74, 0.45), smoothstep(0.7, 1.0, li));
        color += gc * (0.04 + 0.95 * dens * dens) * li * night * 0.95;
        // Bioluminescent seas: living water glows a faint blue at night, shimmering along the coasts.
        float glowLife = (flags & 16u) != 0u ? relief.a * water : 0.0;
        if (glowLife > 0.0)
        {
            float2 gp = float2(atan2(up.z, up.x) * 40.0, up.y * 60.0);
            float shimmer = hl_fbm(gp + frame.misc.y * 0.05) * (0.7 + 0.3 * sin(frame.misc.y * 0.9 + gp.x * 0.3));
            color += float3(0.02, 0.22, 0.42) * pow(glowLife, 1.3) * smoothstep(0.35, 0.8, shimmer) * night * 0.35;
        }
        // Smog lit from below at night: the cities' sodium glow spread through the haze.
        if ((flags & 32u) != 0u)
            color += float3(0.55, 0.30, 0.11) * smoggy(input.uv, water) * night * 0.035;
        if (provinces)
            color = heliosRealisticLines(color, texel, provinceData, night, input.uv);
        color += strikeGround(up, color, night) * 0.08;
    }

    // Aerial perspective: the land seen through the air between it and the eye, dimmed by it and
    // with the sunlit air's own blue (or, at the terminator, red-orange) added.
    if (airy)
    {
        float3 centre = draw.model[3].xyz;
        float scale = globeScale();
        float3 o = (frame.cameraPosition.xyz - centre) / scale;
        float3 d = input.worldPosition - frame.cameraPosition.xyz;
        float tEnd = length(d);
        d /= tEnd;
        tEnd /= scale;
        float2 shell = airSphere(o, d, gAir.x);
        float tStart = max(shell.x, 0.0);
        float3 inscatter, through;
        airMarch(o, d, tStart, tEnd, lightDirection(input.worldPosition), 10, inscatter, through);
        color = color * through + inscatter * frame.sunColor.rgb * AIR_PI;
    }
    // Atmosphere haze (planets without the tables): air seen at a grazing angle on the day side.
    else if (draw.params.y > 0.5 && frame.atmosphere.w > 0.0 && !flat)
    {
        float rim = pow(1.0 - saturate(dot(normalize(input.worldNormal), toCamera)), 3.0);
        float day = saturate(saturate(dot(normalize(input.worldNormal), toSun)) * 1.5 + 0.1);
        color += frame.atmosphere.rgb * frame.atmosphere.w * rim * day * 0.6;
    }
    return float4(color, 1.0);
}

// Cloud layer: the texture's alpha is the cloud coverage. Lit by the sun with
// a little wrap so the terminator is soft; nearly invisible at night.
[shader("fragment")]
float4 fragmentClouds(VertexOutput input) : SV_Target
{
    float3 normal = normalize(input.worldNormal);
    float4 texel = baseColorTexture.Sample(input.uv);
    float coverage = texel.a * draw.baseColor.a * draw.params.w;
    if (draw.params.z < -0.5)
        return float4(draw.baseColor.rgb * texel.rgb, coverage); // unlit overlay (map territory)
    float sun = saturate(dot(normal, lightDirection(input.worldPosition)) * 0.9 + 0.12);
    // Clouds on a planet with air (flag 64) are lit by sunlight that came through it: gold and
    // rose along the terminator.
    float3 sunAir = float3(1.0, 1.0, 1.0);
    if ((uint(draw.params.z + 0.5) & 64u) != 0u)
        airLoad();
    if ((uint(draw.params.z + 0.5) & 64u) != 0u && gAir.x > 1.0)
        sunAir = airTransmittance(1.004, dot(normal, lightDirection(input.worldPosition))) * 1.08;
    // The texture's colour tints the layer (white for clouds; province colours for overlays).
    float3 color = draw.baseColor.rgb * texel.rgb * (frame.ambient.rgb * 0.5 + frame.sunColor.rgb * sunAir * sun * 0.75);
    color += draw.baseColor.rgb * texel.rgb * draw.params.x; // a faint glow of its own (lettering at night)
    return float4(color, coverage);
}

// Volumetric clouds, ported from Project Helios (GlobeTerrain's cloud shader). The deck is drawn
// as a stack of thin shells, lowest first; each shell keeps only the cloud whose column height
// reaches its slice, and is lit with relief from the density gradient, self-shadowing toward the
// sun, a golden terminator and a dark night side. The texture's red channel is the density.
// params: x = softness, y = wispiness, w = opacity. extra: x = slice, y = slice alpha, z = slice step, w = rotation.
struct CloudLookup
{
    float bias; // mip bias that widens toward the poles
    float polar; // density of the polar patch
    float soft; // density threshold
};

float vcDensity(CloudLookup cl, float2 uv)
{
    float vc_pb = cl.bias;
    float vc_pd = cl.polar;
    float vc_soft = cl.soft;
    float la = abs(90.0 - uv.y * 180.0);
    float k = smoothstep(68.0, 80.0, la);
    float raw = k < 1.0 ? baseColorTexture.SampleBias(float2(uv.x, clamp(uv.y, 10.0 / 180.0, 170.0 / 180.0)), vc_pb).r : 0.0;
    if (k > 0.0)
        raw = lerp(raw, vc_pd, k);
    raw *= 1.0 - 0.5 * smoothstep(58.0, 72.0, la);
    return smoothstep(vc_soft, 0.8, raw);
}

// Helios's flat-map clouds (FlatClouds): the same deck seen from straight above on the map,
// with detail noise, light from the sun's side and a soft shadow cast on the map beneath.
float4 flatClouds(VertexOutput input)
{
    float3 dir = directionFromMap(input.uv);
    float u = frac(atan2(dir.z, dir.x) / 6.2831853 + draw.extra.w);
    float v = acos(clamp(dir.y, -1.0, 1.0)) / 3.14159265;
    float2 uv = float2(u, v);
    float time = frame.misc.y;
    CloudLookup cl;
    cl.soft = 0.08;
    cl.bias = 0.0;
    cl.polar = 0.0;
    float d = vcDensity(cl, uv);
    float2 nuv = uv * float2(260.0, 150.0);
    float det = hl_fbm(nuv * float2(0.6, 1.0) + float2(time * 0.02, 0.0));
    float det2 = hl_fbm(nuv * 2.4 - float2(0.0, time * 0.03));
    float col = d * (0.72 + 0.4 * det) - 0.08 * det2 * (1.0 - d);
    float cover = smoothstep(0.10, 0.50, col);
    float2 sun = float2(-0.0035, -0.0025);
    float toward = vcDensity(cl, uv + sun) * 0.6 + vcDensity(cl, uv + sun * 2.2) * 0.4;
    float relief = (hl_fbm(nuv + float2(-0.7, -0.5)) - hl_fbm(nuv + float2(0.7, 0.5))) * 0.9;
    float lit = clamp(0.78 - toward * 0.55 * (1.0 - col * 0.5) + relief + col * 0.18, 0.0, 1.0);
    float3 cc = lerp(float3(0.40, 0.44, 0.52), float3(0.95, 0.94, 0.92), lit);
    // Night: the clouds go dark with the ground under them.
    float sunUp = dot(dir, -frame.sunDirection.xyz);
    cc *= lerp(0.05, 1.0, smoothstep(-0.15, 0.2, sunUp));
    float alpha = draw.baseColor.a;
    float ac = cover * 0.88 * alpha;
    float sd = vcDensity(cl, uv - sun * 3.0);
    float as = sd * 0.30 * alpha;
    float A = ac + as * (1.0 - ac);
    if (A < 0.01)
        discard;
    float3 c = cc * ac / max(A, 1e-4);
    // Map styles tint the clouds too.
    float style = mapStyle(frame.misc.z);
    if (style > 0.5)
    {
        float4 ctint = style < 1.5 ? float4(0.55, 0.66, 0.70, 0.55) : style < 2.5 ? float4(0.22, 0.25, 0.32, 0.55) : float4(0.40, 0.70, 1.00, 0.35);
        c = dot(c, float3(0.30, 0.59, 0.11)) * ctint.rgb * 1.08;
        A *= ctint.a;
    }
    return float4(heliosToScene(c), A);
}

[shader("fragment")]
float4 fragmentVolumetricClouds(VertexOutput input) : SV_Target
{
    if (draw.params.z > 1.5)
        return flatClouds(input);
    float slice = draw.extra.x;
    float sliceAlpha = draw.extra.y;
    float sliceStep = draw.extra.z;
    float wispy = draw.params.y;
    float alpha = draw.baseColor.a * draw.params.w;
    float time = frame.misc.y;
    CloudLookup cl;
    cl.soft = draw.params.x;

    float3 local = input.worldPosition - draw.model[3].xyz;
    float3 up = normalize(local);
    float2 uv = input.uv + float2(draw.extra.w, 0.0);
    float sy = clamp(abs(up.y), 0.0, 1.0);
    cl.bias = max(log2(1.0 / max(sqrt(1.0 - min(sy, 0.985) * min(sy, 0.985)), 0.02)) - 1.0, 0.0);
    cl.polar = 0.0;
    if (sy > 0.92)
    {
        float la0 = degrees(asin(sy));
        float pa0 = uv.x * 6.2831853;
        float2 pq = float2(cos(pa0), sin(pa0)) * (90.0 - la0);
        cl.polar = smoothstep(0.30, 0.85, baseColorTexture.SampleBias(float2(0.37 + pq.x * 0.0045, 0.30 + pq.y * 0.009), 1.0).r);
    }
    float d = vcDensity(cl, uv) * step(0.01, alpha);
    if (d < 0.02)
        discard;
    float alat = degrees(asin(sy));
    float pk = smoothstep(68.0, 72.0, alat);
    float pa = uv.x * 6.2831853;
    float2 nuvP = float2(cos(pa), sin(pa)) * (90.0 - alat) / 1.2 + 500.0;
    float2 nuvE = uv * float2(260.0, 150.0);
    float det = 0.0;
    float det2 = 0.0;
    if (pk < 1.0)
    {
        det += (1.0 - pk) * hl_fbm(nuvE * float2(0.6, 1.0) + float2(time * 0.02, 0.0));
        det2 += (1.0 - pk) * hl_fbm(nuvE * 2.4 - float2(0.0, time * 0.03));
    }
    if (pk > 0.0)
    {
        det += pk * hl_fbm(nuvP * float2(0.6, 1.0) + float2(time * 0.02, 0.0));
        det2 += pk * hl_fbm(nuvP * 2.4 - float2(0.0, time * 0.03));
    }
    float col = d * (0.72 + 0.4 * det) - 0.08 * det2 * (1.0 - d);
    col = lerp(col, d * det2, wispy);
    float jit = frac(sin(dot(input.clipPosition.xy, float2(12.9898, 78.233)) + slice * 91.7) * 43758.5453) - 0.5;
    float f = slice + jit * sliceStep * smoothstep(0.15, 0.5, col);
    float cover = smoothstep(f - 0.08, f + 0.22, col);
    if (cover < 0.01)
        discard;
    float2 e = float2(1.0 / 2048.0, 1.0 / 1024.0);
    float dx = vcDensity(cl, uv + float2(e.x, 0.0)) - vcDensity(cl, uv - float2(e.x, 0.0)) + 0.35 * (det - 0.5) * 0.4;
    float dy = vcDensity(cl, uv + float2(0.0, e.y)) - vcDensity(cl, uv - float2(0.0, e.y)) + 0.35 * (det2 - 0.5) * 0.4;
    float polK = smoothstep(80.0, 87.0, alat);
    dx *= 1.0 - polK;
    dy *= 1.0 - polK;
    // Tangents along +u (east) and +v (south) of the sphere's texture mapping.
    float3 tU = abs(up.y) > 0.999 ? float3(1.0, 0.0, 0.0) : normalize(float3(-up.z, 0.0, up.x));
    float3 tV = cross(tU, up);
    float3 n0 = normalize(up * (0.6 + f) - tU * dx * 2.2 - tV * dy * 2.2);
    float hb = col * 0.007;
    float3 dpdx = ddx(local), dpdy = ddy(local);
    float dhx = ddx(hb), dhy = ddy(hb);
    float3 r1 = cross(dpdy, up), r2 = cross(up, dpdx);
    float det0 = dot(dpdx, r1);
    float3 sg = sign(det0) * (dhx * r1 + dhy * r2);
    float3 nb = normalize(abs(det0) * up - sg * 1.2 + float3(1e-7, 1e-7, 1e-7));
    float3 n = normalize(nb + (n0 - up) * 0.35);
    float3 L = lightDirection(input.worldPosition);
    float3 V = normalize(frame.cameraPosition.xyz - input.worldPosition);
    float diff = clamp(dot(n, L) * 0.6 + 0.4, 0.0, 1.0) * max(dot(up, L) * 0.8 + 0.2, 0.0);
    // Shadow from the cloud between this point and the sun.
    float2 lshift = float2(dot(L, tU), dot(L, tV)) * 0.0075;
    float toward = vcDensity(cl, uv + lshift * (1.5 - f));
    toward = lerp(toward, d, smoothstep(78.0, 86.0, alat));
    float occl = clamp(toward * (1.0 - f) * 0.7 + (1.0 - f) * (0.25 * d), 0.0, 0.85);
    float3 top = float3(0.92, 0.91, 0.89);
    float3 base = float3(0.36, 0.40, 0.48);
    float3 c = lerp(base, top, clamp(diff * (1.0 - occl) + f * 0.25, 0.0, 1.0));
    c += 0.18 * (1.0 - cover) * max(dot(up, L), 0.0);
    float limb = 1.0 - max(dot(up, V), 0.0);
    float graze = smoothstep(0.015, 0.2, max(dot(up, V), 0.0));
    float day = smoothstep(-0.15, 0.2, dot(up, L));
    float sh = dot(up, L);
    // Helios's golden terminator, narrowed: only the clouds the sun is setting on turn gold.
    float gold = exp(-pow((sh - 0.03) / 0.08, 2.0));
    c *= lerp(float3(1.0, 1.0, 1.0), float3(1.0, 0.70, 0.48), gold * 0.8);
    c += float3(0.45, 0.16, 0.12) * exp(-pow((sh + 0.02) / 0.04, 2.0)) * (1.0 - f) * 0.35;
    c *= lerp(0.05, 1.0, day);
    float a = cover * sliceAlpha * alpha * (0.9 + 0.3 * limb) * graze;
    // A tinted world (Venus's yellow deck, Titan's haze) keeps the light and shade, in its colour.
    float tinted = saturate(dot(abs(draw.baseColor.rgb - 1.0), float3(1.0, 1.0, 1.0)) * 4.0);
    c = lerp(c, dot(c, float3(0.30, 0.59, 0.11)) * draw.baseColor.rgb * 1.08, tinted);
    // Map styles tint and thin the clouds (Helios GlobeStyle.CLOUD: Strategic, Satellite Night, Holo Table).
    float style = mapStyle(frame.misc.z);
    if (style > 0.5)
    {
        float4 ctint = style < 1.5 ? float4(0.55, 0.66, 0.70, 0.55) : style < 2.5 ? float4(0.22, 0.25, 0.32, 0.55) : float4(0.40, 0.70, 1.00, 0.35);
        c = dot(c, float3(0.30, 0.59, 0.11)) * ctint.rgb * 1.08;
        a *= ctint.a;
    }
    return float4(heliosToScene(c), clamp(a, 0.0, 0.97));
}

// Atmosphere shell, drawn inside-out with additive blending. Only the ring of
// shell visible beyond the planet's edge survives the depth test, and it is
// brightest right at the edge.
[shader("fragment")]
float4 fragmentAtmosphere(VertexOutput input) : SV_Target
{
    // Project Helios's atmosphere (GlobeTerrain): an 8-step ray march through air whose density
    // falls off exponentially with height (scale height H, planet radius 1), Rayleigh-like
    // colour, an orange-red terminator band, forward scattering toward the sun and a faint blue
    // halo past the limb; over the planet itself only the thin grazing band at the edge.
    // baseColor: rgb = tint (white = Earth-like air), a = strength scale. params.x = shell radius.
    float3 center = draw.model[3].xyz;
    float3 eye = frame.cameraPosition.xyz - center;
    float3 D = normalize(input.worldPosition - frame.cameraPosition.xyz);
    if ((uint(draw.params.z + 0.5) & 64u) != 0u)
        airLoad();
    if ((uint(draw.params.z + 0.5) & 64u) != 0u && gAir.x > 1.0)
    {
        eye /= globeScale();
        // The air past the planet's edge, ray-marched through the tables (Hillaire 2020). Over
        // the planet itself the surface draws its own aerial perspective, so nothing is added.
        float2 shell = airSphere(eye, D, gAir.x);
        if (shell.y <= max(shell.x, 0.0))
            discard;
        float2 ground = airSphere(eye, D, 1.0);
        if (ground.x <= ground.y && ground.x > 0.0)
            discard;
        float3 inscatter, through;
        airMarch(eye, D, max(shell.x, 0.0), shell.y, lightDirection(input.worldPosition), 24, inscatter, through);
        return float4(inscatter * frame.sunColor.rgb * AIR_PI, 1.0);
    }
    float rA = draw.params.x;
    float H = 0.02;
    float strength = 5.5 * draw.baseColor.a;
    float b = dot(eye, D);
    float cE = dot(eye, eye);
    float dA = b * b - (cE - rA * rA);
    if (dA < 0.0)
        discard;
    float t0 = max(0.0, -b - sqrt(dA));
    float t1 = -b + sqrt(dA);
    float dP = b * b - (cE - 1.0);
    bool hitP = false;
    float tp = 0.0;
    if (dP > 0.0)
    {
        tp = -b - sqrt(dP);
        if (tp > 0.0)
        {
            t1 = min(t1, tp);
            hitP = true;
        }
    }
    if (t1 <= t0)
        discard;
    if (hitP)
    {
        float3 nP = normalize(eye + D * tp);
        if (max(dot(nP, -D), 0.0) > 0.72)
            discard;
    }
    float3 L = lightDirection(input.worldPosition);
    float ds = (t1 - t0) / 8.0;
    float od = 0.0;
    float3 scat = float3(0.0, 0.0, 0.0);
    float3 beta = float3(0.24, 0.50, 1.0);
    for (int i = 0; i < 8; i++)
    {
        float3 x = eye + D * (t0 + (float(i) + 0.5) * ds);
        float r = length(x);
        float dens = exp(-max(r - 1.0, 0.0) / H);
        float sun = dot(x / r, L);
        float lit = smoothstep(-0.3, 0.35, sun);
        float3 warm = lerp(float3(1.0, 0.38, 0.12), float3(1.0, 1.0, 1.0), smoothstep(-0.02, 0.45, sun));
        od += dens * ds;
        scat += dens * ds * lit * warm * exp(-od * strength * 0.3 * beta);
    }
    float mu = dot(D, L);
    float phase = 0.75 * (1.0 + mu * mu) + 0.6 * pow(max(mu, 0.0), 12.0);
    float3 col = (1.0 - exp(-scat * strength * beta * phase)) * float3(0.8, 0.92, 1.0);
    float dmin = sqrt(max(cE - b * b, 0.0));
    float3 cp = eye + D * (-b);
    float halo = hitP ? 0.0 : exp(-(dmin - 1.0) / 0.035) * smoothstep(-0.3, 0.4, dot(normalize(cp), L));
    col += float3(0.25, 0.55, 1.0) * halo * 0.25;
    if (hitP)
    {
        float3 n = normalize(eye + D * tp);
        float graze = 1.0 - max(dot(n, -D), 0.0);
        col *= 0.6 * pow(graze, 5.0);
    }
    col *= draw.baseColor.rgb;
    return float4(heliosToScene(col), 1.0);
}

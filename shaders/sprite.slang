// Additive sprites: stars, markers and territory discs. One instance per
// sprite; the six corner vertices are generated from the vertex index.

#include "frame.slang"

struct SpriteInput
{
    [[vk::location(0)]] float4 positionSize;   // xyz = centre, w = radius in world units
    [[vk::location(1)]] float4 color;
    [[vk::location(2)]] float4 params;         // x = shape: 0 glow, 1 ring, 2 ground disc
    uint vertexId : SV_VertexID;
};

struct SpriteOutput
{
    float4 clipPosition : SV_Position;
    float2 local;        // -1..1 across the sprite
    float4 color;
    float shape;
    float3 world;        // 0.1.24: where on the sprite this is, for nebula and territory texture
    float time;          // frame time, passed on so the fragment stage needs no frame uniform
    float2 ecliptic;     // 0.1.25: the orbital plane's direction across the screen (sprite space)
};

static const float2 corners[6] = {
    float2(-1.0, -1.0), float2(1.0, -1.0), float2(1.0, 1.0),
    float2(-1.0, -1.0), float2(1.0, 1.0), float2(-1.0, 1.0)
};

[shader("vertex")]
SpriteOutput vertexMain(SpriteInput input)
{
    float2 corner = corners[input.vertexId % 6];
    float radius = input.positionSize.w;

    // Ground discs lie flat in the galactic plane; everything else faces the camera.
    float3 axisX = frame.cameraRight.xyz;
    float3 axisY = frame.cameraUp.xyz;
    if (input.params.x > 1.5)
    {
        axisX = float3(1.0, 0.0, 0.0);
        axisY = float3(0.0, 0.0, 1.0);
    }
    float3 world = input.positionSize.xyz + (axisX * corner.x + axisY * corner.y) * radius;

    SpriteOutput output;
    output.clipPosition = mul(frame.viewProjection, float4(world, 1.0));
    output.local = corner;
    output.color = input.color;
    output.shape = input.params.x;
    output.world = world;
    output.time = frame.misc.y;
    float3 toSprite = normalize(input.positionSize.xyz - frame.cameraPosition.xyz + float3(1e-6, 0.0, 0.0));
    float3 lineDir = cross(float3(0.0, 1.0, 0.0), toSprite);
    float2 ec = float2(dot(lineDir, axisX), dot(lineDir, axisY));
    output.ecliptic = length(ec) > 1e-4 ? normalize(ec) : float2(1.0, 0.0);
    return output;
}

// 0.1.24: smooth 3D value noise for nebulae and territory shimmer.
float spHash(float3 p) { p = frac(p * 0.3183099 + 0.1); p *= 17.0; return frac(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float spNoise(float3 x)
{
    float3 i = floor(x), f = frac(x);
    f = f * f * (3.0 - 2.0 * f);
    return lerp(lerp(lerp(spHash(i), spHash(i + float3(1, 0, 0)), f.x), lerp(spHash(i + float3(0, 1, 0)), spHash(i + float3(1, 1, 0)), f.x), f.y),
                lerp(lerp(spHash(i + float3(0, 0, 1)), spHash(i + float3(1, 0, 1)), f.x), lerp(spHash(i + float3(0, 1, 1)), spHash(i + float3(1, 1, 1)), f.x), f.y), f.z);
}
float spFbm(float3 x) { return spNoise(x) * 0.5 + spNoise(x * 2.03 + 7.1) * 0.27 + spNoise(x * 4.1 + 3.3) * 0.15 + spNoise(x * 8.3 + 1.7) * 0.08; }

[shader("fragment")]
float4 fragmentMain(SpriteOutput input) : SV_Target
{
    float r = length(input.local);
    float intensity;
    if (input.shape > 2.5 && input.shape < 3.5)
    {
        // Selection: four thin corner brackets, a square frame with its middles cut away.
        float2 a = abs(input.local);
        float edge = max(a.x, a.y);
        float line = smoothstep(0.075, 0.0, abs(edge - 0.86));
        float corner = step(0.48, min(a.x, a.y));
        intensity = line * corner;
        if (intensity < 0.001)
            discard;
        return float4(input.color.rgb * input.color.a * intensity, 1.0);
    }
    if (r > 1.0 && input.shape < 4.5)
        discard;
    if (input.shape > 4.5)
    {
        // Galaxy-map star, as a telescope sees one: a white-hot core, a halo in the star's
        // colour, and four faint diffraction spikes (a reflector's spider vanes).
        float2 p = input.local;
        float core = exp(-r * r * 40.0) * 3.0;
        float halo = exp(-r * r * 7.0) * 0.6 + pow(saturate(1.0 - r), 4.0) * 0.18;
        float spikeX = exp(-abs(p.y) * 160.0) * pow(1.0 - min(abs(p.x), 1.0), 3.0);
        float spikeY = exp(-abs(p.x) * 160.0) * pow(1.0 - min(abs(p.y), 1.0), 3.0);
        float spikes = (spikeX + spikeY) * 0.45;
        float3 c = float3(1.0, 1.0, 1.0) * core + input.color.rgb * (halo + spikes);
        return float4(c * input.color.a, 1.0);
    }
    if (input.shape < 0.5)
    {
        // Star: tight bright core with a faint halo.
        intensity = exp(-r * r * 14.0) * 2.2 + pow(1.0 - r, 3.0) * 0.35;
        // 0.1.24: glows that cover much of the screen (the galaxy's arms and clouds) turn into
        // nebulae: wisps and dark lanes in the sprite's colour, drifting very slowly.
        float px = 2.0 / max(fwidth(input.local.x), 1e-5);   // sprite size on screen, pixels
        float neb = smoothstep(160.0, 420.0, px);
        if (neb > 0.0)
        {
            float3 q = float3(input.local * 2.2, 0.0) + input.world * 0.002 + float3(0.0, 0.0, input.time * 0.004);
            float w = spFbm(q + spFbm(q * 0.7) * 1.6);
            float lanes = smoothstep(0.30, 0.55, spFbm(q * 1.7 + 11.0));
            float wisp = (0.35 + 1.3 * smoothstep(0.35, 0.8, w)) * lerp(0.55, 1.0, lanes);
            intensity = lerp(intensity, intensity * wisp, neb);
            float3 hue = lerp(input.color.rgb, input.color.rgb * float3(0.85, 0.75, 1.25), smoothstep(0.5, 0.8, w));
            return float4(hue * input.color.a * intensity, 1.0);
        }
    }
    else if (input.shape < 1.5)
    {
        // Marker ring: thin.
        intensity = smoothstep(0.06, 0.0, abs(r - 0.84));
    }
    else if (input.shape < 2.5)
    {
        // Territory: flat fill that fades out at the rim; 0.1.24: a brighter rim and a slow shimmer.
        float shimmer = 0.85 + 0.3 * spNoise(float3(input.local * 3.0, input.time * 0.12) + input.world * 0.01);
        intensity = smoothstep(1.0, 0.6, r) * shimmer + exp(-pow((r - 0.78) / 0.07, 2.0)) * 0.35;
    }
    else
    {
        // Sun (Project Helios): a limb-darkened disc, a warm glow and faint rays.
        float disc0 = 0.22;
        float a = atan2(input.local.y, input.local.x);
        float disc = smoothstep(disc0, disc0 * 0.94, r);
        float mu = sqrt(max(1.0 - (r * r) / (disc0 * disc0), 0.0));
        float3 core = float3(1.0, 0.97, 0.9) * (0.55 + 0.45 * mu) * 3.0;
        float glow = exp(-(r - disc0) * 9.0) * 0.55 + exp(-r * 3.2) * 0.35;
        float rays = pow(abs(cos(a * 3.0 + 0.4)), 60.0) + pow(abs(cos(a * 3.0 + 1.45)), 60.0) * 0.6;
        glow += rays * exp(-r * 4.0) * 0.25;
        float3 c = core * disc * input.color.rgb + input.color.rgb * float3(1.0, 0.86, 0.62) * glow * (1.0 - disc);
        // 0.1.25: a lens streak, a faint halo ring, and the zodiacal light along the planets' plane.
        float2 lp = input.local;
        float streak = exp(-abs(lp.y) * 55.0) * exp(-abs(lp.x) * 2.2) * 0.35;
        float ring = exp(-pow((r - 0.62) / 0.025, 2.0)) * 0.05;
        float3 ringC = lerp(float3(1.0, 0.6, 0.4), float3(0.5, 0.7, 1.0), saturate((r - 0.6) * 25.0 + 0.5));
        float along = dot(lp, input.ecliptic), across = dot(lp, float2(-input.ecliptic.y, input.ecliptic.x));
        float zodi = exp(-pow(across / (0.05 + 0.10 * abs(along)), 2.0)) * exp(-abs(along) * 2.5) * smoothstep(0.2, 0.35, r) * 0.18;
        c += input.color.rgb * (float3(1.0, 0.9, 0.75) * streak + ringC * ring + float3(1.0, 0.92, 0.8) * zodi);
        float edgeFade = 1.0 - smoothstep(0.85, 1.0, r);
        return float4(c * edgeFade * input.color.a, 1.0);
    }
    return float4(input.color.rgb * input.color.a * intensity, 1.0);
}

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
    return output;
}

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
    }
    else if (input.shape < 1.5)
    {
        // Marker ring: thin.
        intensity = smoothstep(0.06, 0.0, abs(r - 0.84));
    }
    else if (input.shape < 2.5)
    {
        // Territory: flat fill that fades out at the rim.
        intensity = smoothstep(1.0, 0.6, r);
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
        float edgeFade = 1.0 - smoothstep(0.85, 1.0, r);
        return float4(c * edgeFade * input.color.a, 1.0);
    }
    return float4(input.color.rgb * input.color.a * intensity, 1.0);
}

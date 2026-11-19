// Physically based bloom (Jorge Jimenez, "Next Generation Post Processing in Call of Duty:
// Advanced Warfare", SIGGRAPH 2014; as in LearnOpenGL's "Phys. Based Bloom"). The HDR image is
// halved again and again with a 13-tap filter (a Karis average on the first step keeps single
// bright pixels from flickering), then each level is blurred back up with a 3x3 tent and added to
// the one above. No threshold: everything blooms in proportion to its brightness, so only the
// truly bright (sun glints, city lights, the sun) visibly glow.

[[vk::binding(0, 0)]] Sampler2D source;

struct BloomData
{
    float4 params; // xy = source texel size, z = 1 on the first step (Karis average), w = tent radius (uv)
};
[[vk::push_constant]] ConstantBuffer<BloomData> bloom;

struct PostOutput
{
    float4 clipPosition : SV_Position;
    float2 uv;
};

float luma(float3 c) { return dot(c, float3(0.2126, 0.7152, 0.0722)); }
float3 karis(float3 c) { return c / (1.0 + luma(c)); }

[shader("fragment")]
float4 fragmentDown(PostOutput input) : SV_Target
{
    float2 t = bloom.params.xy;
    float2 uv = input.uv;
    float3 a = source.SampleLevel(uv + t * float2(-2, -2), 0.0).rgb;
    float3 b = source.SampleLevel(uv + t * float2(0, -2), 0.0).rgb;
    float3 c = source.SampleLevel(uv + t * float2(2, -2), 0.0).rgb;
    float3 d = source.SampleLevel(uv + t * float2(-2, 0), 0.0).rgb;
    float3 e = source.SampleLevel(uv, 0.0).rgb;
    float3 f = source.SampleLevel(uv + t * float2(2, 0), 0.0).rgb;
    float3 g = source.SampleLevel(uv + t * float2(-2, 2), 0.0).rgb;
    float3 h = source.SampleLevel(uv + t * float2(0, 2), 0.0).rgb;
    float3 i = source.SampleLevel(uv + t * float2(2, 2), 0.0).rgb;
    float3 j = source.SampleLevel(uv + t * float2(-1, -1), 0.0).rgb;
    float3 k = source.SampleLevel(uv + t * float2(1, -1), 0.0).rgb;
    float3 l = source.SampleLevel(uv + t * float2(-1, 1), 0.0).rgb;
    float3 m = source.SampleLevel(uv + t * float2(1, 1), 0.0).rgb;
    float3 result;
    if (bloom.params.z > 0.5)
    {
        // Five boxes, each weighted by its Karis average.
        float3 g0 = (a + b + d + e) * 0.25, g1 = (b + c + e + f) * 0.25, g2 = (d + e + g + h) * 0.25, g3 = (e + f + h + i) * 0.25;
        float3 g4 = (j + k + l + m) * 0.25;
        float w0 = 1.0 / (1.0 + luma(g0)), w1 = 1.0 / (1.0 + luma(g1)), w2 = 1.0 / (1.0 + luma(g2)), w3 = 1.0 / (1.0 + luma(g3));
        float w4 = 1.0 / (1.0 + luma(g4));
        result = (g0 * w0 * 0.125 + g1 * w1 * 0.125 + g2 * w2 * 0.125 + g3 * w3 * 0.125 + g4 * w4 * 0.5) /
                 (w0 * 0.125 + w1 * 0.125 + w2 * 0.125 + w3 * 0.125 + w4 * 0.5);
    }
    else
    {
        result = e * 0.125 + (a + c + g + i) * 0.03125 + (b + d + f + h) * 0.0625 + (j + k + l + m) * 0.125;
    }
    return float4(max(result, float3(0.0, 0.0, 0.0)), 1.0);
}

[shader("fragment")]
float4 fragmentUp(PostOutput input) : SV_Target
{
    float r = bloom.params.w;
    float2 uv = input.uv;
    float3 s = source.SampleLevel(uv, 0.0).rgb * 4.0;
    s += (source.SampleLevel(uv + float2(-r, 0), 0.0).rgb + source.SampleLevel(uv + float2(r, 0), 0.0).rgb +
          source.SampleLevel(uv + float2(0, -r), 0.0).rgb + source.SampleLevel(uv + float2(0, r), 0.0).rgb) * 2.0;
    s += source.SampleLevel(uv + float2(-r, -r), 0.0).rgb + source.SampleLevel(uv + float2(r, -r), 0.0).rgb +
         source.SampleLevel(uv + float2(-r, r), 0.0).rgb + source.SampleLevel(uv + float2(r, r), 0.0).rgb;
    return float4(s / 16.0, 1.0);
}

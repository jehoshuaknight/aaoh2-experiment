// Post-processing: the scene's HDR colour goes in, a displayable image comes
// out. Currently exposure, tone mapping, vignette and gamma encoding. Further
// effects are added as stages between the HDR target and this final pass.

[[vk::binding(0, 0)]] Sampler2D sceneColor;
// The bloom chain's top level (bloom.slang), the sum of every level.
[[vk::binding(0, 1)]] Sampler2D bloomColor;

struct PostData
{
    float4 params;   // x = exposure, y = vignette strength, z = 1 to gamma-encode, w = bloom strength
    float4 more;     // x = 1 / number of bloom levels
};
[[vk::push_constant]] ConstantBuffer<PostData> post;

struct PostOutput
{
    float4 clipPosition : SV_Position;
    float2 uv;
};

// One triangle that covers the whole screen.
[shader("vertex")]
PostOutput vertexMain(uint vertexId : SV_VertexID)
{
    PostOutput output;
    output.uv = float2((vertexId << 1) & 2, vertexId & 2);
    output.clipPosition = float4(output.uv * 2.0 - 1.0, 0.0, 1.0);
    return output;
}

// ACES filmic curve, Narkowicz fit.
float3 toneMap(float3 x)
{
    return saturate((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14));
}

[shader("fragment")]
float4 fragmentMain(PostOutput input) : SV_Target
{
    float3 hdr = sceneColor.Sample(input.uv).rgb;
    // Bloom: a camera's soft glow around everything bright, blended in (no threshold).
    float3 glow = bloomColor.Sample(input.uv).rgb * post.more.x;
    float3 color = lerp(hdr, glow, post.params.w) * post.params.x;
    color = toneMap(color);

    // Colour grade (0.1.5): a gentle filmic S-curve, cool shadows and warm highlights (split
    // toning), a touch more saturation in the mids. Mild on purpose: the map must keep its colours.
    float lum = dot(color, float3(0.2126, 0.7152, 0.0722));
    color = lerp(color, color * color * (3.0 - 2.0 * color), 0.18);
    float3 shadows = float3(0.97, 0.99, 1.04);
    float3 highs = float3(1.035, 1.0, 0.955);
    color *= lerp(shadows, highs, smoothstep(0.15, 0.85, lum));
    float l2 = dot(color, float3(0.2126, 0.7152, 0.0722));
    color = lerp(float3(l2, l2, l2), color, 1.0 + 0.08 * (1.0 - abs(l2 * 2.0 - 1.0)));
    color = saturate(color);

    float2 centered = input.uv * 2.0 - 1.0;
    color *= 1.0 - post.params.y * dot(centered, centered) * 0.5;

    if (post.params.z > 0.5)
        color = pow(color, float3(1.0 / 2.2));
    // Fine dither (one display step): removes banding in the dark sky and soft glows.
    float n = frac(sin(dot(input.clipPosition.xy, float2(12.9898, 78.233))) * 43758.5453);
    color += (n - 0.5) / 255.0;
    return float4(color, 1.0);
}

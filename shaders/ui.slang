// Interface overlay: flat and textured rectangles in pixel coordinates, drawn
// over the finished image. One instance per rectangle; the six corner
// vertices are generated from the vertex index.

[[vk::binding(0, 0)]] Sampler2D atlas;

struct UiData
{
    float4 screen;   // x, y = target size in pixels; z = 1 if the target stores linear colour
};
[[vk::push_constant]] ConstantBuffer<UiData> ui;

struct UiInput
{
    [[vk::location(0)]] float4 rect;     // x, y = top-left corner in pixels; z, w = size
    [[vk::location(1)]] float4 uv;       // u0, v0, u1, v1 in the atlas
    [[vk::location(2)]] float4 color;    // as seen on screen (sRGB), alpha = opacity
    [[vk::location(3)]] float4 params;   // x = 1 to multiply by the atlas alpha, y = rotation (radians) about the centre
    uint vertexId : SV_VertexID;
};

struct UiOutput
{
    float4 clipPosition : SV_Position;
    float2 uv;
    float4 color;
    float textured;
};

static const float2 corners[6] = {
    float2(0.0, 0.0), float2(1.0, 0.0), float2(1.0, 1.0),
    float2(0.0, 0.0), float2(1.0, 1.0), float2(0.0, 1.0)
};

[shader("vertex")]
UiOutput vertexMain(UiInput input)
{
    float2 corner = corners[input.vertexId % 6];
    float2 pixel = input.rect.xy + corner * input.rect.zw;
    if (input.params.y != 0.0 || input.params.z != 0.0)
    {
        // Map lettering: sheared, then turned about the rectangle's centre, so a letter can
        // lie on a surface seen at an angle.
        float2 c = input.rect.xy + input.rect.zw * 0.5;
        float2 o = pixel - c;
        o.x += input.params.z * o.y;
        float cs = cos(input.params.y), sn = sin(input.params.y);
        pixel = c + float2(cs * o.x - sn * o.y, sn * o.x + cs * o.y);
    }

    UiOutput output;
    // Pixel (0,0) is the top-left corner; Vulkan clip space has y pointing down too.
    output.clipPosition = float4(pixel / ui.screen.xy * 2.0 - 1.0, 0.0, 1.0);
    output.uv = lerp(input.uv.xy, input.uv.zw, corner);
    output.color = input.color;
    output.textured = input.params.x;
    return output;
}

[shader("fragment")]
float4 fragmentMain(UiOutput input) : SV_Target
{
    float4 color = input.color;
    if (input.textured > 0.5)
        color.a *= atlas.Sample(input.uv).a;
    if (ui.screen.z > 0.5)
        color.rgb = pow(color.rgb, float3(2.2));
    return color;
}

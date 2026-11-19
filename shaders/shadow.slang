// Depth-only pass from the sun's point of view. No fragment shader is needed.

struct ShadowDraw
{
    float4x4 lightModelViewProjection;
};
[[vk::push_constant]] ConstantBuffer<ShadowDraw> draw;

[shader("vertex")]
float4 vertexMain([[vk::location(0)]] float3 position) : SV_Position
{
    return mul(draw.lightModelViewProjection, float4(position, 1.0));
}

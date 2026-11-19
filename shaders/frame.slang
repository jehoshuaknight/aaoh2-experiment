// Per-frame data shared by every shader. Must match FrameUniforms in
// engine/presentation/render/src/renderer.cpp.
//
// Shaders are compiled with -matrix-layout-column-major, so matrices arrive
// exactly as glm stores them and mul(M, v) means M * v.

struct FrameData
{
    float4x4 view;
    float4x4 projection;
    float4x4 viewProjection;
    float4x4 lightViewProjection;
    float4 cameraPosition;
    float4 cameraRight;
    float4 cameraUp;
    float4 sunDirection;   // xyz = direction the light travels, w = 1 if shadows are enabled
    float4 sunColor;       // rgb, already multiplied by intensity
    float4 ambient;
    float4 atmosphere;     // rgb, w = strength
    float4 misc;           // x = shadow map texel size, y = time in seconds, z = map style (0 realistic, 1 Strategic, 2 Satellite Night, 3 Holo Table)
    float4 strikes[4];     // planet surfaces: xyz = unit direction of an impact or launch flash, w = seconds since (< 0 = none)
    float4 strikeInfo;     // x = angular size of a strike (radians), y = alert pulse 0..1
    float4 air;            // x = radius of the top of the air (planet radius 1; 0 = none), y = density, z = haze
    float4 airTint;        // rgb = the Rayleigh colours' multipliers
};

[[vk::binding(0, 0)]] ConstantBuffer<FrameData> frame;

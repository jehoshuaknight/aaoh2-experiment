# Province and region borders (0.1.4)

## What other games do

- **Hearts of Iron IV**: provinces are painted as unique RGB colours in `provinces.bmp`, with IDs in `definition.csv`. States and strategic regions group them. Borders form a hierarchy of plain lines: a hairline for provinces, thicker for states, bold for countries, all fading with zoom.
- **Stellaris**: borders are light, not ink. Each empire's area is filled with its colour, brightest at the edge and fading inward, with a glowing rim. Neighbours meet as two coloured bands.
- **EU4 / Victoria 3 (Jomini)**: a painted political map at zoom-out, and terrain with thin lines and shader effects at zoom-in. Victoria 3's graphics dev diary covers borders, shorelines and fog drawn in shaders.

## What Astra Novum does now

All of it is in `shaders/mesh.slang` (compiled to `bin/game/shaders/mesh.lit.frag.spv`). The engine and the province maps are unchanged.

| Layer | Look |
|---|---|
| Province | HOI4 hairline that fades out from orbit, plus a faint light along its edge up close. |
| Region | Bold dark ink line (HOI4). On each side, a band of the region's own vivid colour fades inward over 3 to 10 texels depending on zoom, with a bright rim against the ink (Stellaris). |
| Region fill | Each region takes a light tint of its own colour, so the region map reads as a political map. |
| Frontier and coast | As before (heaviest line). |
| Night | The bands glow faintly in the dark. |
| Strategic / Holo Table | Region edges glow in the style's line colour mixed with the region's colour, with a slow shimmer from orbit. |

The glow uses a 16-tap golden-angle spiral over the province data texture, which wraps around in longitude. It costs 16 texture loads per land pixel, with no new textures, bindings or engine changes.

## Building

```
g++ -std=c++17 -I<slang include> tools/slangc/slangc.cpp -L<slang lib> -lslang-compiler -o slangc
slangc shaders/mesh.slang fragmentLit bin/game/shaders/mesh.lit.frag.spv shaders
```
The Slang library comes from the `slangpy` wheel on PyPI (2026.12). The rebuilt unmodified shaders match the shipped ones: the vertex shader is byte-identical and the fragment shaders have the same bindings.

`tools/preview_borders.py` renders a CPU approximation (old vs new, Realistic and Strategic) from the real province maps.

## Not done (needs the engine source)

- Region and country labels that follow the shape of each region (Paradox style).
- A painted paper map at full zoom-out.
- Border distance fields baked on the CPU. A Rust baker would make the glow wider and cheaper, but the engine has to load and bind the texture.

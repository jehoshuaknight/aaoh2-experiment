# 0.1.5: quality pass

| Change | Where |
|---|---|
| **Sea in the map styles**: a continental shelf from nearby land, nautical-chart depth contours, slow wave texture and light along the coasts (Strategic, Satellite Night, Holo Table). | `shaders/mesh.slang` → `mesh.lit.frag.spv` |
| **Map hill shading**: relief lit from the north-west, as cartographers do, so mountains read in every style. | same |
| **Colour grade**: a gentle filmic S-curve, cool shadows and warm highlights, a little more mid-tone saturation, and a one-step dither against banding. | `shaders/post.slang` → `post.frag.spv` |
| **4K planet maps by default** (Earth day, Earth night lights, terraformed Mars): about 75 % less graphics memory for those maps. The 8K originals are in `AstraNovum-HD-Textures-0.1.5.zip`. | `bin/game/textures/bodies` |
| **Province facts** (Rust): area, centre, coastline, relief, terrain class, river share, night lights, ecology, a 2240 climate class and every neighbour with its shared border length, for Earth's 480 and Mars's 200 provinces. Baked in about 0.5 s. | `rust/province_facts` → `data/<body>/province_facts.tsv` |

Shader bindings are unchanged; the post shader also reads the pixel position (a built-in, not a resource).

## Not possible without the engine source
- **City glow on clouds at night**: the cloud pass has no access to the city-lights map.
- **Mars cities and night lights**: the engine reads only `data/earth/cities.tsv`, and Mars's lights are generated inside the engine.
- **Province facts in gameplay**: the TSVs are ready, but the engine does not read them yet.

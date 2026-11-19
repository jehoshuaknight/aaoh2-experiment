# 0.1.6: solar system HD pass

## Maps (17 bodies)
| Body | Before | Now | Source |
|---|---|---|---|
| Mercury, Moon, Venus, Venus clouds | 1024 | 4096 | Solar System Scope (MESSENGER, LRO, Magellan); CC BY 4.0 |
| Jupiter, Saturn | 2048 (painted) | 4096 | Solar System Scope (Cassini); CC BY 4.0 |
| Io, Europa, Ganymede, Callisto | 1024 | 4096 | USGS Galileo/Voyager mosaics |
| Enceladus, Titan, Triton, Pluto, Charon, Ceres, Phobos | 512 to 1024 | 2048 | USGS Cassini, Voyager 2, New Horizons, Dawn, Mars Express mosaics |
| Uranus, Neptune, Deimos | unchanged | | no better public map exists (Uranus and Neptune are nearly featureless in real imagery) |

Checks:
- Every mosaic was compared with the game's earlier map.
- Europa, Ganymede and Callisto came in a 0 to 360 layout and were shifted 180 degrees. This was found by cross-correlation, with clear peaks (12 to 16).
- Solar System Scope's Venus is upside down; it is rotated 180 degrees, as checked against Maxwell Montes and the old Magellan map.
- The Moon was checked by Tycho's position.
- Gaps a probe never imaged are filled from the earlier map with feathered seams.

## Shader effects (`shaders/mesh.slang`, plain globes in the system view)
- **Gas giants**: bands sway east and west at alternating jet speeds. The sway oscillates, so the map never smears. The clouds boil slowly, the limb darkens, and a sunlit haze rim takes the planet's own colour.
- **Hazy worlds** (bodies with air: Venus, Titan): the same haze rim.
- **Airless bodies**: a crater and ridge bump from the map's own shading, strongest at the terminator.
- **Ice** (bright, pale ground: Europa, Enceladus, Triton): a sun glint and a cold rim sheen.
- **Io**: small dark paterae on sulphur-yellow ground glow red-orange and flicker, strongest on the night side.
- **Sun**: boiling granulation and supergranulation, sunspots with penumbrae, and faculae toward the limb. Glare comes from the existing bloom.

Detection is by shape and colour, since the shader has no body id:
- A plain globe is a mesh whose normal points from its centre.
- Gas giants are found by the map's bandedness: colour changes north-south far more than east-west.
- Io is found by sulphur-yellow surroundings plus spots darker than their surroundings.

## Needs the engine source
- Saturn's rings: the engine has no ring geometry.
- A corona drawn beyond the Sun's disc.
- Asteroid belt particles.

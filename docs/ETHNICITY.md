# Ethnicity in 2240: data and gameplay spec

The 0.1.2 build ships the ethnicity **data**. The current `astra_client.exe` does not read it yet.
The map mode and the effects below have to be added in the engine source (`engine/`), which is not in this repository.

## Files (in `bin/game/`)

| File | What |
|---|---|
| `data/ethnicity/groups.tsv` | 160 groups: key, name, language family, map colour, bodies (Earth/Mars), homeland and 2240 notes. 153 on Earth, 7 Martian-born, 11 Earth groups also present on Mars. |
| `data/earth/ethnicity.tsv` | For each of Earth's 480 provinces: `group:percent;...` (top groups, the remainder is `other`). |
| `data/mars/ethnicity.tsv` | The same for Mars's 200 provinces. |
| `textures/bodies/Earth_ethnicity.png`, `Mars_ethnicity.png` | 2048 x 1024 equirectangular maps, drawn like the ecology map: no borders, soft blends, brighter where more people live. |

The files are built by `tools/build_ethnicity.py` (group placements in `tools/groups.py`). To change a group, edit its seeds and rebuild.
The Siberian lights and cities come from `tools/siberia_lights.py`.

## How the 2240 projection was made

- Real groups sit at their real homelands; there is no real ethnic dataset in it (the GREG/Atlas Narodov Mira files could not be downloaded), so placements are hand-made and approximate.
- 2240 changes: the +70 m sea removes drowned populations (Bengal delta, West Siberian lowland, Gulf coasts, Netherlands polders); a 3 C warmer climate pulls people north. Siberia gains Central Asian, Chinese and Korean communities and a new hybrid group, the **Sibiryaks**. Canada's thawed north gets the **Reachers**, Antarctica the **Austral settlers**, and ice-free Greenland Scandinavian settlers. Maghrebi communities grow in southern Europe.
- Mars: seven Martian-born identities (Tharsians, Mariners, Arabians, Hellasians, Elysians, Boreal coasters, Southern highlanders) dominate after 54 years of war-time nationalism. Earth-origin minorities remain from the settlement waves (Han, Hindustani, Anglo-American, Russian, Japanese, Korean, Brazilian, Yoruba, Levantine, German, Mexican).

## Engine work needed

### Map mode
- New overlay `Ethnicity [T]` next to `Ecology [E]`, using `<Body>_ethnicity.png` the way the ecology overlay uses `Earth_ecology.png` (but as a plain colour texture, not a data texture).
- Province tooltip: top 3 groups with percentages and colour swatches.
- `view.planet_ethnicity = false` config key, like `view.planet_ecology`.

### Effects (chosen: unrest/approval, faction relations, growth and assimilation)

Per province, read the mix into `shares[group]` (sum 1).

1. **Diversity and approval**
   - `fractionalisation = 1 - sum(share^2)`.
   - Every faction gets a `core_groups` list in `campaign_2240.toml` (Terran Union: none, as it is a pan-human federation; Martian Sovereignty: the `m_*` groups).
   - `alienation = 1 - sum(shares[g] for g in owner.core_groups)` (0 for the Terran Union).
   - Approval modifier: `-12 % * alienation - 4 % * fractionalisation`.
   - If one non-core group holds 40 % or more and approval is under 35 %, the chance of the existing *independence movement* event goes up by `+50 % * share`.

2. **Faction relations**
   - For each pair of factions A and B, `kinship = sum over groups of min(popshare_A[g], popshare_B[g])`, with populations summed over the provinces each controls.
   - Relation drift: `+8 * kinship` per year towards friendship, capped at +20.
   - A group that is 10 % or more of a province of A and the core group of B gives B a casus belli / "protect our people" diplomatic option.

3. **Growth and assimilation** (monthly tick)
   - Each group has `growth` (from its region's demography: about 0.5 % a year for East Asia and Europe, up to 2 % for the Sahel) and `assimilation_target` (the province's largest group, or the owner's core group if it holds 25 % or more).
   - Each year `0.3 % * development * (1 - fractionalisation)` of every minority shifts to the target; the shift doubles in cities over 1 M people.
   - Renormalise the shares, and save them in the save file (the shares in `ethnicity.tsv` are only the 2240 start).

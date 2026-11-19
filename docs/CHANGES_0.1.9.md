# 0.1.9: information on every people, ethnicity one key-press away

## Ethnicity on F6, first in the cycle
Press **F6** once from the normal view to get the ethnicity map: Realistic → **Peoples of 2240** → Strategic → Holo Table. **E** stays Ecology. The game has no spare key, because keys are wired inside the `.exe`.

How it was done:
- In `astra_client.exe`, the order of the style labels was swapped. Two string pointers and their lengths in the label code changed (`0x14017b0f6`, `0x14017b105`, `0x14017b128`, `0x14017b136`), and the two entries of the style-name table at `0x140705f08` and `0x140705f10` were swapped. No logic changed.
- In the shader, `mapStyle()` swaps the looks of the engine's styles 1 and 2 to match, for the surface and both cloud passes.

## Information on every people
`bin/game/data/ethnicity/peoples_info.tsv` has a row for each of the 359 peoples. Each row gives:
- name, family and map colour
- **parent cultures** (fusion peoples)
- **language**
- **faith**
- **estimated 2240 population**
- number of provinces
- **three strongholds**
- history

How the population is estimated: each province's people (Earth 8.6 billion, Mars 410 million, from the campaign) are spread 60 % by the game's city list (real populations) and 40 % by night lights above the background glow, then split by the province's ethnic mix. The largest peoples come out as Anglo-Americans (about 0.96 bn), Northern Han (0.46 bn), Brazilians, Hindustanis and Mexicans.

The game cannot show this text yet: its info panels are in the engine. The atlas shows all of it: click a people for its card. The list is sorted by population and can be searched by language.

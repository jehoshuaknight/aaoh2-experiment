"""Narrative descriptions of every people of 2240 ("The people of ... are ..."), built from the data:
homeland, language, faith, population, strongholds, language-family history, what the +70 m sea and the
3 C warming did to their lands, and for fusion peoples the two cultures that met to make them."""
import hashlib
import re

# One or two sentences of deep history per language family (real history, kept general).
FAMILY_PAST = {
 'Slavic': 'Their ancestors were among the Slavic peoples who spread across eastern and central Europe in the early Middle Ages and later built kingdoms, empires and, in the twentieth century, nations of their own.',
 'Germanic': 'They descend from the Germanic-speaking peoples of northern Europe, whose languages and laws shaped much of the modern West.',
 'Celtic': 'They are heirs of the Celtic peoples who once held most of western Europe and who held on longest at its Atlantic edge.',
 'Romance': 'Their language grew out of the Latin of the Roman Empire, carried by soldiers, settlers and later by the Church.',
 'Finnic': 'Their Finnic tongue came west with Uralic-speaking hunters and farmers thousands of years ago and survived among the forests and lakes of the north.',
 'Baltic': 'Their Baltic language is one of the oldest living branches of the Indo-European family, kept alive through centuries of rule by stronger neighbours.',
 'Ugric': 'Their ancestors rode west from the Urals in the ninth century and settled the Carpathian basin for good.',
 'Uralic': 'They belong to the Uralic peoples of the northern forests and tundra, among the oldest inhabitants of their lands.',
 'Hellenic': 'Their language has been written for more than three thousand years, longer than almost any other on Earth.',
 'Albanian': 'Their language forms a branch of the Indo-European family all of its own, older than the borders drawn around it.',
 'Kartvelian': 'Their Kartvelian language and alphabet are unique to the Caucasus, and their kingdom was among the first to adopt Christianity.',
 'Armenian': 'Their nation is one of the oldest in the world: the first to make Christianity a state faith, scattered by catastrophe and never dissolved.',
 'Caucasian': 'They are an ancient mountain people of the Caucasus, whose many languages are found nowhere else on Earth.',
 'Turkic': 'Their Turkic forebears rode out of the steppes of Inner Asia over a thousand years ago and founded khanates and empires from China to the Danube.',
 'Iranian': 'Their Iranian language links them to the old empires of Persia and to the horse peoples of the ancient steppe.',
 'Semitic': 'Their Semitic language belongs to the family of Akkadian, Hebrew and Arabic, among the oldest written traditions in the world.',
 'Berber': 'They are the indigenous people of North Africa, older on their land than every empire that came to rule it.',
 'Mongolic': 'Their ancestors once rode with the largest land empire in history, and the steppe still shapes their way of life.',
 'Tungusic': 'They come from the Tungusic peoples of the far north-east, reindeer herders, hunters and, once, the founders of China\'s last dynasty.',
 'Chukotko-Kamchatkan': 'They are reindeer herders and sea hunters of the far north-east, the last people of Asia before America.',
 'Indo-Aryan': 'Their language descends from the Sanskrit of ancient India, through the many tongues of the medieval kingdoms.',
 'Dravidian': 'Their Dravidian language is older in India than the Indo-Aryan ones, with a literature reaching back two thousand years.',
 'Austroasiatic': 'They speak an Austroasiatic language, the tongue of the first rice farmers of mainland Southeast Asia.',
 'Austroasiatic/Dravidian': 'They are among the oldest peoples of India, keeping their own gods, councils and forests through every empire.',
 'Indo-Aryan/Tibeto-Burman': 'Their valley has been a meeting place of Indian and Himalayan peoples for thousands of years.',
 'Sinitic': 'They belong to the Han Chinese, whose written language and civilisation run unbroken for more than three thousand years.',
 'Tibeto-Burman': 'Their Tibeto-Burman language ties them to the peoples of the Himalaya and the high hills that run south into Burma.',
 'Tai': 'They are a Tai-speaking people, rice farmers of the valleys who spread south from southern China a thousand years ago.',
 'Hmong-Mien': 'They are a Hmong-Mien people of the southern Chinese mountains, long known for their embroidery, silver and independence.',
 'Koreanic': 'Their Korean nation has lived on the same peninsula, with its own language and alphabet, for well over a thousand years.',
 'Japonic': 'Their islands kept their own language, emperors and culture through the long centuries of East Asian history.',
 'Austronesian': 'They belong to the Austronesian seafarers who sailed out of Taiwan five thousand years ago and settled half the world\'s oceans.',
 'Austronesian/Austroasiatic': 'They are the highland peoples of Indochina, who kept their longhouses and lands while the lowland kingdoms rose and fell.',
 'Papuan': 'Their ancestors reached New Guinea more than forty thousand years ago and became some of the world\'s first farmers.',
 'Pama-Nyungan': 'They are part of the oldest continuous culture on Earth, more than fifty thousand years on the Australian continent.',
 'Polynesian': 'Their ancestors were the Polynesian navigators who found every island of the Pacific with stars, swells and memory.',
 'Chadic': 'They are a Chadic people of the Sahel, long-distance traders whose language became the common tongue of West Africa\'s interior.',
 'Atlantic': 'They are an Atlantic people of West Africa, herders, farmers and traders of the savannah and the coast.',
 'Saharan': 'They are a Saharan people, heirs of the trans-desert caravan kingdoms around Lake Chad.',
 'Volta-Niger': 'Their forebears built the forest kingdoms and city-states of the lower Niger, famous for bronze, trade and art.',
 'Benue-Congo': 'They belong to the Benue-Congo peoples of Nigeria\'s Middle Belt and Cross River, the cradle from which the Bantu once set out.',
 'Kwa': 'They are a Kwa people of the West African forest, heirs of kingdoms built on gold, kola and trade.',
 'Mande': 'They descend from the Mande of the old Mali Empire, whose griots still keep its history in song.',
 'Gur': 'They are a Gur-speaking people of the West African savannah, farmers whose chiefdoms resisted the great empires around them.',
 'Bantu': 'They are part of the great Bantu migration that carried farming and iron across central and southern Africa over three thousand years.',
 'Bantoid': 'They are a Grassfields people of western Cameroon, organised in chiefdoms famous for their masks and markets.',
 'Nilotic': 'They are a Nilotic people, cattle herders of the Nile and the Rift, tall, proud and stubborn about their land.',
 'Nilo-Saharan': 'They are a Nilo-Saharan people of the dry lands between the Nile and Lake Chad.',
 'Nilo-Saharan/Kordofanian': 'They are the mountain peoples of Kordofan, more than a hundred communities on a few ranges of hills.',
 'Cushitic': 'They are a Cushitic people of the Horn of Africa, herders and traders on one of the oldest routes between Africa and Arabia.',
 'Semitic/Cushitic/Omotic': 'They are the peoples of the southern Ethiopian highlands, farmers of ensete and coffee on some of Africa\'s richest soil.',
 'Ubangian': 'They are the peoples of the Ubangi savannah, whose kingdoms long stood between the Sahel and the forest.',
 'Khoe/Bantu': 'Among them are the descendants of the Khoe and San, the oldest peoples of southern Africa, and of the Herero cattle nations.',
 'Songhai': 'They are heirs of the Songhai Empire, which once ruled the Niger bend from Gao and Timbuktu.',
 'Dogon': 'They are the Dogon of the Bandiagara cliffs, famous for their villages, masks and astronomy.',
 'Ijoid': 'They are the people of the Niger Delta creeks, fishers and traders of a maze of water.',
 'Central Sudanic': 'They are a Central Sudanic people of the Uele, once known across Africa for their court art.',
 'Mande/Kru': 'They are the forest peoples of the Liberian and Ivorian hills, keepers of masks and secret societies.',
 'Mande/Atlantic': 'They are the peoples of the Guinea highlands and coast, where the Mande world meets the Atlantic.',
 'Nilotic/Cushitic': 'They are a pastoral people of the Horn.',
 'Afro-American': 'They descend from Africans carried across the Atlantic in slavery, who made new peoples, faiths and music in the Americas.',
 'Afro-Indigenous': 'They were born where escaped Africans met the native peoples of the Caribbean coast.',
 'Indigenous American': 'Their ancestors were in the Americas thousands of years before Europeans arrived, and their nations survived conquest, disease and assimilation.',
 'Eskimo-Aleut': 'They are the Arctic people who mastered the ice, hunting seal and whale from Greenland to Alaska.',
 'Mixed': 'They are a people of many origins, made by trade, plantations and migration.',
 'Basque': 'Their language is older than any other in western Europe and related to none of them, a survivor from before the Indo-Europeans came.',
 'Ainu': 'They are the indigenous people of Japan\'s north, who held Hokkaido long before the Japanese state reached it.',
 'Isolate': 'Their language is related to no other on Earth, a survivor in the high valleys of the Karakoram.',
}

# What 2240 did, by where a people lives (first match wins).
def hook(lat, lon, key, fam):
    if fam == 'Martian':
        return None
    if lat > 50 and 55 < lon < 180:
        return 'The warming of the twenty-second century turned their Siberian land from frontier into farmland and boom towns, and newcomers from Central Asia, China and Korea now live among them.'
    if lat > 55 and -170 < lon < -50:
        return 'The thaw opened the north of their land to farming, and new towns grew where there had been permafrost.'
    if lat < -60:
        return 'They live on the newest settled land on Earth, the ice-free coasts of Antarctica, under the Antarctic Trust.'
    if 60 < lat and -60 < lon < 50:
        return 'The warming made their northern lands milder and busier than ever, and ice-free seas opened new ports.'
    if -35 < lat < 35 and (-20 < lon < 60 or 60 < lon < 75) and key not in ('amhara', 'oromo', 'kikuyu', 'great_lakes', 'banyarwanda'):
        return 'The heat of the twenty-second century was hard on their land: many moved to the highlands, the coasts or abroad, and water became the measure of every town.'
    if 5 < lat < 30 and 75 < lon < 110:
        return 'The rising sea took the great river deltas, and millions of their people moved up into the hills, where they live crowded but alive.'
    if -10 < lat < 30 and 95 < lon < 140:
        return 'The rising sea drowned the old coastal capitals, and their cities were rebuilt on the hills above the new shore.'
    if 20 < lat < 45 and 100 < lon < 125:
        return 'Shanghai, Tianjin and the old coastal plain went under the rising sea, and their people moved inland, to the hills and the new northern cities.'
    if 24 < lat < 50 and -130 < lon < -60:
        return 'When the sea took Florida, the Gulf coast and lower Manhattan, millions of refugees moved inland, and the old heartland grew crowded, mixed and rich.'
    if -60 < lat < 15 and -85 < lon < -30:
        return 'The sea rose along their coasts and the cities climbed into the hills; the interior and its farms grew in importance.'
    if 35 < lat < 72 and -25 < lon < 45:
        return 'Europe lost its low coasts and polders to the sea; the drowned lowlanders were resettled inland, and few regions are as unmixed as they were a century ago.'
    if 35 < lat < 50 and 45 < lon < 90:
        return 'Their steppes and oases became corridors of trade and migration between a warming north and an overheated south.'
    if -50 < lat < -10 and 110 < lon < 180:
        return 'The heat pushed their towns south and to the coasts, and the outback emptied further.'
    return 'They live through the turbulent twenty-third century, a member people of the United Terran Commonwealth in the long Sol Conflict with Mars.'

def fmt_pop(n):
    if n >= 1e9: return f'{n / 1e9:.1f} billion'
    if n >= 1e6: return f'{n / 1e6:.0f} million' if n >= 1e7 else f'{n / 1e6:.1f} million'
    if n >= 1e4: return f'{round(n / 1e3):,} thousand'
    return 'a few thousand'

def pick(key, options):
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return options[h % len(options)]

GEO = ('plateau', 'mountains', 'hills', 'valley', 'basin', 'highlands', 'coast', 'steppe', 'delta', 'islands', 'river', 'rivers',
       'uplands', 'lowland', 'lowlands', 'forests', 'atolls', 'gorges', 'desert', 'shore', 'sea', 'seas', 'cliffs', 'ranges', 'plain',
       'heights', 'interior', 'north', 'south', 'east', 'west', 'hill', 'grasslands', 'zone', 'belt', 'archipelago', 'corridor', 'peninsula')

def items(text):
    """Split on commas that are not inside parentheses."""
    out, depth, cur = [], 0, ''
    for ch in text:
        depth += ch == '('; depth -= ch == ')'
        if ch == ',' and depth == 0:
            out.append(cur.strip()); cur = ''
        else:
            cur += ch
    if cur.strip(): out.append(cur.strip())
    return out

def place(note, strongholds, family):
    """A clean place name for 'the people of ...'."""
    n = note.split('. Mars:')[0].split(';')[0]
    if ':' in n:
        n = n.split(':')[0]
    if family in ('2240 hybrid', '2240 fusion') or not n or not n[0].isupper():
        return strongholds.split(',')[0].strip() if strongholds else n
    keep = []
    for it in items(n):
        if not it or not it[0].isupper():
            break
        keep.append(it)
    n = ', '.join(keep) if keep else n
    n = n.rstrip('.').strip()
    words = n.split()
    if words and words[-1].lower() in GEO and not n.lower().startswith('the '):
        n = 'the ' + n
    return n

FAITH_LOWER = ('Secular', 'Folk', 'Traditional', 'Animist', 'Indigenous', 'Mostly', 'Mixed', 'Ancestral', 'Many', 'Shamanist', 'Shamanism')

def faith_text(faith):
    parts = [p.strip() for p in items(faith.replace(';', ',')) if p.strip()]
    seen = []
    for p in parts:
        if p.split()[0] in FAITH_LOWER:
            p = p[0].lower() + p[1:]
        if p.lower() not in [x.lower() for x in seen]:
            seen.append(p)
    if not seen: return 'of many faiths'
    if len(seen) == 1: return seen[0]
    return ', '.join(seen[:-1]) + ' or ' + seen[-1]

from peoples_lore_1 import LORE as _L1
from peoples_lore_2 import LORE as _L2
from peoples_lore_3 import LORE as _L3
from peoples_lore_4 import LORE as _L4
from peoples_lore_5 import LORE as _L5
from peoples_lore_6 import LORE as _L6
from peoples_lore_7 import LORE as _L7
from peoples_lore_8 import LORE as _L8
LORE = {**_L1, **_L2, **_L3, **_L4, **_L5, **_L6, **_L7, **_L8}

MARS_LORE = {
 'm_tharsian': ('The Tharsians are the people of the great volcanic bulge, where the first domes went up under Arsia and Pavonis in the 2060s and the independence movement was born.',
                'They live in pressurised towns dug into lava tubes, keep Landing Day with the old flight logs read aloud, and are proud, blunt and fiercely loyal to the Martian cause.'),
 'm_hellasian': ('The Hellasians settled the floor of Hellas, the deepest basin on Mars, where the air is thickest and the first open-air farms became possible under the domes.',
                 'They are farmers and engineers, famous for their greenhouses, their slow, careful speech and the lantern festivals held in the long dust season.'),
 'm_arabian': ('The Martian Arabians live on the cratered uplands of Arabia Terra, settled by miners and later by families from the Gulf, Turkey and South Asia.',
               'They keep coffee and hospitality in the old way, build their towns around ice mines, and pray towards an Earth-bound Mecca by a calendar of their own.'),
 'm_boreal': ('The Boreal coasters settled the northern lowlands around the new polar sea that the terraformers began to fill in the twenty-second century.',
              'They are sailors on the first seas of Mars, fishers of farmed fish under ice, and they say they are the only Martians who have ever seen waves.'),
 'm_elysian': ('The Elysians live around the Elysium volcanoes, a later wave of settlers from Asia and Europe who came with the industrial boom of the 2120s.',
               'They run the foundries and reactors of the north, love music played in the vast lava-tube halls, and quarrel cheerfully with the Tharsians over who founded Mars.'),
 'm_marineris': ('The Mariners are the people of Valles Marineris, the great canyon, whose cliff towns hang on walls seven kilometres high.',
                 'They climb, fly gliders on the canyon winds, and keep the most mixed culture on Mars, a crossroads of every settler line.'),
 'm_olympian': ('The Olympians live around Olympus Mons, the highest mountain in the solar system, where the cliff-foot towns grew up beneath its six-kilometre scarp and launch rails run up its slopes to thin air.',
                'They are pilots, launch crews and cliff builders, proud that every ship leaving Mars passes over their heads, and they hold the Ascent, a race up the volcano, every Martian year.'),
 'm_utopian': ('The Utopians farm Utopia Planitia, the great northern plain where the first open-field crops of Mars were sown under pressure tents; when the northern sea began to fill, their fields became a coast.',
               'They are careful farmers and ferry sailors, keep tea houses and harvest festivals from their Japanese and Korean grandparents, and plant a tree for every child born.'),
 'm_argyrian': ('The Argyrians live in the walled Argyre basin, where meltwater from the southern ice was pooled into the first lake of Mars, ringed by terraced towns.',
                'They fish and sail on their lake, build in white stone cut from the basin rim, and sing in Portuguese-flavoured Martian at the lake festivals of the long southern summer.'),
 'm_isidian': ('The Isidians settled the Isidis basin and the dark sands of Syrtis Major, a later wave from South Asia and the Middle East who came to work the mines and the solar fields.',
               'Their bazaars, spice gardens under glass and colourful festivals of lights and lanterns make Isidis the liveliest region of Mars, and their creole is the trade language of the eastern hemisphere.'),
 'm_austral': ('The Southern highlanders live on the old, cold cratered south of Mars, the last region settled, among ice miners and observatories.',
               'They are hardy, solitary and famously hospitable to travellers caught by dust storms, and keep the longest memory of the dead in every family.'),
}

def _join(xs):
    xs = [x for x in xs if x]
    if not xs: return ''
    if len(xs) == 1: return xs[0]
    return ', '.join(xs[:-1]) + ' and ' + xs[-1]

def _short(n):
    return re.sub(r'\s*\([^)]*\)', '', n).strip()

def _life2240(key, pop, ctx, strongholds):
    s = []
    if strongholds:
        s.append(pick(key + 'w', [f'Their heartland in 2240 is {_join([x.strip() for x in strongholds.split(",")])}.',
                                  f'Today most of them live in {_join([x.strip() for x in strongholds.split(",")])}.']))
    mj, npv = ctx.get('majority', 0), ctx.get('provinces', 0)
    if mj >= 2: s.append(f'They are the majority in {mj} provinces and live in {npv} in all.')
    elif mj == 1: s.append(f'They are the majority in one province and live in {npv} in all.')
    elif npv > 1: s.append(f'They are a minority wherever they live, spread over {npv} provinces.')
    nb = [_short(n) for n in ctx.get('neighbours', [])]
    if nb:
        s.append(pick(key + 'n', [f'Their closest neighbours are the {_join(nb)}, and mixed marriages and shared markets are common.',
                                  f'They share towns and valleys with the {_join(nb)}.',
                                  f'Around them live the {_join(nb)}; old rivalries have softened, but the jokes have not.']))
    if pop >= 100e6:
        s.append(pick(key + 'z', ['They are one of the great peoples of Earth, and no government of the Commonwealth can rule without them.',
                                  'Their numbers give them a loud voice in Earth\'s politics and in the long argument about the war with Mars.']))
    elif pop >= 5e6:
        s.append(pick(key + 'z', ['Their schools, newspapers and broadcasts work in their own language, and their young people move freely between home and the megacities.',
                                  'They have their own media, universities and parties, and send their sons and daughters to the Commonwealth\'s fleets and offices.']))
    else:
        s.append(pick(key + 'z', ['Small as they are, they have kept their language and customs, helped by the cultural charters of the Commonwealth.',
                                  'They are few, and their elders worry about the young leaving for the cities, but their festivals still bring everyone home.']))
    return ' '.join(s)

def describe(key, name, family, homeland, language, faith, pop, strongholds, parents, lat, lon, body, ctx=None):
    ctx = ctx or {}
    the = name if name.lower().startswith('the ') else 'the ' + name
    The = the[0].upper() + the[1:]
    land = place(homeland, strongholds, family)
    faith_l = faith_text(faith)
    p = fmt_pop(pop)
    mars_note = homeland.split('. Mars:')[1].strip().rstrip('.') if '. Mars:' in homeland else ''
    paras = []
    if family == 'Martian':
        h, c = MARS_LORE.get(key, ('', ''))
        paras.append(pick(key, [f'The people of {land} are {the}, about {p} strong, born on Mars of the settlers who came in the 2060s and after.',
                                f'{The} are the Martian-born people of {land}, about {p} in 2240.']) + f' They speak {language}, and most hold to {faith_l}.')
        paras.append((h + ' ' if h else '') + 'Their parents and grandparents fought in the war of independence that began in 2186; they think of themselves as Martians first, and of Earth as the old country that taxed them without a vote.')
        if c: paras.append(c)
        paras.append(_life2240(key, pop, ctx, strongholds))
        return '\n\n'.join(x for x in paras if x)
    if parents:
        pa, pb = [x.strip() for x in parents.split('+')]
        a, b = _short(pa), _short(pb)
        origin = homeland.rstrip('.')
        speech = language.split('(')[0].strip()
        fparts = [x.strip() for x in faith.split(';')[0].replace(' families', '').split(' and ')]
        fparts = [x for i, x in enumerate(fparts) if x and x.lower() not in [y.lower() for y in fparts[:i]]]
        rel = [x for x in fparts if x.lower() != 'secular']
        fusion_faith = (' or '.join(rel) + ' by family, and many are secular') if rel else 'mostly secular'
        paras.append(pick(key, [f'The people of {land} are {the}, a new people of the twenty-third century, born where {a} and {b} families met and married.',
                                f'{The} are a fusion people of 2240 from {land}: {origin}, grown into one community.',
                                f'In {land}, {a} and {b} families have lived side by side for so long that their grandchildren became a people of their own, {the}.'])
                     + f' They number about {p}. At home they speak {speech}, switching between the two in the same sentence; they are {fusion_faith}.')
        pk = ctx.get('parent_keys', [])
        bits = []
        for nm, k in zip((a, b), pk):
            if k in LORE and LORE[k][1]:
                bits.append(f'The {nm} side of the family keeps its own world alive. ' + LORE[k][1])
        if bits: paras.append(' '.join(bits))
        paras.append(pick(key + 'h', ['Their weddings run for days with two kinds of music, their kitchens mix both cuisines into something new, and their children grow up with grandparents who still argue about whose customs come first.',
                                      'They are young, urban and ambitious, and the old communities they came from watch them with a mix of pride and suspicion.',
                                      'They are the face of the new Earth: mixed, mobile, and loyal to their city before any old nation.'])
                     + ' ' + pick(key + 'q', ['Older relatives on both sides complain they have lost their roots; they answer that they grew new ones.',
                                             'Their slang, their food stalls and their music have spread far beyond their own neighbourhoods.']))
        paras.append(_life2240(key, pop, ctx, strongholds))
        return '\n\n'.join(x for x in paras if x)
    # real peoples
    lang1 = language
    paras.append(pick(key, [f'The people of {land} are {the}, about {p} strong in 2240.',
                            f'{The} are the people of {land}, and in 2240 they number about {p}.',
                            f'In {land} live {the}, a people of about {p} in 2240.'])
                 + ' ' + pick(key + 'l', [f'They speak {lang1}, and most are {faith_l}.',
                                          f'Their language is {lang1}; in faith most are {faith_l}.']))
    h, c = LORE.get(key, ('', ''))
    past = FAMILY_PAST.get(family, '')
    paras.append(' '.join(x for x in (past, h) if x))
    if c: paras.append(c)
    hk = hook(lat, lon, key, family) or ''
    tail = _life2240(key, pop, ctx, strongholds)
    if mars_note:
        tail += ' ' + pick(key + 'm', [f'Some of them went to Mars as well: {mars_note[0].lower() + mars_note[1:]}.',
                                      f'Their story reaches Mars too: {mars_note[0].lower() + mars_note[1:]}.'])
    paras.append(' '.join(x for x in (hk, tail) if x))
    return '\n\n'.join(x for x in paras if x)

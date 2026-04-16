"""
Categorize all remaining non_classifie concepts (Easton, BYM, multi-source).
Uses definition analysis from all available dictionary sources.
"""
import json, re
from collections import Counter

def load_json(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

concepts = load_json('uploads/dictionnaires/concepts.json')
easton = load_json('uploads/dictionnaires/easton/easton.entries.json')
smith = load_json('uploads/dictionnaires/smith/smith.entries.json')
bym_raw = load_json('uploads/dictionnaires/bym/bym-lexicon.entries.json')
bym_list = bym_raw if isinstance(bym_raw, list) else bym_raw.get('value', [bym_raw])

easton_by_id = {e['id']: e for e in easton}
smith_by_id = {e['id']: e for e in smith}
bym_by_id = {e['id']: e for e in bym_list}

def get_definition(concept):
    """Get the best definition text from any available entry."""
    texts = []
    for e in concept.get('entries', []):
        eid = e.get('entry_id', '')
        entry = None
        if eid.startswith('easton-'):
            entry = easton_by_id.get(eid)
        elif eid.startswith('smith-'):
            entry = smith_by_id.get(eid)
        elif eid.startswith('bym-'):
            entry = bym_by_id.get(eid)
        if entry:
            defn = entry.get('definition', '')
            if defn:
                texts.append(defn)
    return ' '.join(texts)[:1500]

# ── Classification rules ──

RULES = [
    # (category, patterns_list, min_score)
    ('personnage', [
        r'\bfils d[e\u2019\']', r'\bfille d[e\u2019\']', r'\bfrère d[e\u2019\']',
        r'\bpère d[e\u2019\']', r'\bmère d[e\u2019\']', r'\bfemme d[e\u2019\']',
        r'\broi d[e\u2019\']', r'\bprêtre\b', r'\bprophète\b', r'\bprophétesse\b',
        r'\blévite\b', r'\bchrétien\b', r'\bapôtre\b', r'\bdisciple\b',
        r'\bgouverneur\b', r'\bcapitaine\b', r'\bgénéral\b',
        r'\bjuge d[e\u2019\']', r'\bsacrificateur\b',
        r'\bun des.*vaillants\b', r'\bvaillants? de David\b',
        r'\bl\'un des\b.*\bfils\b', r'\bnom d[e\u2019\'].*\bhomme\b',
        r'\bun? descendant', r'\bun? ancêtre\b',
        r'\bépouse d[e\u2019\']', r'\boncle d[e\u2019\']',
        r'\bav\. J\.-C\.\)', r'\bap\. J\.-C\.\)',
        r'\bavant \d+\s*av\.', r'\baprès \d+\s*ap\.',
        r'\bchef d[e\u2019\'].*tribu\b', r'\bchef de\b',
        r'\bcompagnon\b', r'\bnatif d\b', r'\bun homme\b', r'\bune femme\b',
        r'\bl\'épouse\b', r'\ble mari\b', r'\bévêque\b', r'\bdiacre\b',
        r'\bmartyr\b', r'\bconverti\b', r'\bserviteur d[e\u2019\']',
        r'\bun Manassite\b', r'\bun Benjamite\b', r'\bun Éphraïmite\b',
        r'\bIsraélite\b', r'\bun laïc\b', r'\baîné\b',
    ], 1),

    ('lieu', [
        r'\bville\b', r'\bcité\b', r'\brégion\b', r'\bprovince\b',
        r'\bmontagne\b', r'\bmont\b', r'\bcolline\b', r'\bvallée\b',
        r'\brivière\b', r'\btorrent\b', r'\blac\b', r'\bmer\b',
        r'\bdésert\b', r'\bplaine\b', r'\boasis\b', r'\bîle\b',
        r'\bfrontière d[e\u2019\']', r'\bsur la frontière\b',
        r'\bsitué[e]?\b', r'\bau (?:nord|sud|est|ouest)\b',
        r'\bà .*kilomètres?\b', r'\bà .*milles?\b',
        r'\bl\'une des villes\b', r'\bun lieu\b', r'\bune ville\b',
        r'\bun village\b', r'\bune localité\b', r'\bune forteresse\b',
        r'\bstation\b', r'\bdistrict\b', r'\bterritoire\b',
        r'\bcontrée\b', r'\bpays\b', r'\bcampement\b',
        r'\bgéographi\b', r'\btopographi\b',
    ], 1),

    ('peuple', [
        r'\bpeuple\b', r'\btribu\b', r'\bnation\b',
        r'\bdescendants? d[e\u2019\']', r'\bclan\b', r'\brace\b',
        r'\bhabitants? d[e\u2019\']', r'\bgentilé\b', r'\bnomade\b',
        r'\bpeupl\b', r'\bethni\b',
    ], 1),

    ('doctrine', [
        r'\bdoctrine\b', r'\benseignement\b', r'\bcroyance\b',
        r'\bthéologie\b', r'\brésurrection\b', r'\bsalut\b',
        r'\brédemption\b', r'\bpéché\b', r'\bgrâce\b',
        r'\bfoi\b', r'\bprophétie\b', r'\beschatologie\b',
        r'\balliance\b', r'\bhérésie\b', r'\brepentance\b',
        r'\bjustification\b', r'\bsanctification\b',
        r'\bexpiation\b', r'\bélection\b', r'\bprédestination\b',
        r'\brévélation\b', r'\bspirituel\b',
        r'\bsignifie\b.*\bmot\b', r'\bmot hébreu\b', r'\bmot grec\b',
        r'\bterme\b.*\bsignifi\b', r'\btraduction\b.*\bhébreu\b',
        r'\bdu grec\b.*\bsignifi\b', r'\bde l\'hébreu\b.*\bsignifi\b',
        r'\bsymbole\b', r'\ballégor\b', r'\bparabole\b',
        r'\bmettre à nu\b', r'\brévélation d\'une vérité\b',
        r'\bgénéralement traduit\b',
    ], 1),

    ('rite', [
        r'\bfête\b', r'\bcérémonie\b', r'\brite\b', r'\brituel\b',
        r'\bsacrifice\b', r'\boffrande\b', r'\bpurification\b',
        r'\bcirconcision\b', r'\bbaptême\b', r'\bsabbat\b',
        r'\bjour saint\b', r'\bcélébration\b', r'\blibation\b',
        r'\bablution\b', r'\bfestivité\b', r'\bfestin\b',
        r'\bnoces\b', r'\bmariage\b.*\bfête\b',
        r'\bonction\b', r'\bimmersion\b',
    ], 1),

    ('institution', [
        r'\bsynagogue\b', r'\btemple\b', r'\btabernacle\b',
        r'\bautel\b', r'\bconseil\b', r'\bsanhédrin\b',
        r'\btribunal\b', r'\bécole\b', r'\bassemblée\b',
        r'\bcongrégation\b', r'\béglise\b',
        r'\bcohorte\b', r'\blégion\b', r'\brégiment\b',
        r'\bclergé\b', r'\bsacerdoce\b',
    ], 1),

    ('animal', [
        r'\banimal\b', r'\boiseau\b', r'\bserpent\b', r'\bpoisson\b',
        r'\binsecte\b', r'\bbête\b', r'\breptile\b', r'\bmammifère\b',
        r'\bgazelle\b', r'\bcheval\b', r'\bâne\b', r'\bchameau\b',
        r'\bbrebis\b', r'\bchèvre\b', r'\bbœuf\b', r'\btaureau\b',
        r'\blion\b', r'\bloup\b', r'\bzoologie\b',
        r'\bvipère\b', r'\baigle\b', r'\bcorbeau\b',
        r'\bhibou\b', r'\bpélican\b', r'\bautruche\b',
        r'\bsauterelle\b', r'\bmouche\b', r'\babeille\b',
    ], 1),

    ('plante', [
        r'\bplante\b', r'\barbre\b', r'\bfleur\b', r'\bherbe\b',
        r'\bfruit\b', r'\bvigne\b', r'\bblé\b', r'\borge\b',
        r'\bbotanique\b', r'\bbuisson\b', r'\brésine\b',
        r'\bgomme\b', r'\bencens\b', r'\bmyrrhe\b',
        r'\bbois\b.*\bespèce\b', r'\bépine\b',
        r'\bcèdre\b', r'\bchêne\b', r'\bpalmier\b',
        r'\bfiguier\b', r'\bolivier\b', r'\bgrenadier\b',
    ], 1),

    ('matiere', [
        r'\bmétal\b', r'\bminéral\b', r'\bpierre\b(?!.*précieuse)',
        r'\bcuivre\b', r'\bbronze\b', r'\btissu\b',
        r'\blin\b', r'\blaine\b', r'\bcouleur\b', r'\bteinture\b',
        r'\borganique\b', r'\bparfum\b', r'\bonguent\b',
        r'\bcorindon\b', r'\bdiamant\b', r'\bgem\b',
        r'\bpierre précieuse\b', r'\bjoyau\b',
        r'\bmarbre\b', r'\bargile\b', r'\bcristal\b',
    ], 1),

    ('objet_sacre', [
        r'\binstrument\b', r'\boutil\b', r'\barme\b',
        r'\bépée\b', r'\blance\b', r'\bbouclier\b',
        r'\bvêtement\b', r'\bhabit\b', r'\btunique\b', r'\bmanteau\b',
        r'\bbijou\b', r'\banneau\b', r'\bvase\b', r'\bustensile\b',
        r'\bmeuble\b', r'\barc\b.*\bflèche\b',
        r'\bamulette\b', r'\bornement\b',
        r'\barmure\b', r'\béquipement militaire\b',
        r'\bbracelet\b', r'\bcollier\b',
        r'\btrompette\b', r'\bmusical\b', r'\blyrique\b',
    ], 1),

    ('livre_biblique', [
        r'\blivre d[e\u2019\']', r'\bévangile d[e\u2019\']',
        r'\bépître\b', r'\bcanon\b', r'\bPentateuque\b',
        r'\bApocalypse\b', r'\bSeptante\b',
        r'Book Of', r'\bpsaume\b.*\btitre\b',
    ], 1),

    ('etre_divin', [
        r'\bange\b', r'\bchérubin\b', r'\bséraphin\b',
        r'\bêtre céleste\b', r'\bdivinité\b', r'\bfaux dieu\b',
        r'\bidole\b', r'\bdémon\b', r'\bmauvais esprit\b',
        r'\bangélique\b', r'\bêtre angélique\b',
    ], 1),

    ('evenement', [
        r'\bbataille\b', r'\bguerre\b', r'\bsiège\b',
        r'\bexode\b', r'\bcaptivité\b', r'\bexil\b',
        r'\bconquête\b', r'\brévolte\b', r'\binsurrection\b',
        r'\bdéluge\b', r'\bplaie\b',
    ], 1),

    ('mesures_et_temps', [
        r'\bmesure\b', r'\bpoids\b', r'\bmonnaie\b',
        r'\bcoudée\b', r'\bsicle\b', r'\btalent\b',
        r'\bcalendrier\b', r'\bhin\b', r'\bépha\b',
        r'\bdenari\b', r'\bdrachme\b', r'\bmine\b',
        r'\bstade\b.*\bmesure\b', r'\bempan\b',
    ], 1),

    ('alimentation_et_agriculture', [
        r'\bnourriture\b', r'\baliment\b', r'\bpain\b',
        r'\bvin\b', r'\bhuile\b', r'\bmiel\b', r'\bviande\b',
        r'\bboisson\b', r'\bagriculture\b', r'\brécolte\b',
        r'\bmoisson\b', r'\blabour\b', r'\bsemence\b',
        r'\bboulanger\b', r'\bfromage\b', r'\bbeurre\b',
    ], 1),

    ('corps_et_sante', [
        r'\bmaladie\b', r'\bguérison\b', r'\blèpre\b',
        r'\bparalys\b', r'\baveugle\b', r'\bsourd\b',
        r'\bmédecin\b', r'\bremède\b', r'\bcorps\b.*\bhumain\b',
        r'\bsang\b', r'\bchair\b',
    ], 1),
]


def classify(concept):
    """Classify a concept using its combined definitions."""
    text = get_definition(concept)
    label = concept.get('label', '')

    if not text:
        return None

    scores = {}
    for cat, patterns, min_score in RULES:
        score = 0
        for p in patterns:
            matches = re.findall(p, text, re.I)
            score += len(matches)
        if score >= min_score:
            scores[cat] = score

    if not scores:
        return None

    # Disambiguation rules
    best = max(scores, key=scores.get)

    # If personnage and lieu are close, check which is dominant
    if best == 'personnage' and 'lieu' in scores:
        if scores['lieu'] > scores['personnage']:
            best = 'lieu'
    elif best == 'lieu' and 'personnage' in scores:
        if scores['personnage'] > scores['lieu'] * 1.3:
            best = 'personnage'

    # Doctrine vs other: if term/translation patterns dominate
    if 'doctrine' in scores and scores.get('doctrine', 0) > scores.get(best, 0) * 0.8:
        if any(re.search(p, text, re.I) for p in [
            r'\bsignifie\b', r'\bterme\b', r'\btraduit\b',
            r'\bdu grec\b', r'\bde l\'hébreu\b', r'\bmot\b'
        ]):
            best = 'doctrine'

    return best


# ── Process all non_classifie concepts ──
classified = 0
results = Counter()
still_uncat = []

for c in concepts:
    cat = c.get('category', '') or 'non_classifie'
    if cat != 'non_classifie':
        continue

    new_cat = classify(c)
    if new_cat:
        c['category'] = new_cat
        results[new_cat] += 1
        classified += 1
    else:
        still_uncat.append(c)

print(f"Classified: {classified} / 1012")
print(f"\nCategories assigned:")
for k, v in results.most_common():
    print(f"  {k}: {v}")

print(f"\nStill unclassified: {len(still_uncat)}")
if still_uncat:
    print(f"\nSamples:")
    for c in still_uncat[:20]:
        defn = get_definition(c)[:100]
        print(f"  {c['label']}: {defn}...")

save_json('uploads/dictionnaires/concepts.json', concepts)

# Final totals
all_cats = Counter()
for c in concepts:
    all_cats[c.get('category', '') or 'non_classifie'] += 1
print(f"\n=== FINAL TOTALS ===")
for k, v in all_cats.most_common():
    print(f"  {k}: {v}")
print(f"\nTotal: {len(concepts)}")

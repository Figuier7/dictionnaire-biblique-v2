"""
Categorize the 881 uncategorized Smith-only concepts using definition analysis.
Categories: personnage, lieu, peuple, institution, doctrine, rite, animal, plante,
matiere, livre_biblique, etre_divin, objet_sacre, evenement, mesures_et_temps,
alimentation_et_agriculture, corps_et_sante, objets_et_vetements
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
smith = load_json('uploads/dictionnaires/smith/smith.entries.json')
smith_by_id = {e['id']: e for e in smith}

# ── Keyword-based classification rules ──

# Patterns applied to the definition text (case-insensitive)
PERSON_PATTERNS = [
    r'\bfils d[e\u2019\']',
    r'\bfille d[e\u2019\']',
    r'\bfrère d[e\u2019\']',
    r'\bpère d[e\u2019\']',
    r'\bmère d[e\u2019\']',
    r'\bfemme d[e\u2019\']',
    r'\broi d[e\u2019\']',
    r'\bprêtre\b',
    r'\bprophète\b',
    r'\bprophétesse\b',
    r'\bjuge d[e\u2019\']',
    r'\blévite\b',
    r'\bchrétien\b',
    r'\bapôtre\b',
    r'\bdisciple\b',
    r'\bgénéral\b',
    r'\bcapitaine\b',
    r'\bgouverneur\b',
    r'\bsacerdotal\b',
    r'\bsacrificateur\b',
    r'\bl\'un des\b.*\bfils\b',
    r'\bnom d[e\u2019\'].*\bhomme\b',
    r'\bnom d[e\u2019\'].*\bfemme\b',
    r'\bun? descendant',
    r'\bun? ancêtre\b',
    r'\bun? lévite\b',
    r'\bun? prêtre\b',
    r'\bun? prophète\b',
    r'\bépouse d[e\u2019\']',
    r'\boncle d[e\u2019\']',
    r'\bav\. J\.-C\.\)',  # date marker typical of people
    r'\bap\. J\.-C\.\)',
    r'\bavant \d+\s*av\.',
    r'\baprès \d+\s*ap\.',
]

PLACE_PATTERNS = [
    r'\bville\b',
    r'\bcité\b',
    r'\brégion\b',
    r'\bprovince\b',
    r'\bmontagne\b',
    r'\bmont\b',
    r'\bcolline\b',
    r'\bvallée\b',
    r'\brivière\b',
    r'\btorrent\b',
    r'\blac\b',
    r'\bmer\b',
    r'\bdésert\b',
    r'\bplaine\b',
    r'\boasis\b',
    r'\bfrontière d[e\u2019\']',
    r'\bsur la frontière\b',
    r'\blieu\b(?!.*\bnom\b)',
    r'\bsitué[e]?\b',
    r'\bau (?:nord|sud|est|ouest)\b',
    r'\bà .*kilomètres?\b',
    r'\bà .*milles?\b',
    r'\bl\'une des villes\b',
    r'\bun lieu\b',
    r'\bune ville\b',
    r'\bun village\b',
    r'\bune localité\b',
    r'\bune forteresse\b',
    r'\bune place forte\b',
    r'\bstation\b.*\bdésert\b',
    r'\bcampement\b',
    r'\bdistrict\b',
    r'\bterritoire\b',
    r'\bcontrée\b',
    r'\bpays\b',
    r'\bîle\b',
]

PEOPLE_PATTERNS = [
    r'\bpeuple\b',
    r'\btribu\b',
    r'\bnation\b',
    r'\bdescendants? d[e\u2019\']',
    r'\bfamille\b.*\btribu\b',
    r'\bclan\b',
    r'\brace\b',
    r'\bethnie\b',
    r'\bhabitants? d[e\u2019\']',
    r'\bles fils d[e\u2019\'].*\bcollectivement\b',
    r'\bgentilé\b',
    r'\bnomade\b',
]

BOOK_PATTERNS = [
    r'\blivre\b.*\bBible\b',
    r'\blivre d[e\u2019\']',
    r'\blivre biblique\b',
    r'\bcanon\b',
    r'\bévangile d[e\u2019\']',
    r'\bépître\b',
    r'\bApocalypse\b',
    r'\bPentateuque\b',
    r'\bSeptante\b',
    r'Book Of',  # in the label
]

DIVINE_PATTERNS = [
    r'\bange\b',
    r'\bchérubin\b',
    r'\bséraphin\b',
    r'\bêtre céleste\b',
    r'\bdivinité\b',
    r'\bfaux dieu\b',
    r'\bidole\b',
    r'\bdivin\b',
]

ANIMAL_PATTERNS = [
    r'\banimal\b',
    r'\boiseau\b',
    r'\bserpent\b',
    r'\bpoisson\b',
    r'\binsecte\b',
    r'\bbête\b',
    r'\breptile\b',
    r'\bmammifère\b',
    r'\bgazelle\b',
    r'\bcheval\b',
    r'\bâne\b',
    r'\bchameau\b',
    r'\bbrebis\b',
    r'\bchèvre\b',
    r'\bbœuf\b',
    r'\btaureau\b',
    r'\blion\b',
    r'\bloup\b',
    r'\beaucoup d\'espèces\b',
    r'\bzoologie\b',
]

PLANT_PATTERNS = [
    r'\bplante\b',
    r'\barbre\b',
    r'\bfleur\b',
    r'\bherbe\b',
    r'\bfruit\b',
    r'\bvigne\b',
    r'\bblé\b',
    r'\borge\b',
    r'\bépine\b',
    r'\bbotanique\b',
    r'\bbuisson\b',
    r'\bbois\b.*\bespèce\b',
    r'\brésine\b',
    r'\bgomme\b',
    r'\bencens\b',
    r'\bmyrrhe\b',
]

OBJECT_PATTERNS = [
    r'\binstrument\b',
    r'\boutil\b',
    r'\barme\b',
    r'\bépée\b',
    r'\blance\b',
    r'\bbouclier\b',
    r'\bvêtement\b',
    r'\bhabit\b',
    r'\btunique\b',
    r'\bmanteau\b',
    r'\bbijou\b',
    r'\bjoyau\b',
    r'\bpierre précieuse\b',
    r'\banneau\b',
    r'\bvase\b',
    r'\bustensile\b',
    r'\bmeuble\b',
]

RITE_PATTERNS = [
    r'\bfête\b',
    r'\bcérémonie\b',
    r'\brit[eu]\b',
    r'\bsacrifice\b',
    r'\boffrande\b',
    r'\bpurification\b',
    r'\bcirconcision\b',
    r'\bbaptême\b',
    r'\bsabbat\b',
    r'\bjour saint\b',
    r'\bcélébration\b',
]

DOCTRINE_PATTERNS = [
    r'\bdoctrine\b',
    r'\benseignement\b',
    r'\bcroyance\b',
    r'\bthéologie\b',
    r'\brésurrection\b',
    r'\bsalut\b',
    r'\brédemption\b',
    r'\bpéché\b',
    r'\bgrâce\b',
    r'\bfoi\b',
    r'\bprophétie\b',
    r'\beschatologie\b',
    r'\balliance\b',
    r'\bhérésie\b',
]

INSTITUTION_PATTERNS = [
    r'\bsynagogue\b',
    r'\btemple\b',
    r'\btabernacle\b',
    r'\bautel\b',
    r'\bconseil\b',
    r'\bsanhédrin\b',
    r'\btribunal\b',
    r'\bécole\b',
    r'\bassemblée\b',
]

MEASURE_PATTERNS = [
    r'\bmesure\b',
    r'\bpoids\b',
    r'\bmonnaie\b',
    r'\bcoudée\b',
    r'\bsicle\b',
    r'\btalent\b',
    r'\bmois\b.*\bcalendrier\b',
    r'\bhin\b',
    r'\bbath\b.*\bmesure\b',
    r'\bépha\b',
]

FOOD_PATTERNS = [
    r'\bnourriture\b',
    r'\baliment\b',
    r'\bpain\b',
    r'\bvin\b',
    r'\bhuile\b',
    r'\bmiel\b',
    r'\bviande\b',
    r'\bboisson\b',
    r'\bcuisine\b',
    r'\bagriculture\b',
    r'\brécolte\b',
    r'\bmoisson\b',
    r'\blabour\b',
    r'\bsemence\b',
]

MATERIAL_PATTERNS = [
    r'\bmétal\b',
    r'\bminéral\b',
    r'\bpierre\b(?!.*\bpré)',
    r'\bor\b.*\bmétal\b',
    r'\bargent\b.*\bmétal\b',
    r'\bcuivre\b',
    r'\bfer\b.*\bmétal\b',
    r'\bbronze\b',
    r'\btissu\b',
    r'\blin\b',
    r'\blaine\b',
    r'\bcouleur\b',
    r'\bteinture\b',
]

EVENT_PATTERNS = [
    r'\bbataille\b',
    r'\bguerre\b',
    r'\bsiège\b',
    r'\bexode\b',
    r'\bcaptivité\b',
    r'\bexil\b',
    r'\bconquête\b',
    r'\bmigration\b',
    r'\brévolte\b',
    r'\binsurrection\b',
]


def classify(concept, smith_entry):
    """Return a category for the given concept based on definition analysis."""
    label = concept.get('label', '')
    defn = smith_entry.get('definition', '')
    text = defn[:600]  # Focus on beginning for classification

    # Cross-references only (e.g., "[Achsah]") - inherit from target
    if re.match(r'^\s*\[+\d*\]*\s*\[?\w', defn) and len(defn) < 100:
        return None  # Can't classify from xref alone

    # Check "Book Of" in label first
    if re.search(r'Book Of|Livre d', label, re.I):
        return 'livre_biblique'

    # Score each category
    scores = {}

    categories = [
        ('personnage', PERSON_PATTERNS),
        ('lieu', PLACE_PATTERNS),
        ('peuple', PEOPLE_PATTERNS),
        ('livre_biblique', BOOK_PATTERNS),
        ('etre_divin', DIVINE_PATTERNS),
        ('animal', ANIMAL_PATTERNS),
        ('plante', PLANT_PATTERNS),
        ('objet_sacre', OBJECT_PATTERNS),
        ('rite', RITE_PATTERNS),
        ('doctrine', DOCTRINE_PATTERNS),
        ('institution', INSTITUTION_PATTERNS),
        ('mesures_et_temps', MEASURE_PATTERNS),
        ('alimentation_et_agriculture', FOOD_PATTERNS),
        ('matiere', MATERIAL_PATTERNS),
        ('evenement', EVENT_PATTERNS),
    ]

    for cat, patterns in categories:
        score = 0
        for p in patterns:
            matches = re.findall(p, text, re.I)
            score += len(matches)
        if score > 0:
            scores[cat] = score

    if not scores:
        # Heuristic: most uncategorized Smith entries with short definitions
        # containing parenthetical etymology are people
        if re.match(r'^\s*\(', text) and any(re.search(p, text, re.I) for p in [
            r'\bfils\b', r'\bfille\b', r'\bnom\b', r'\bIsraélite\b',
            r'\baîné\b', r'\bsecond\b', r'\btroisième\b',
        ]):
            return 'personnage'
        return None

    # Return highest scoring category
    best = max(scores, key=scores.get)

    # Disambiguation: personnage vs lieu
    if best == 'personnage' and 'lieu' in scores:
        if scores['lieu'] > scores['personnage']:
            return 'lieu'
    if best == 'lieu' and 'personnage' in scores:
        if scores['personnage'] > scores['lieu'] * 1.5:
            return 'personnage'

    return best


# ── Classify all uncategorized Smith-only concepts ──
results = Counter()
classified = 0
unclassified_examples = []

for c in concepts:
    cat = c.get('category', '') or 'non_classifie'
    if cat != 'non_classifie':
        continue

    sources = set(e.get('entry_id','').split('-')[0] for e in c.get('entries',[]))
    if sources != {'smith'}:
        continue

    smith_eid = [e['entry_id'] for e in c['entries'] if e['entry_id'].startswith('smith-')][0]
    se = smith_by_id.get(smith_eid, {})

    new_cat = classify(c, se)
    if new_cat:
        c['category'] = new_cat
        results[new_cat] += 1
        classified += 1
    else:
        if len(unclassified_examples) < 20:
            defn = se.get('definition', '')[:120]
            unclassified_examples.append(f"  {c['label']}: {defn}")

print(f"Classified: {classified} / 881")
print(f"\nCategories assigned:")
for k, v in results.most_common():
    print(f"  {k}: {v}")

print(f"\nStill unclassified: {881 - classified}")
if unclassified_examples:
    print(f"\nExamples of remaining unclassified:")
    for e in unclassified_examples:
        print(e)

# Save
save_json('uploads/dictionnaires/concepts.json', concepts)
print(f"\nconcepts.json saved with updated categories.")

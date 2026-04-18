#!/usr/bin/env python3
"""Phase 2: Extend concept-hebrew mapping to common concepts."""
import json, sys, io, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE, 'uploads/dictionnaires/concepts.json'), encoding='utf-8') as f:
    concepts = json.load(f)
with open(os.path.join(BASE, 'uploads/dictionnaires/concept-hebrew-map.json'), encoding='utf-8') as f:
    existing_map = json.load(f)
with open(os.path.join(BASE, 'hebrew-lexicon-fr-compact.json'), encoding='utf-8') as f:
    lexicon = json.load(f)

lex_by_strong = {e['s']: e for e in lexicon}

# Manual verified mappings: concept_label_lower -> [Strong IDs]
MANUAL = {
    'foi': ['H529','H530'],
    'alliance': ['H1285'],
    'paix': ['H7965'],
    'grace': ['H2580','H2617'],
    'amour': ['H157','H160'],
    'priere': ['H8605'],
    'justice': ['H6664','H6666'],
    'peche': ['H2398','H2399','H2403'],
    'salut': ['H3444','H3468'],
    'redemption': ['H1350','H1353','H6299','H6306'],
    'prophetie': ['H5016','H5030'],
    'sagesse': ['H2449','H2451'],
    'louange': ['H1984','H8416'],
    'benediction': ['H1288','H1293'],
    'malediction': ['H779','H7045'],
    'repentance': ['H5162','H7725'],
    'sanctification': ['H6942','H6944'],
    'expiation': ['H3722','H3725'],
    'sacrifice': ['H2077','H4503'],
    'holocauste': ['H5930'],
    'offrande': ['H4503','H7133'],
    'autel': ['H4196'],
    'tabernacle': ['H4908','H168'],
    'temple': ['H1964'],
    'sabbat': ['H7676'],
    'circoncision': ['H4135','H4139'],
    'onction': ['H4886','H4888'],
    'jugement': ['H4941','H8199'],
    'colere': ['H639','H2534'],
    'misericorde': ['H2617','H7355'],
    'verite': ['H571'],
    'gloire': ['H3519','H8597'],
    'roi': ['H4428'],
    'royaume': ['H4467','H4468'],
    'berger': ['H7462','H7473'],
    'prophete': ['H5030'],
    'sacrificateur': ['H3548'],
    'ange': ['H4397'],
    'satan': ['H7854'],
    'ciel': ['H8064'],
    'terre': ['H776'],
    'mer': ['H3220'],
    'eau': ['H4325'],
    'feu': ['H784'],
    'sang': ['H1818'],
    'pain': ['H3899'],
    'vin': ['H3196'],
    'huile': ['H8081'],
    'or': ['H2091'],
    'argent': ['H3701'],
    'epee': ['H2719'],
    'pierre': ['H68'],
    'montagne': ['H2022'],
    'desert': ['H4057'],
    'fleuve': ['H5104'],
    'arbre': ['H6086'],
    'vigne': ['H1612','H3754'],
    'ble': ['H2406'],
    'mort': ['H4191','H4194'],
    'vie': ['H2416','H2425'],
    'ame': ['H5315'],
    'esprit': ['H7307'],
    'coeur': ['H3820'],
    'lumiere': ['H216'],
    'tenebres': ['H2822'],
    'peuple': ['H5971'],
    'nation': ['H1471'],
    'serviteur': ['H5650'],
    'fils': ['H1121'],
    'fille': ['H1323'],
    'pere': ['H1'],
    'mere': ['H517'],
    'frere': ['H251'],
    'homme': ['H120','H376'],
    'femme': ['H802'],
    'maison': ['H1004'],
    'ville': ['H5892'],
    'porte': ['H8179'],
    'chemin': ['H1870'],
    'guerre': ['H4421'],
    'joie': ['H8057','H1524'],
    'deuil': ['H60','H4553'],
    'honte': ['H954','H1322'],
    'crainte': ['H3374'],
    'esperance': ['H8615'],
    'orgueil': ['H1346','H1347'],
    'humilite': ['H6038'],
    'idole': ['H457','H6091'],
    'idolatrie': ['H8655'],
    'serment': ['H7621'],
    'trone': ['H3678'],
    'couronne': ['H5850','H3804'],
    'sceptre': ['H7626','H8275'],
    'loi': ['H8451'],
    'commandement': ['H4687'],
    'statut': ['H2706'],
    'temoignage': ['H5715'],
    'decret': ['H1881','H2706'],
    'pardon': ['H5545','H5547'],
    'consolation': ['H5150','H5162'],
    'delivrance': ['H3444','H6413'],
    'captivite': ['H1473','H7622'],
    'exil': ['H1546','H1547'],
    'esclavage': ['H5650','H5659'],
    'liberte': ['H1865','H2670'],
    'heritage': ['H5159'],
    'promesse': ['H1697'],
    'propitiation': ['H3722','H3727'],
    'justification': ['H6663','H6666'],
    'sanctuaire': ['H4720'],
    'arche': ['H727'],
    'encens': ['H7004'],
    'dime': ['H4643'],
    'premier-ne': ['H1060','H1062'],
    'paque': ['H6453'],
    'pentecote': ['H2282'],
    'resurrection': ['H6965','H8545'],
    'tentation': ['H4531'],
    'jeune': ['H6685'],
    'onction': ['H4888'],
    'redempteur': ['H1350'],
    'sauveur': ['H3467'],
    'juge': ['H8199'],
    'createur': ['H1254'],
    'creation': ['H1254'],
    'deluge': ['H3999'],
    'arc-en-ciel': ['H7198'],
    'manne': ['H4478'],
    'miracle': ['H4159','H226'],
    'vision': ['H2377','H4236'],
    'songe': ['H2472'],
    'angel': ['H4397'],
    'cherubins': ['H3742'],
    'seraphins': ['H8314'],
    'leviathan': ['H3882'],
    'enfer': ['H7585'],
    'paradis': ['H6508'],
    'tribulation': ['H6869'],
    'persecution': ['H7291'],
    'conversion': ['H7725','H8666'],
    'bapteme': ['H2881'],
    'apotre': ['H7971'],
    'ancien': ['H2205'],
    'diacre': ['H8334'],
    'eglise': ['H6951'],
    'assemblee': ['H6951','H5712'],
    'synagogue': ['H4150'],
    'chretien': ['H4899'],
    'disciple': ['H3928'],
    'pasteur': ['H7462'],
    'evangeliste': ['H1319'],
    'docteur': ['H3384'],
    'predication': ['H7150'],
    'confession': ['H3034'],
    'adoration': ['H7812'],
    'culte': ['H5656'],
    'meditation': ['H1902','H7879'],
    'intercession': ['H6293'],
    'benediction': ['H1293'],
    'psaume': ['H4210'],
    'cantique': ['H7892'],
    'harpe': ['H3658'],
    'trompette': ['H2689','H7782'],
    'cloche': ['H6472'],
    'parfum': ['H7004','H5561'],
    'myrrhe': ['H4753'],
    'olive': ['H2132'],
    'palmier': ['H8558'],
    'cedre': ['H730'],
    'figuier': ['H8384'],
    'grenade': ['H7416'],
    'miel': ['H1706'],
    'lait': ['H2461'],
    'sel': ['H4417'],
    'levain': ['H7603','H2557'],
    'agneau': ['H3532','H7716'],
    'boeuf': ['H7794','H1241'],
    'colombe': ['H3123'],
    'aigle': ['H5404'],
    'lion': ['H738'],
    'serpent': ['H5175'],
    'brebis': ['H7716','H3535'],
    'cheval': ['H5483'],
    'ane': ['H2543'],
    'chameau': ['H1581'],
    'loup': ['H2061'],
    'corbeau': ['H6158'],
    'sauterelle': ['H697'],
    'poisson': ['H1710'],
    'pourpre': ['H713'],
    'ecarlate': ['H8144','H8438'],
    'lin': ['H6593','H948'],
    'laine': ['H6785'],
    'bronze': ['H5178'],
    'fer': ['H1270'],
    'cuivre': ['H5178'],
    'etain': ['H913'],
    'plomb': ['H5777'],
}

new_map = {}
manual_count = 0

# Apply manual mappings
concept_by_label = {}
for c in concepts:
    label = c.get('label', '').lower().strip()
    # Normalize accents for matching
    label_norm = label.replace('\u00e9', 'e').replace('\u00e8', 'e').replace('\u00ea', 'e').replace('\u00f4', 'o').replace('\u00e2', 'a').replace('\u00ee', 'i').replace('\u00fb', 'u').replace('\u00e0', 'a')
    if label not in concept_by_label:
        concept_by_label[label] = []
    concept_by_label[label].append(c)
    if label_norm != label and label_norm not in concept_by_label:
        concept_by_label[label_norm] = []
    if label_norm != label:
        concept_by_label[label_norm].append(c)

for label_key, strong_ids in MANUAL.items():
    matching = concept_by_label.get(label_key, [])
    for mc in matching:
        cid = mc['concept_id']
        if cid in existing_map:
            continue
        entries = []
        for sid in strong_ids:
            e = lex_by_strong.get(sid)
            if e:
                entries.append({'s': sid, 'h': e.get('h', ''), 'x': e.get('x', '')})
        if entries:
            new_map[cid] = entries
            manual_count += 1

# Phase 2A auto: exact label match on first gloss
first_gloss_idx = {}
for entry in lexicon:
    if entry.get('l') == 'arc':
        continue
    glosses = entry.get('g', [])
    if glosses and isinstance(glosses, list) and glosses[0]:
        fg = glosses[0].lower().strip()
        if fg not in first_gloss_idx:
            first_gloss_idx[fg] = []
        first_gloss_idx[fg].append(entry)

COMMON_CATS = {'doctrine','rite','institution','objet_sacre','matiere',
               'animal','plante','alimentation_et_agriculture','corps_et_sante',
               'mesures_et_temps','evenement','objets_et_vetements','etre_spirituel',
               'non_classifie'}

auto_count = 0
for c in concepts:
    cid = c.get('concept_id', '')
    label = c.get('label', '').lower().strip()
    cat = c.get('category', '')
    if cid in existing_map or cid in new_map:
        continue
    if cat not in COMMON_CATS:
        continue
    candidates = first_gloss_idx.get(label, [])
    # Filter: only Hebrew, not proper nouns
    candidates = [e for e in candidates if e.get('l') != 'arc' and not (e.get('p','').startswith('n-pr'))]
    if candidates:
        entries = [{'s': e['s'], 'h': e.get('h',''), 'x': e.get('x','')} for e in candidates]
        new_map[cid] = entries
        auto_count += 1

print(f'=== Phase 2 Results ===')
print(f'Manual verified: {manual_count}')
print(f'Auto first-gloss: {auto_count}')
print(f'Total new: {len(new_map)}')
print(f'Existing: {len(existing_map)}')
print(f'New total: {len(existing_map) + len(new_map)}')
print(f'Coverage: {(len(existing_map) + len(new_map))}/{len(concepts)} = {(len(existing_map) + len(new_map))/len(concepts)*100:.1f}%')

# Apply: merge into existing map
merged = dict(existing_map)
merged.update(new_map)

out_path = os.path.join(BASE, 'uploads/dictionnaires/concept-hebrew-map.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(merged, f, ensure_ascii=False, separators=(',', ':'))
print(f'\nWritten: {out_path} ({len(merged)} concepts)')

# Report
print(f'\n=== New mappings ===')
for cid, entries in sorted(new_map.items()):
    label = next((c2['label'] for c2 in concepts if c2['concept_id'] == cid), cid)
    strongs = ', '.join(e['s'] + ' ' + e['h'] for e in entries[:4])
    extra = f' (+{len(entries)-4})' if len(entries) > 4 else ''
    print(f'  {label}: {strongs}{extra}')

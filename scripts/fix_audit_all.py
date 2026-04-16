#!/usr/bin/env python3
"""
Applique toutes les corrections issues de l'audit complet 2026-03-31.
- Résidus anglais (Easton + Smith)
- Labels corrompus
- Références cassées
- Recatégorisations
- Fusions BYM ALL-CAPS
- Fusions doublons sémantiques
"""
import json, sys, io, os, re
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = "uploads/dictionnaires"

def load(path):
    with open(os.path.join(BASE, path), 'r', encoding='utf-8-sig') as f:
        return json.load(f)

def save(path, data, bom=True):
    enc = 'utf-8-sig' if bom else 'utf-8'
    with open(os.path.join(BASE, path), 'w', encoding=enc) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print("PHASE 1 : Résidus anglais dans mot/label_fr")
print("=" * 70)

easton = load("easton/easton.entries.json")
smith = load("smith/smith.entries.json")

entry_fixes = {
    # Easton (10 critiques)
    "easton-000977": "Bien-aimé(e)",
    "easton-001386": "Phylactères",
    "easton-001701": "Âne mâle",
    "easton-002554": "Démarche affectée",
    "easton-002765": "Prosternation",
    "easton-003021": "Chaire",
    "easton-003436": "Pièce d'argent",
    "easton-003454": "Position assise",
    "easton-003558": "Battement de tambour",
    "easton-003569": "Gréement",
    # Smith (61 résidus)
    "smith-000315": "Onction",
    "smith-000316": "Fourmi",
    "smith-000544": "Sac",
    "smith-000560": "Baume",
    "smith-000563": "Bande",
    "smith-000614": "Barbe",
    "smith-000820": "Frère",
    "smith-000830": "Buisson",
    "smith-000842": "Cage",
    "smith-000744": "Fiançailles",
    "smith-000855": "Camp",
    "smith-000890": "Sculpture",
    "smith-000918": "Chambre",
    "smith-000955": "Coffre",
    "smith-000988": "Église",
    "smith-001011": "Vêtements",
    "smith-001065": "Cour",
    "smith-001079": "Croix",
    "smith-001113": "Danse",
    "smith-001127": "Fille",
    "smith-001156": "Désert",
    "smith-001163": "Diamant",
    "smith-001188": "Divorce",
    "smith-001207": "Dragon",
    "smith-001224": "Terre",
    "smith-001249": "Éducation",
    "smith-001352": "Campement",
    "smith-001481": "Graisse",
    "smith-001506": "Chair",
    "smith-001511": "Flûte",
    "smith-001514": "Nourriture",
    "smith-001563": "Potence",
    "smith-001878": "Haie",
    "smith-001881": "Génisse",
    "smith-001915": "Troupeau",
    "smith-001927": "Héron",
    "smith-001989": "Corne",
    "smith-002060": "Image",
    "smith-002069": "Héritage",
    "smith-002648": "Lion",
    "smith-002943": "Millet",
    "smith-002971": "Mitre",
    "smith-003148": "Nitre",
    "smith-003176": "Oblation",
    "smith-003205": "Onyx",
    "smith-003274": "Passage",
    "smith-003325": "Pestilence",
    "smith-003381": "Pigeon",
    "smith-003429": "Pot",
    "smith-003446": "Prison",
    "smith-003453": "Province",
    "smith-003470": "Purification",
    "smith-003610": "Rose",
    "smith-003614": "Rue",
    "smith-003632": "Sacrifice",
    "smith-003696": "Scorpion",
    "smith-003744": "Serpent",
    "smith-004092": "Synagogue",
    "smith-004106": "Battement de tambour",
    "smith-004107": "Tabernacle",
    "smith-004124": "Talent",
    "smith-004170": "Temple",
}

count_e = count_s = 0
for e in easton:
    if e['id'] in entry_fixes:
        e['mot'] = entry_fixes[e['id']]
        e['label_fr'] = entry_fixes[e['id']]
        count_e += 1
for e in smith:
    if e['id'] in entry_fixes:
        e['mot'] = entry_fixes[e['id']]
        e['label_fr'] = entry_fixes[e['id']]
        count_s += 1

save("easton/easton.entries.json", easton, bom=False)
save("smith/smith.entries.json", smith, bom=False)
print(f"  Easton: {count_e} corrections | Smith: {count_s} corrections")

# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PHASE 2 : Labels corrompus / concaténés")
print("=" * 70)

concepts = load("concepts.json")

label_fixes = {
    "achevementdesages": "Achèvement des âges",
    "blasphemecontrelesaint-esprit": "Blasphème contre le Saint-Esprit",
    "chepharhaammonai": "Chephar-haammonai",
}

# Fix (gr.) artifacts
label_gr_fix = {"yoshiyah": "Josias", "yonah-2": "Jonas"}

count_labels = 0
for c in concepts:
    cid = c['concept_id']
    if cid in label_fixes:
        old = c['label']
        c['label'] = label_fixes[cid]
        c['display_titles']['primary'] = label_fixes[cid]
        c['public_forms']['french_reference'] = label_fixes[cid]
        print(f"  {cid}: '{old}' -> '{c['label']}'")
        count_labels += 1
    if cid in label_gr_fix:
        old = c['label']
        c['label'] = label_gr_fix[cid]
        c['display_titles']['primary'] = label_gr_fix[cid]
        c['public_forms']['french_reference'] = label_gr_fix[cid]
        print(f"  {cid}: '{old}' -> '{c['label']}'")
        count_labels += 1

print(f"  {count_labels} labels corrigés")

# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PHASE 3 : Références cassées related_concepts")
print("=" * 70)

valid_cids = set(c['concept_id'] for c in concepts)
broken_refs = {"bapteme-chretien", "baptism", "joseph", "funerals",
               "chief-priest", "high_places6813_priest", "yithro"}

count_broken = 0
for c in concepts:
    rc = c.get('related_concepts', [])
    if rc:
        cleaned = [r for r in rc if r.get('concept_id','') in valid_cids]
        removed = len(rc) - len(cleaned)
        if removed > 0:
            c['related_concepts'] = cleaned
            count_broken += removed

print(f"  {count_broken} références cassées supprimées")

# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PHASE 4 : Recatégorisations (138 concepts)")
print("=" * 70)

recats = {
    # personnage -> autre
    "assemblee": "institution", "apotre": "institution", "prophete": "institution",
    "juge": "institution", "eunuque": "institution", "chretien": "institution",
    "diacre": "institution", "tetrarque": "institution", "disciple": "institution",
    "grand-pretre": "institution", "premierpretre": "institution",
    "roi": "institution", "reine": "institution", "procurator": "institution",
    "serviteur": "institution", "servante": "institution",
    "prophetie": "doctrine", "peche": "doctrine", "reconciliation": "doctrine",
    "lumiere": "doctrine", "jugement-final": "doctrine",
    "fils-de-l-homme": "doctrine", "filsd-humain": "doctrine",
    "fils": "doctrine", "son": "doctrine",
    "semitic_languages": "doctrine", "shemitic_languages": "doctrine",
    "versions_ancient_of_the_old_and_new_testaments": "doctrine",
    "vol": "doctrine", "spouse": "doctrine",
    "sidon": "lieu", "galilee": "lieu", "smyrna": "lieu",
    "thessalonica": "lieu", "laodicea": "lieu", "kiriathaim": "lieu",
    "dale-du-roi": "lieu", "vallee-du-roi": "lieu",
    "actes-des-apotres": "livre_biblique", "livre-des-juges": "livre_biblique",
    "kings": "livre_biblique", "rois": "livre_biblique",
    "ephesians_the_epistle_to_the": "livre_biblique",
    "wisdom_of_jesus_son_of_sirach": "livre_biblique",
    "couronne": "objet_sacre", "ephod": "objet_sacre",
    "lookingglas": "objets_et_vetements", "miroir": "objets_et_vetements",
    "hibou": "animal", "paille": "plante",
    "reine-du-ciel": "etre_spirituel",
    "solomons_servants": "peuple", "israel": "peuple",
    # peuple -> autre
    "loi": "doctrine", "malediction": "doctrine", "salut-2": "doctrine",
    "communion": "doctrine", "communion-3": "doctrine",
    "jourduseigneur": "doctrine", "salut": "doctrine",
    "vigne": "plante", "acacia-2": "plante",
    "manne": "alimentation_et_agriculture", "moisson": "alimentation_et_agriculture",
    "glanage": "alimentation_et_agriculture", "gleaning": "alimentation_et_agriculture",
    "offrande": "rite", "paque-2": "rite",
    "yeriycho": "lieu", "kadesh": "lieu", "marah": "lieu",
    "massah": "lieu", "kibroth-hattaavah": "lieu",
    "shaveh-kiriathaim": "lieu", "laodicee": "lieu",
    "netanel": "personnage", "nikodemos": "personnage",
    "rehabam": "personnage", "jerijah": "personnage",
    # lieu -> autre
    "yishmael": "personnage", "yishmael-2": "personnage",
    "jour-du-seigneur": "doctrine", "deluge-2": "evenement",
    "encens-2": "plante", "piete-2": "doctrine",
    "vipere-2": "animal", "sidonians": "peuple",
    "fiancer": "rite", "sceau-2": "matiere",
    "ephesiens-epitre-aux": "livre_biblique",
    # doctrine -> autre
    "rush": "plante", "sweat_bloody": "corps_et_sante",
    "treillis": "objets_et_vetements", "veilles": "mesures_et_temps",
    "coiffes": "objets_et_vetements", "yah": "etre_spirituel",
    "mara": "lieu", "servitor": "institution",
    # rite -> autre
    "qayin": "personnage", "qayin-2": "personnage",
    "eveque": "institution", "arc-2": "objet_sacre",
    # institution -> autre
    "nicodemus": "personnage", "olivier": "plante",
    "achevementdesages": "evenement",
    "epouse": "doctrine", "epouse-2": "doctrine",
    # evenement -> autre
    "elohim": "etre_spirituel", "gifts-spiritual": "doctrine",
    "sibbecai": "personnage", "zebaim": "lieu",
    # etre_spirituel -> autre
    "a": "doctrine", "omega": "doctrine", "alpha-et-omega": "doctrine",
    "anathoth": "lieu", "paque": "rite",
    "crainte-de-yhwh": "doctrine", "divinite": "doctrine",
    "esprit-2": "doctrine", "demetrius": "personnage",
    "demetrios": "personnage", "adorateur": "institution",
    "how_the_prophetic_gift_was_received": "doctrine",
    "bosquet": "lieu",
    # matiere -> autre
    "fallow_deer": "animal", "flute-2": "objets_et_vetements",
    "etoile-du-matin": "doctrine",
    # objet_sacre -> autre
    "bitume": "matiere", "coiffes-2": "objets_et_vetements",
    # plante -> autre (glanage already done above)
    # livre_biblique -> autre
    "paradise": "lieu",
    # mesures_et_temps -> autre (glanage already in alimentation)
}

count_recat = 0
for c in concepts:
    if c['concept_id'] in recats:
        old = c['category']
        new = recats[c['concept_id']]
        if old != new:
            c['category'] = new
            count_recat += 1

print(f"  {count_recat} concepts recatégorisés")

# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PHASE 5 : Fusion des doublons BYM ALL-CAPS (44)")
print("=" * 70)

links = load("concept-entry-links.json")

# Find ALL-CAPS concepts that are BYM orphans
allcaps = []
for c in concepts:
    if c['label'] == c['label'].upper() and len(c['label']) > 2:
        # Check if it's a BYM-only concept
        dicts = set(e.get('dictionary','') for e in c['entries'])
        if dicts == {'bym_lexicon'} or (len(c['entries']) == 1 and c['entries'][0].get('dictionary') == 'bym_lexicon'):
            allcaps.append(c)

# Find matching primary concept for each
merge_map = {}
for ac in allcaps:
    ac_label_lower = ac['label'].lower().replace("'", "").replace("\u2019", "").replace("-", " ")
    best = None
    for c in concepts:
        if c['concept_id'] == ac['concept_id']:
            continue
        c_label_lower = c['label'].lower().replace("'", "").replace("\u2019", "").replace("-", " ")
        if c_label_lower == ac_label_lower and c['label'] != c['label'].upper():
            best = c
            break
    if best:
        merge_map[ac['concept_id']] = best['concept_id']

# Execute merges
merged_cids = set()
clookup = {c['concept_id']: c for c in concepts}
for src_cid, tgt_cid in merge_map.items():
    src = clookup.get(src_cid)
    tgt = clookup.get(tgt_cid)
    if not src or not tgt:
        continue
    # Merge entries
    existing = set(e['entry_id'] for e in tgt['entries'])
    for entry in src['entries']:
        if entry['entry_id'] not in existing:
            tgt['entries'].append(entry)
    # Add aliases
    aliases = set(tgt.get('aliases', []))
    aliases.add(src['label'])
    tgt['aliases'] = list(aliases)
    merged_cids.add(src_cid)

# Redirect links
for link in links:
    if link['concept_id'] in merge_map:
        link['concept_id'] = merge_map[link['concept_id']]

concepts = [c for c in concepts if c['concept_id'] not in merged_cids]
print(f"  {len(merged_cids)} doublons BYM ALL-CAPS fusionnés")

# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PHASE 6 : Fusion des doublons sémantiques (~30 paires)")
print("=" * 70)

# Find remaining duplicate labels with same or compatible categories
label_groups = {}
for c in concepts:
    label_groups.setdefault(c['label'], []).append(c)

merge_map2 = {}
for label, group in label_groups.items():
    if len(group) < 2:
        continue
    # Sort by number of entries (keep the largest)
    group.sort(key=lambda c: len(c['entries']), reverse=True)
    target = group[0]
    for source in group[1:]:
        merge_map2[source['concept_id']] = target['concept_id']

merged2 = set()
clookup2 = {c['concept_id']: c for c in concepts}
for src_cid, tgt_cid in merge_map2.items():
    src = clookup2.get(src_cid)
    tgt = clookup2.get(tgt_cid)
    if not src or not tgt:
        continue
    existing = set(e['entry_id'] for e in tgt['entries'])
    for entry in src['entries']:
        if entry['entry_id'] not in existing:
            tgt['entries'].append(entry)
    aliases = set(tgt.get('aliases', []))
    for a in src.get('aliases', []):
        aliases.add(a)
    tgt['aliases'] = list(aliases)
    # Merge related_concepts
    existing_rc = set(r.get('concept_id','') for r in tgt.get('related_concepts',[]))
    for r in src.get('related_concepts',[]):
        if r.get('concept_id','') not in existing_rc and r.get('concept_id','') != tgt['concept_id']:
            tgt.setdefault('related_concepts',[]).append(r)
    merged2.add(src_cid)

for link in links:
    if link['concept_id'] in merge_map2:
        link['concept_id'] = merge_map2[link['concept_id']]

concepts = [c for c in concepts if c['concept_id'] not in merged2]

# Dedup links
seen = set()
deduped = []
for link in links:
    key = (link['entry_id'], link['concept_id'])
    if key not in seen:
        seen.add(key)
        deduped.append(link)

print(f"  {len(merged2)} doublons sémantiques fusionnés")

# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SAUVEGARDE")
print("=" * 70)

save("concepts.json", concepts)
save("concept-entry-links.json", deduped)
print(f"  Concepts: {len(concepts)}")
print(f"  Links: {len(deduped)}")

# Verify
cats = Counter(c['category'] for c in concepts)
print(f"\n  Catégories ({len(cats)}):")
for cat, count in cats.most_common():
    print(f"    {cat:35s} {count:5d}")

# Check orphans
valid_final = set(c['concept_id'] for c in concepts)
orphans = sum(1 for l in deduped if l['concept_id'] not in valid_final)
print(f"\n  Liens orphelins: {orphans}")

dupes = sum(1 for l, c in Counter(c2['label'] for c2 in concepts).items() if c > 1)
print(f"  Labels dupliqués restants: {dupes}")

print("\n✓ Audit corrections terminées.")

#!/usr/bin/env python3
"""
Audit C8 : Category A — concepts non_classifie avec suffixe anglais caractéristique.

Produit la liste précise des concepts dont :
- catégorie = non_classifie
- ISBE entry primaire non traduite (mot == label_fr)
- mot = single word avec suffixe EN typique : -er, -ing, -ness, -hood, -ship,
  -ment, -less, -ful, -dom, -ish, -ous, -tion, -sion, -ance, -ence

Exclut :
- Noms propres bibliques transcrits (Abacuc, Abadias, etc.)
- Labels multi-mots (traités par C3)
- Labels avec accents français
- Mots déjà connus comme français (bouclier, chandelier, etc.)

Output :
- work/audit/isbe-c8-cat-a.json
- work/audit/isbe-c8-cat-a.md
"""
import json
import re
import sys
import glob
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
DICT_DIR = ROOT / "uploads" / "dictionnaires"
AUDIT_DIR = ROOT / "work" / "audit"
OUT_JSON = AUDIT_DIR / "isbe-c8-cat-a.json"
OUT_MD = AUDIT_DIR / "isbe-c8-cat-a.md"

# Suffixes anglais forts (confidence maximale)
EN_SUFFIX_RE = re.compile(
    r'(er|ing|ness|hood|ship|ment|less|ful|dom|ish|ous|tion|sion|ance|ence)$',
    re.IGNORECASE
)

# Mots français courants avec ces suffixes : à préserver
FRENCH_SAFE = {
    'hier', 'ancier', 'bouclier', 'berger', 'boulanger', 'boucher', 'chandelier',
    'chasseur', 'courrier', 'dernier', 'étranger', 'figuier', 'guerrier',
    'herbier', 'janvier', 'lévrier', 'messager', 'métier', 'meunier',
    'oiselier', 'olivier', 'palmier', 'panier', 'papier', 'père', 'pêcher',
    'pilier', 'pommier', 'portier', 'premier', 'quartier', 'rosier', 'sauveur',
    'seuil', 'soulier', 'tailleur', 'terrier', 'tonnerre', 'vigneron', 'cahier',
    'meurtrier', 'rocher', 'sorcier', 'levier', 'acier', 'brasier', 'berger',
    'collier', 'cordonnier', 'courrier', 'cuisinier', 'écuyer', 'épicier',
    'fossoyeur', 'gardien', 'garnier', 'greffier', 'jardinier', 'laitier',
    'lieutenant', 'mendier', 'minier', 'mortier', 'notaire', 'paysan', 'pilier',
    'prisonnier', 'rentier', 'sentier', 'soldier', 'tenancier', 'trésorier',
    'usurier', 'vacancier', 'versoir', 'vivier', 'voisinage', 'voyageur',
}

# Patterns de noms propres bibliques à exclure (transliterations)
PROPER_NOUN_PATTERNS = [
    r'^[A-Z][a-z]*ian$',       # Assyrian, Ephesian, Egyptian
    r'^[A-Z][a-z]*[eir]$',     # si pattern avec consonnes particulières
]


def is_likely_proper_noun(mot):
    """Détection approximative des transliterations/noms propres."""
    # Commence par une majuscule mais contient peu de voyelles répétitives
    # Heuristic : si se termine en -ites, -ims, -iah, -ius, -us, -um, -ah, -eth, -oth
    if re.search(r'(ites|ims|iah|ius|um|eth|oth|ath|ina|ites)$', mot.lower()):
        return True
    return False


def main():
    print('Indexing ISBE chunks...')
    chunks_by_entry = {}
    for fp in sorted((DICT_DIR / 'isbe').glob('isbe-?.json')):
        with open(fp, encoding='utf-8-sig') as f:
            for e in json.load(f):
                chunks_by_entry[e['id']] = (e, fp.name)
    print(f'  {len(chunks_by_entry)} ISBE entries')

    with open(DICT_DIR / 'concepts.json', encoding='utf-8') as f:
        concepts = json.load(f)
    print(f'  {len(concepts)} concepts loaded')

    suspects = []
    for c in concepts:
        label = c.get('label', '')
        cid = c['concept_id']
        if not label or c.get('category') != 'non_classifie':
            continue

        # Multi-word : skip
        if re.search(r'[\s;,\-]', label):
            continue
        # French accents : skip
        if re.search(r'[éèàçôûêâïëÉÈÀÇÔÛÊÂÏË]', label):
            continue

        # Single word : does it match EN suffix?
        if not EN_SUFFIX_RE.search(label.lower()):
            continue

        # French safe word : skip
        if label.lower() in FRENCH_SAFE:
            continue

        # Proper noun heuristic : skip
        if is_likely_proper_noun(label):
            continue

        # Must have ISBE primary entry
        isbe_refs = [e for e in c.get('entries', []) if e.get('dictionary') == 'isbe']
        if not isbe_refs:
            continue
        primary_ref = next((e for e in isbe_refs if e.get('is_primary_for_role')), isbe_refs[0])

        entry_info = chunks_by_entry.get(primary_ref['entry_id'])
        if not entry_info:
            continue
        entry, chunk_name = entry_info

        mot = entry.get('mot', '')
        label_fr = entry.get('label_fr', '')
        if mot != label_fr:
            continue  # already translated

        # Short definition preview
        defn = entry.get('definition', '').replace('\n', ' ').strip()
        preview = defn[:180]

        suspects.append({
            'concept_id': cid,
            'label': label,
            'entry_id': primary_ref['entry_id'],
            'chunk': chunk_name,
            'mot': mot,
            'def_preview': preview,
        })

    suspects.sort(key=lambda s: s['mot'].lower())

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump({'count': len(suspects), 'items': suspects}, f, ensure_ascii=False, indent=2)

    lines = [
        f'# Audit C8 — Category A (suffixe EN caractéristique)',
        '',
        f'Total suspects : **{len(suspects)}**',
        '',
        '| mot | concept_id | entry_id | definition_preview |',
        '|---|---|---|---|',
    ]
    for s in suspects:
        prev = s['def_preview'].replace('|', '\\|')[:120]
        lines.append(f"| **{s['mot']}** | `{s['concept_id']}` | `{s['entry_id']}` | {prev} |")
    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    print()
    print(f'Suspects : {len(suspects)}')
    print(f'Output   : {OUT_JSON}')
    print()


if __name__ == '__main__':
    main()

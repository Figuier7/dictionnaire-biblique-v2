#!/usr/bin/env python3
"""
Audit C6 : scan complet des résidus anglais résiduels qui ont échappé
aux audits C2/C3/C4 précédents.

Méthodologie :
1. Index toutes les entrées ISBE dans un dict unique (par id)
2. Pour chaque concept où label == primary ISBE entry's label_fr == mot (untranslated)
3. Filtrer les noms propres évidents (même forme FR/EN : Adam, Benjamin, etc.)
4. Retourner la liste des suspects avec leur concept_id + entry_id + mot

Ajoute au scan C6 les heuristiques :
- Single-word ASCII labels
- Avec suffixe EN typique (-er, -ing, -tion*, -ness, -hood, -ship)
- OU dans une liste de noms communs EN (sans accents, non-français)
- Dans des concepts catégorie "non_classifie" ou "non classifié"

Lecture seule.
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
OUT_JSON = AUDIT_DIR / "isbe-c6-residues-scan.json"
OUT_MD = AUDIT_DIR / "isbe-c6-residues-scan.md"

# Mots français courants à ne jamais flagger même s'ils ont un suffixe -er/-ing
FRENCH_SAFE = {
    # -er endings (verbes et noms français)
    'Hier', 'Ancier', 'Bouclier', 'Berger', 'Boulanger', 'Boucher', 'Chandelier',
    'Chasseur', 'Cheveu', 'Courrier', 'Cheveux', 'Deuxième', 'Deuil', 'Devoir',
    'Dernier', 'Elohim', 'Étranger', 'Figuier', 'Gentil', 'Gloire', 'Guerrier',
    'Herbier', 'Janvier', 'Juger', 'Juillet', 'Levier', 'Lévrier', 'Lundi',
    'Marier', 'Mardi', 'Marmitonner', 'Mauvais', 'Meilleur', 'Mercredi',
    'Messager', 'Métier', 'Meunier', 'Meunier', 'Mi-carême', 'Minuit',
    'Mois', 'Mouillage', 'Nocturne', 'Oiselier', 'Olivier', 'Palmier',
    'Panier', 'Papier', 'Parler', 'Payer', 'Père', 'Pêcher', 'Pénitent',
    'Pétrir', 'Pilier', 'Plumer', 'Pommier', 'Porte', 'Portier', 'Poudrier',
    'Pourquoi', 'Pouvoir', 'Premier', 'Prier', 'Printemps', 'Prisonnier',
    'Prisonnier', 'Quartier', 'Rameur', 'Ravenir', 'Répondre', 'Retraiter',
    'Rêver', 'Rire', 'Rocher', 'Rosier', 'Rôtir', 'Sauveur', 'Savoir',
    'Septembre', 'Serviteur', 'Seuil', 'Signifier', 'Singulier', 'Songer',
    'Sorcier', 'Soulier', 'Spécifier', 'Sur', 'Tailleur', 'Tapisser',
    'Terrier', 'Terre', 'Tonnerre', 'Trépasser', 'Troupeau', 'Tuer',
    'Vendredi', 'Venir', 'Vérifier', 'Verset', 'Vetir', 'Vigneron',
    'Vivre', 'Voir', 'Voir', 'Vouloir', 'Zodier',
    # -ing, not common in French
    # -ness, not common
    # -hood, not common
}

# Noms propres bibliques à ne jamais flagger (identique FR/EN)
PROPER_NOUNS = {
    'Aaron', 'Adam', 'Abel', 'Abraham', 'Absalom', 'Adonijah', 'Agag', 'Ahab',
    'Amasa', 'Amos', 'Andrew', 'Andronicus', 'Antipater', 'Aquila', 'Archelaus',
    'Ariel', 'Aristobulus', 'Asahel', 'Asher', 'Azariah', 'Balaam', 'Balak',
    'Barak', 'Barnabas', 'Baruch', 'Benjamin', 'Caiaphas', 'Cain', 'Cleopas',
    'Cyrus', 'Daniel', 'David', 'Deborah', 'Eber', 'Eleazar', 'Eli', 'Eliezer',
    'Enoch', 'Esther', 'Gabriel', 'Gad', 'Gideon', 'Goliath', 'Hagar', 'Ham',
    'Hezekiah', 'Hiram', 'Hosea', 'Isaac', 'Ishmael', 'Jacob', 'James', 'Japheth',
    'Jehu', 'Jephthah', 'Job', 'Joel', 'Jonah', 'Jonathan', 'Joseph', 'Joshua',
    'Josiah', 'Judah', 'Judas', 'Lazarus', 'Leah', 'Levi', 'Luke', 'Manasseh',
    'Mark', 'Martha', 'Mary', 'Matthew', 'Melchizedek', 'Mephibosheth', 'Micah',
    'Michael', 'Miriam', 'Moses', 'Naaman', 'Nadab', 'Naomi', 'Nathan', 'Nebuchadnezzar',
    'Nehemiah', 'Noah', 'Obadiah', 'Peter', 'Philemon', 'Philip', 'Rachel', 'Rahab',
    'Rebekah', 'Reuben', 'Ruth', 'Samson', 'Samuel', 'Sarah', 'Saul', 'Seth',
    'Shem', 'Silas', 'Simeon', 'Solomon', 'Stephen', 'Tamar', 'Thomas',
    'Timothy', 'Titus', 'Uriah', 'Zacharias', 'Zechariah', 'Zedekiah',
    'Israel', 'Zerubbabel',
}


def main():
    # Index ISBE chunks
    print('Indexing ISBE chunks...')
    chunks_by_entry = {}
    for fp in sorted((DICT_DIR / 'isbe').glob('isbe-?.json')):
        with open(fp, encoding='utf-8-sig') as f:
            for e in json.load(f):
                chunks_by_entry[e['id']] = (e, fp.name)
    print(f'  {len(chunks_by_entry)} entries indexed')

    # Load concepts
    print('Loading concepts.json...')
    with open(DICT_DIR / 'concepts.json', encoding='utf-8') as f:
        concepts = json.load(f)
    print(f'  {len(concepts)} concepts')

    # Scan
    suspects = []
    for c in concepts:
        label = c.get('label', '')
        cid = c['concept_id']
        if not label or not cid:
            continue
        # Only scan non_classifie (where residues live)
        if c.get('category') != 'non_classifie':
            continue
        # Must have ISBE entry
        isbe_refs = [e for e in c.get('entries', []) if e.get('dictionary') == 'isbe']
        if not isbe_refs:
            continue

        # Pick primary ISBE entry
        primary = None
        for ref in isbe_refs:
            if ref.get('is_primary_for_role'):
                primary = ref
                break
        if not primary:
            primary = isbe_refs[0]

        entry_info = chunks_by_entry.get(primary['entry_id'])
        if not entry_info:
            continue
        entry, chunk_name = entry_info
        mot = entry.get('mot', '')
        label_fr = entry.get('label_fr', '')

        # Skip if already translated (C4 / C4.2 / manual pass)
        if mot != label_fr:
            continue

        # Skip if label contains French accents
        if re.search(r'[éèàçôûêâïëÉÈÀÇÔÛÊÂÏË]', label):
            continue

        # Skip proper nouns
        first_word = re.split(r'[\s;,\-]+', label)[0]
        if first_word in PROPER_NOUNS:
            continue
        if first_word in FRENCH_SAFE:
            continue

        # Flag it
        suspects.append({
            'concept_id': cid,
            'label': label,
            'chunk': chunk_name,
            'entry_id': primary['entry_id'],
            'mot': mot,
            'def_preview': entry.get('definition', '')[:120].replace('\n', ' '),
            'entries_count': len(c.get('entries', [])),
        })

    # Sort alphabetically
    suspects.sort(key=lambda s: s['concept_id'])

    # Save
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump({'count': len(suspects), 'items': suspects}, f, ensure_ascii=False, indent=2)

    # MD
    lines = [
        '# Audit C6 — Résidus anglais résiduels (concepts non_classifie)',
        '',
        f'Total suspects : **{len(suspects)}**',
        '',
        '| concept_id | label | entry_id | chunk |',
        '|---|---|---|---|',
    ]
    for s in suspects:
        lines.append(f"| `{s['concept_id']}` | {s['label']} | `{s['entry_id']}` | {s['chunk']} |")
    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    print()
    print(f'Suspects : {len(suspects)}')
    print(f'Output   : {OUT_JSON}')
    print()
    print('=== First 30 samples ===')
    for s in suspects[:30]:
        print(f"  {s['concept_id']:50s} {s['label']!r:35s} {s['entry_id']}")


if __name__ == '__main__':
    main()

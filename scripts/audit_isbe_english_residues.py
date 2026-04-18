#!/usr/bin/env python3
"""
Audit read-only des résidus anglais dans le dictionnaire concepts + chunks ISBE.

Produit deux fichiers dans work/audit/ :
  - isbe-residues-report.md   (rapport lisible pour arbitrage éditorial)
  - isbe-residues-report.json (données structurées par cluster)

Aucune modification d'aucun fichier source. Lecture pure.

Clusters analysés :
  C1. Labels de concepts avec mots fonctionnels anglais non traduits (Of/The/And/...)
  C2. Labels de concepts en un seul mot anglais (heuristique : ASCII pur + sources ISBE)
  C3. Labels de concepts mixtes FR/EN (contiennent un mot anglais connu isolé)
  C4. Entrées ISBE chunks dont le `mot` est anglais mais la définition est FR
  C5. Doublons potentiels FR/EN (concept anglais stub + concept français riche)
"""
import json
import glob
import os
import re
import sys
import unicodedata
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
CONCEPTS_PATH = ROOT / "uploads" / "dictionnaires" / "concepts.json"
ISBE_CHUNKS_GLOB = str(ROOT / "uploads" / "dictionnaires" / "isbe" / "isbe-*.json")
OUT_DIR = ROOT / "work" / "audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Pattern des mots fonctionnels anglais (même pattern que fix_isbe_concept_labels.py)
EN_FUNCTION_WORDS = re.compile(
    r'\b(?:Of|The|And|In|For|To|At|By|On|Or|With|From|As|Between|Through|'
    r'Under|Upon|Into|Before|After|Against|Among|Without)\b'
)

# Liste curée de mots anglais à flaguer s'ils apparaissent isolés dans un label
EN_KEYWORDS_RESIDUAL = {
    # Personnes/rôles
    'Elder', 'Elders', 'Priest', 'Priests', 'Stranger', 'Sojourner',
    'Widow', 'Widows', 'Husband', 'Wife', 'Slave', 'Servant',
    # Actions/événements
    'Decease', 'Divorce', 'Marriage', 'Birth', 'Death', 'Burial',
    'Arrest', 'Trial', 'Judgment', 'Sacrifice',
    # Objets
    'Manuscripts', 'Languages', 'Scriptures', 'Books', 'Letters',
    'Gate', 'Gates', 'Well', 'Wells', 'Rock', 'Stone', 'Stones',
    'Altar', 'Altars', 'Offering', 'Offerings',
    # Temps/ancienneté
    'Ancient', 'Ancients', 'Old', 'New', 'Young',
    # Lieux génériques
    'City', 'Cities', 'Land', 'Lands', 'Mountain', 'Mountains',
    'Valley', 'River', 'Sea', 'Desert', 'Wilderness',
    # Abstractions
    'Covenant', 'Kingdom', 'Righteousness', 'Holiness', 'Wickedness',
    'Wisdom', 'Knowledge', 'Understanding',
    # Petits mots
    'Against', 'Before', 'After', 'With', 'Without', 'Among',
    'Apocrypha', 'Apocyphra',  # + typo observée
    # Divers
    'Field', 'Fields', 'Battle', 'Bow', 'Shield', 'Sword',
    'Feast', 'Feasts', 'Law', 'Laws', 'Prophet', 'Prophets',
    'Angel', 'Angels', 'Demon', 'Demons',
    'Bird', 'Birds', 'Beast', 'Beasts',
    'Prayer', 'Prayers', 'Vow', 'Vows', 'Fast', 'Fasts',
    'Sin', 'Sins', 'Grace', 'Mercy', 'Hope', 'Faith', 'Love',
    'Church', 'Churches', 'Synagogue', 'Temple',
}

# Mots identiques/compatibles FR/EN à ne PAS flaguer (faux positifs)
SAFE_WORDS = {
    'Adam', 'Eve', 'Moab', 'Sinai', 'Baal', 'Amen', 'Zion',
    'Israel', 'David', 'Paul', 'Jean', 'Marc', 'Luc', 'Pierre',
    'Aaron', 'Abel', 'Noah', 'Nimrod', 'Goliath', 'Ruth', 'Esther',
    'Job', 'Daniel', 'Jonas', 'Tobit', 'Baruch', 'Nahum', 'Hosea',
    'Amos', 'Micah', 'Joel', 'Enoch',
    # Noms géographiques communs aux deux langues
    'Jerusalem', 'Nazareth', 'Bethlehem', 'Damas', 'Corinth',
    # Transliterations
    'Shaddai', 'Torah', 'Tanakh', 'Yhwh', 'Elohim', 'Mashiah',
}

# Patterns qui indiquent une structure anglaise "X in the Y" ou "X of the Y"
MIXED_STRUCTURE_PATTERNS = [
    re.compile(r'\bdans\s+Ancien\b'),     # "Elder dans Ancien" (manque l')
    re.compile(r'\bdans\s+Nouveau\b'),    # "X dans Nouveau" (manque le)
    re.compile(r'\bde\s+Ancien\b'),       # "Languages de Ancien"
    re.compile(r'\bde\s+Nouveau\b'),
]


def strip_accents(s: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )


def get_sources(concept):
    return sorted({e.get('dictionary', '') for e in concept.get('entries', [])})


def is_ascii_only(s: str) -> bool:
    return all(ord(c) < 128 for c in s)


def main():
    # -- Load data --
    with open(CONCEPTS_PATH, 'r', encoding='utf-8-sig') as f:
        concepts = json.load(f)
    print(f"Loaded {len(concepts)} concepts from concepts.json")

    isbe_entries_by_id = {}
    for path in sorted(glob.glob(ISBE_CHUNKS_GLOB)):
        with open(path, 'r', encoding='utf-8-sig') as f:
            entries = json.load(f)
        for e in entries:
            isbe_entries_by_id[e.get('id', '')] = {
                'mot': e.get('mot', ''),
                'definition': e.get('definition', ''),
                'chunk': os.path.basename(path),
            }
    print(f"Loaded {len(isbe_entries_by_id)} ISBE chunk entries")

    # Index concepts by normalized label for C5
    concepts_by_normalized_label = defaultdict(list)
    for c in concepts:
        label = c.get('label', '')
        norm = strip_accents(label).lower().strip()
        if norm:
            concepts_by_normalized_label[norm].append(c)

    # -- C1 : mots fonctionnels anglais dans le label --
    c1 = []
    for c in concepts:
        label = c.get('label', '')
        if EN_FUNCTION_WORDS.search(label):
            c1.append({
                'concept_id': c.get('concept_id', ''),
                'label': label,
                'category': c.get('category', ''),
                'sources': get_sources(c),
                'entries_count': len(c.get('entries', [])),
            })

    # -- C2 : labels single-word ASCII potentiellement anglais --
    c2 = []
    for c in concepts:
        label = c.get('label', '').strip()
        if not label or ' ' in label or '-' in label or ',' in label:
            continue
        if label in SAFE_WORDS:
            continue
        if not is_ascii_only(label):
            continue
        # Label ASCII pur sans espace, sources contiennent ISBE
        sources = get_sources(c)
        if 'isbe' not in sources:
            continue
        # Exclure les labels qui commencent par une minuscule (probablement des slugs bruts)
        if not label[0].isupper():
            continue
        # Exclure les labels avec chiffres
        if any(ch.isdigit() for ch in label):
            continue
        c2.append({
            'concept_id': c.get('concept_id', ''),
            'label': label,
            'category': c.get('category', ''),
            'sources': sources,
            'entries_count': len(c.get('entries', [])),
            'flagged_by_keyword': label in EN_KEYWORDS_RESIDUAL,
        })

    # -- C3 : labels mixtes (structure FR cassée) --
    c3 = []
    for c in concepts:
        label = c.get('label', '')
        matched_patterns = []
        for p in MIXED_STRUCTURE_PATTERNS:
            if p.search(label):
                matched_patterns.append(p.pattern)
        # Aussi : label contient un mot-clé anglais de EN_KEYWORDS_RESIDUAL isolé
        label_words = re.findall(r'\b[A-Za-z]+\b', label)
        isolated_en = [w for w in label_words if w in EN_KEYWORDS_RESIDUAL and w not in SAFE_WORDS]
        if matched_patterns or (isolated_en and ' ' in label):
            c3.append({
                'concept_id': c.get('concept_id', ''),
                'label': label,
                'category': c.get('category', ''),
                'sources': get_sources(c),
                'matched_patterns': matched_patterns,
                'isolated_english_words': isolated_en,
            })

    # -- C4 : entrées ISBE chunks dont le mot est anglais malgré définition FR --
    # Heuristique : le mot contient un marqueur fonctionnel EN OU est dans EN_KEYWORDS_RESIDUAL
    # ET la définition contient des caractères français (é, è, à, ç, etc.) ou des mots FR typiques
    FR_MARKERS = re.compile(r'[éèêàâçôûîïëü]|(?:\b(?:le|la|les|des|du|qui|que|dans|pour|avec|sans|sont|est)\b)', re.IGNORECASE)
    c4 = []
    for eid, entry in sorted(isbe_entries_by_id.items()):
        mot = entry['mot']
        defn = entry['definition']
        if not mot or not defn:
            continue
        mot_has_en = bool(EN_FUNCTION_WORDS.search(mot)) or mot in EN_KEYWORDS_RESIDUAL
        if mot in SAFE_WORDS:
            continue
        # Single-word ASCII pur en plus
        mot_is_single_en = (
            ' ' not in mot
            and is_ascii_only(mot)
            and mot[:1].isupper()
            and not any(ch.isdigit() for ch in mot)
            and mot not in SAFE_WORDS
        )
        if not (mot_has_en or mot_is_single_en):
            continue
        # La définition doit contenir des marqueurs FR pour que ce soit un "résidu FR-traduit-mot-non-traduit"
        if not FR_MARKERS.search(defn):
            continue
        c4.append({
            'entry_id': eid,
            'mot': mot,
            'chunk': entry['chunk'],
            'def_preview': defn[:140].replace('\n', ' '),
            'def_len': len(defn),
            'matched_as': 'function_word' if mot_has_en else 'single_en_keyword',
        })

    # -- C5 : doublons potentiels FR/EN --
    # Heuristique : pour chaque concept label en EN (C1 ou C2), chercher si un concept FR existe
    # avec un label "proche" (stripping accents, minuscules, suffixes).
    SUFFIX_RULES = [
        ('s', ''),   # pluriel EN vs singulier FR possible
        ('', 's'),   # inverse
        ('', 'e'),   # "ancient" → "anciene"? pas vraiment
        ('t', ''),   # "ancient" → "ancien"
        ('ts', 's'), # "ancients" → "anciens"
    ]
    c5 = []
    en_concepts = [x for x in c1] + [x for x in c2]
    # Dédoublonne par concept_id
    seen_ids = set()
    for item in en_concepts:
        cid = item['concept_id']
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        label = item['label']
        norm_label = strip_accents(label).lower().strip()
        # Générer candidats FR
        candidates = set()
        for suf_en, suf_fr in SUFFIX_RULES:
            if norm_label.endswith(suf_en) and suf_en != '':
                base = norm_label[:-len(suf_en)]
                candidates.add(base + suf_fr)
            elif suf_en == '':
                candidates.add(norm_label + suf_fr)
        candidates.discard(norm_label)
        # Chercher matches
        matches = []
        for cand in candidates:
            if cand in concepts_by_normalized_label:
                for fr_concept in concepts_by_normalized_label[cand]:
                    if fr_concept.get('concept_id') != cid:
                        matches.append({
                            'fr_concept_id': fr_concept.get('concept_id', ''),
                            'fr_label': fr_concept.get('label', ''),
                            'fr_category': fr_concept.get('category', ''),
                            'fr_sources': get_sources(fr_concept),
                        })
        if matches:
            c5.append({
                'en_concept_id': cid,
                'en_label': label,
                'en_category': item.get('category', ''),
                'en_sources': item.get('sources', []),
                'fr_matches': matches,
            })

    # -- Output JSON --
    report = {
        'generated_at_root': str(ROOT),
        'concepts_total': len(concepts),
        'isbe_entries_total': len(isbe_entries_by_id),
        'clusters': {
            'C1_function_words_in_label': {
                'description': 'Labels de concepts contenant des mots fonctionnels anglais (Of/The/And/...)',
                'count': len(c1),
                'items': c1,
            },
            'C2_single_word_english_labels': {
                'description': 'Labels single-word en ASCII pur avec source ISBE (potentiellement anglais)',
                'count': len(c2),
                'items': c2,
            },
            'C3_mixed_fr_en_labels': {
                'description': 'Labels FR avec structure cassée ou mot anglais isolé',
                'count': len(c3),
                'items': c3,
            },
            'C4_isbe_chunk_mot_residues': {
                'description': 'Entrées ISBE chunks dont le champ mot est anglais malgré définition FR',
                'count': len(c4),
                'items': c4,
            },
            'C5_fr_en_potential_duplicates': {
                'description': 'Doublons potentiels concept EN stub + concept FR riche',
                'count': len(c5),
                'items': c5,
            },
        },
    }
    out_json = OUT_DIR / 'isbe-residues-report.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # -- Output Markdown --
    lines = []
    lines.append('# Audit des résidus anglais ISBE dans le dictionnaire')
    lines.append('')
    lines.append(f'- Concepts totaux : **{len(concepts)}**')
    lines.append(f'- Entrées ISBE chunks : **{len(isbe_entries_by_id)}**')
    lines.append('')
    lines.append('## Résumé par cluster')
    lines.append('')
    lines.append('| Cluster | Description | Count |')
    lines.append('|---|---|---:|')
    lines.append(f'| C1 | Labels avec mots fonctionnels anglais (Of/The/And/...) | **{len(c1)}** |')
    lines.append(f'| C2 | Labels single-word ASCII avec source ISBE | **{len(c2)}** |')
    lines.append(f'| C3 | Labels mixtes FR/EN (structure cassée ou mot EN isolé) | **{len(c3)}** |')
    lines.append(f'| C4 | Entrées ISBE chunks avec `mot` EN et définition FR | **{len(c4)}** |')
    lines.append(f'| C5 | Doublons potentiels concept EN stub + FR riche | **{len(c5)}** |')
    lines.append('')

    def emit_cluster(title, items, sample_n=20, fmt=None):
        lines.append(f'## {title}')
        lines.append('')
        lines.append(f'Total : **{len(items)}** — échantillon des {min(sample_n, len(items))} premiers :')
        lines.append('')
        if fmt:
            fmt(items[:sample_n])
        lines.append('')
        if len(items) > sample_n:
            lines.append(f'*(... {len(items) - sample_n} autres dans le JSON)*')
            lines.append('')

    def fmt_c1(items):
        lines.append('| concept_id | label | cat | sources |')
        lines.append('|---|---|---|---|')
        for it in items:
            srcs = ','.join(it['sources'])
            lines.append(f"| `{it['concept_id']}` | {it['label']} | {it['category']} | {srcs} |")

    def fmt_c2(items):
        lines.append('| concept_id | label | cat | sources | keyword? |')
        lines.append('|---|---|---|---|---|')
        for it in items:
            srcs = ','.join(it['sources'])
            kw = 'OUI' if it['flagged_by_keyword'] else ''
            lines.append(f"| `{it['concept_id']}` | **{it['label']}** | {it['category']} | {srcs} | {kw} |")

    def fmt_c3(items):
        lines.append('| concept_id | label | cat | motifs/mots EN |')
        lines.append('|---|---|---|---|')
        for it in items:
            pats = '; '.join(it['matched_patterns']) if it['matched_patterns'] else ''
            iso = ','.join(it['isolated_english_words']) if it['isolated_english_words'] else ''
            badges = (pats + ' ' + iso).strip()
            lines.append(f"| `{it['concept_id']}` | {it['label']} | {it['category']} | {badges} |")

    def fmt_c4(items):
        lines.append('| entry_id | chunk | mot | def_preview |')
        lines.append('|---|---|---|---|')
        for it in items:
            preview = it['def_preview'].replace('|', '\\|')
            lines.append(f"| `{it['entry_id']}` | {it['chunk']} | **{it['mot']}** | {preview} |")

    def fmt_c5(items):
        for it in items:
            lines.append(f"- **{it['en_label']}** (`{it['en_concept_id']}`, cat={it['en_category']}, src={','.join(it['en_sources'])})")
            for m in it['fr_matches']:
                lines.append(f"    → **{m['fr_label']}** (`{m['fr_concept_id']}`, cat={m['fr_category']}, src={','.join(m['fr_sources'])})")

    emit_cluster('C1 — Labels avec mots fonctionnels anglais', c1, 30, fmt_c1)
    emit_cluster('C2 — Labels single-word ASCII avec source ISBE', c2, 40, fmt_c2)
    emit_cluster('C3 — Labels mixtes FR/EN', c3, 30, fmt_c3)
    emit_cluster('C4 — Entrées ISBE chunks avec mot anglais résiduel', c4, 30, fmt_c4)
    emit_cluster('C5 — Doublons potentiels EN stub / FR riche', c5, 20, fmt_c5)

    out_md = OUT_DIR / 'isbe-residues-report.md'
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    print()
    print(f'Rapport JSON : {out_json}')
    print(f'Rapport MD   : {out_md}')
    print()
    print('=== Résumé ===')
    print(f'C1 (function words)      : {len(c1)}')
    print(f'C2 (single-word ASCII)   : {len(c2)}')
    print(f'C3 (mixed FR/EN)         : {len(c3)}')
    print(f'C4 (chunk mot residues)  : {len(c4)}')
    print(f'C5 (FR/EN duplicates)    : {len(c5)}')


if __name__ == '__main__':
    main()

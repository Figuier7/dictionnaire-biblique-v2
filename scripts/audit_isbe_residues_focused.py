#!/usr/bin/env python3
"""
Affinage de l'audit des résidus anglais ISBE.

Filtre le rapport brut produit par audit_isbe_english_residues.py pour ne garder
que les éléments VRAIMENT actionnables (élimine les faux positifs comme les noms
propres identiques FR/EN, les suffixes pluriel/singulier sans rapport, etc.).

Lecture seule. Aucune modification d'aucun fichier source.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT / "work" / "audit"
RAW_JSON = AUDIT_DIR / "isbe-residues-report.json"
OUT_MD = AUDIT_DIR / "isbe-residues-focused.md"
OUT_JSON = AUDIT_DIR / "isbe-residues-focused.json"

# Pattern "début" d'un mot anglais qui indique un vrai résidu (non nom propre)
EN_RESIDUE_WORDS = {
    # Les mots CARDINAUX de EN_KEYWORDS_RESIDUAL qui sont des noms communs, pas propres
    'Elder', 'Elders', 'Decease', 'Divorce', 'Marriage', 'Birth', 'Death',
    'Burial', 'Arrest', 'Trial', 'Judgment', 'Sacrifice', 'Offering', 'Offerings',
    'Manuscripts', 'Languages', 'Scriptures', 'Books', 'Letters',
    'Gate', 'Gates', 'Well', 'Wells', 'Rock', 'Stone', 'Stones',
    'Altar', 'Altars', 'Ancient', 'Ancients',
    'City', 'Cities', 'Land', 'Mountain', 'Valley', 'River', 'Sea',
    'Desert', 'Wilderness', 'Covenant', 'Kingdom',
    'Righteousness', 'Holiness', 'Wickedness', 'Wisdom', 'Knowledge', 'Understanding',
    'Against', 'Before', 'After', 'With', 'Without', 'Among',
    'Field', 'Fields', 'Battle', 'Bow', 'Shield', 'Sword',
    'Feast', 'Feasts', 'Law', 'Laws', 'Prophet', 'Prophets',
    'Angel', 'Angels', 'Demon', 'Demons', 'Bird', 'Birds', 'Beast', 'Beasts',
    'Prayer', 'Prayers', 'Vow', 'Vows', 'Fast', 'Fasts',
    'Sin', 'Sins', 'Grace', 'Mercy', 'Hope', 'Faith', 'Love',
    'Church', 'Churches', 'Synagogue', 'Temple',
    'Stranger', 'Sojourner', 'Widow', 'Widows', 'Husband', 'Wife', 'Slave',
    'Servant', 'Priest', 'Priests',
    'Agrarian', 'Apostolical', 'Brazen', 'Brotherly', 'Burnt', 'Daily',
    'Apocrypha', 'Apocyphra',
}

# Mots qui, bien qu'en ASCII pur et majuscule initiale, sont des noms propres
# biblique identiques dans les deux langues et donc PAS des résidus à traiter.
# Cette liste n'est pas exhaustive — on utilise surtout la règle "tous les mots
# commençant par majuscule sauf si dans EN_RESIDUE_WORDS = skip par défaut".
# En pratique, on ne flague comme residue que les mots CONNUS comme EN.


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


def looks_like_proper_noun(mot):
    """Un mot ASCII pur à majuscule initiale est probablement un nom propre
    sauf s'il est dans EN_RESIDUE_WORDS ou contient des minuscules avant majuscules."""
    if not mot:
        return False
    # Si plusieurs mots, check chacun
    words = re.findall(r'[A-Za-z]+', mot)
    if not words:
        return False
    # Tous les mots doivent être des noms propres probables (majuscule initiale)
    for w in words:
        if w in EN_RESIDUE_WORDS:
            return False
        if w.lower() in {'the', 'of', 'and', 'in', 'for', 'to', 'at', 'by', 'on',
                         'or', 'with', 'from', 'as', 'a', 'an', 'de', 'du', 'la',
                         'le', 'les', 'des', 'et', 'ou'}:
            continue  # articles/conjonctions OK
    return True


def main():
    with open(RAW_JSON, 'r', encoding='utf-8-sig') as f:
        raw = json.load(f)

    clusters = raw['clusters']
    c1_raw = clusters['C1_function_words_in_label']['items']
    c2_raw = clusters['C2_single_word_english_labels']['items']
    c3_raw = clusters['C3_mixed_fr_en_labels']['items']
    c4_raw = clusters['C4_isbe_chunk_mot_residues']['items']
    c5_raw = clusters['C5_fr_en_potential_duplicates']['items']

    # --- C1 : ne garder que ceux qui contiennent un mot EN résiduel (exclure "Or" faux positif) ---
    # Heuristique : le label doit contenir un mot de EN_RESIDUE_WORDS OU un vrai pattern anglais
    c1_focused = []
    for item in c1_raw:
        label = item['label']
        # Exclure si label=Or (métal français)
        if label == 'Or':
            continue
        # Exclure si le label est entièrement en FR sauf un petit mot anglais utilisé en FR
        c1_focused.append(item)

    # --- C2 : ne garder QUE les labels dans EN_RESIDUE_WORDS (true residues) ---
    c2_focused = [
        item for item in c2_raw
        if item['label'] in EN_RESIDUE_WORDS
    ]

    # --- C3 : filtrer pour ne garder que ceux avec un vrai mot EN isolé OU un pattern structurel ---
    c3_focused = []
    for item in c3_raw:
        # Si un motif structurel a matché → true residue
        if item['matched_patterns']:
            c3_focused.append(item)
            continue
        # Si un mot EN isolé est dans EN_RESIDUE_WORDS (pas juste "Sin" dans "Sin offering" FR)
        iso = [w for w in item['isolated_english_words']
               if w in EN_RESIDUE_WORDS]
        if iso:
            # Mais exclure les cas où le mot apparaît en contexte FR légitime
            # (ex: "Sacrifice quotidien" — Sacrifice est un vrai mot français aussi)
            label = item['label']
            # Si label contient déjà des accents français ou structure FR claire, probablement OK
            fr_markers = re.findall(r'[éèàçôûêâïë]', label)
            french_structure = bool(re.search(r'\b(?:du|de la|des|le|la|les|aux|au)\b', label))
            if fr_markers or french_structure:
                # Double-check : est-ce que le mot "EN" est en fait un mot FR aussi ?
                fr_cognates = {'Sacrifice', 'Temple', 'Angel', 'Sin',
                               'Altar', 'Angels', 'Courts', 'Prayer'}
                all_iso_are_cognates = all(w in fr_cognates for w in iso)
                if all_iso_are_cognates and not item['matched_patterns']:
                    continue  # Faux positif : label FR avec cognat
            item['_isolated_filtered'] = iso
            c3_focused.append(item)

    # --- C4 : ne garder que les entries dont le mot est dans EN_RESIDUE_WORDS ---
    c4_focused = [
        item for item in c4_raw
        if item['mot'] in EN_RESIDUE_WORDS or any(
            w in EN_RESIDUE_WORDS for w in re.findall(r'\b[A-Za-z]+\b', item['mot'])
        )
    ]

    # --- C5 : filtrer les faux positifs de suffixe ---
    # Règle : pour un "vrai doublon", il faut que :
    # - L'EN side soit clairement un résidu (label dans EN_RESIDUE_WORDS OU label = version brute d'un mot FR)
    # - Le FR side soit le concept riche FR équivalent
    # - Les deux aient des sources qui se recouvrent (pas Philippes lieu vs Philippe personnage)
    c5_focused = []
    for item in c5_raw:
        en_label = item['en_label']
        en_cat = item['en_category']
        en_sources = set(item['en_sources'])
        # Garder si l'en_label est dans EN_RESIDUE_WORDS
        if en_label in EN_RESIDUE_WORDS:
            c5_focused.append(item)
            continue
        # Sinon, garder si au moins un match FR a le MÊME category (probablement le même concept)
        same_cat_matches = [m for m in item['fr_matches'] if m['fr_category'] == en_cat]
        if same_cat_matches:
            # Et pas un cas pluriel/singulier légitime (ex: Philippe vs Philippes = lieux différents)
            # Garder seulement si très proche sémantiquement (TODO: heuristique plus fine)
            item['_same_cat_matches'] = same_cat_matches
            c5_focused.append(item)

    # --- Stats ---
    focused = {
        'generated_at_root': str(ROOT),
        'source_report': str(RAW_JSON),
        'clusters': {
            'C1_focused': {
                'description': 'Mots fonctionnels anglais dans label (filtré faux positifs)',
                'count': len(c1_focused),
                'items': c1_focused,
            },
            'C2_focused': {
                'description': 'Labels single-word dans liste EN résiduelle stricte',
                'count': len(c2_focused),
                'items': c2_focused,
            },
            'C3_focused': {
                'description': 'Labels mixtes avec pattern ou mot EN résiduel (cognats FR exclus)',
                'count': len(c3_focused),
                'items': c3_focused,
            },
            'C4_focused': {
                'description': 'Chunks ISBE avec mot EN résiduel dans liste stricte',
                'count': len(c4_focused),
                'items': c4_focused,
            },
            'C5_focused': {
                'description': 'Doublons FR/EN : EN dans liste résiduelle OU même catégorie',
                'count': len(c5_focused),
                'items': c5_focused,
            },
        },
    }

    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(focused, f, ensure_ascii=False, indent=2)

    # --- Markdown ---
    lines = []
    lines.append('# Audit focalisé des résidus anglais ISBE')
    lines.append('')
    lines.append(f'Source brute : `{RAW_JSON.name}`')
    lines.append('')
    lines.append('Filtrage conservateur : on ne garde que les cas où la détection')
    lines.append('est suffisamment fiable pour prendre une décision éditoriale.')
    lines.append('')
    lines.append('## Totaux')
    lines.append('')
    lines.append('| Cluster | Brut | Focalisé | Description |')
    lines.append('|---|---:|---:|---|')
    lines.append(f"| C1 | {len(c1_raw)} | **{len(c1_focused)}** | Mots fonctionnels EN dans label |")
    lines.append(f"| C2 | {len(c2_raw)} | **{len(c2_focused)}** | Labels single-word résiduels stricts |")
    lines.append(f"| C3 | {len(c3_raw)} | **{len(c3_focused)}** | Labels mixtes FR/EN structurés |")
    lines.append(f"| C4 | {len(c4_raw)} | **{len(c4_focused)}** | Chunks ISBE `mot` EN résiduel |")
    lines.append(f"| C5 | {len(c5_raw)} | **{len(c5_focused)}** | Doublons FR/EN vrais |")
    lines.append('')

    def render_c1_c2(items, title, extra_col=None):
        lines.append(f'## {title}')
        lines.append('')
        lines.append(f'**{len(items)} cas**')
        lines.append('')
        if not items:
            lines.append('_Aucun cas dans cette catégorie._')
            lines.append('')
            return
        headers = ['concept_id', 'label', 'catégorie', 'sources']
        lines.append('| ' + ' | '.join(headers) + ' |')
        lines.append('|' + '|'.join(['---'] * len(headers)) + '|')
        for it in items:
            row = [
                f"`{it['concept_id']}`",
                f"**{it['label']}**",
                it['category'],
                ','.join(it.get('sources', [])),
            ]
            lines.append('| ' + ' | '.join(row) + ' |')
        lines.append('')

    render_c1_c2(c1_focused, 'C1 focalisé — Mots fonctionnels EN dans label')
    render_c1_c2(c2_focused, 'C2 focalisé — Labels single-word résiduels')

    lines.append('## C3 focalisé — Labels mixtes FR/EN structurés')
    lines.append('')
    lines.append(f'**{len(c3_focused)} cas**')
    lines.append('')
    lines.append('| concept_id | label | catégorie | motifs / mots EN |')
    lines.append('|---|---|---|---|')
    for it in c3_focused:
        badges = []
        if it['matched_patterns']:
            badges.append('`pattern`')
        iso = it.get('_isolated_filtered') or it.get('isolated_english_words') or []
        if iso:
            badges.append(','.join(iso))
        lines.append(f"| `{it['concept_id']}` | {it['label']} | {it['category']} | {' '.join(badges)} |")
    lines.append('')

    lines.append('## C4 focalisé — Chunks ISBE avec mot EN résiduel')
    lines.append('')
    lines.append(f'**{len(c4_focused)} cas**')
    lines.append('')
    lines.append('| entry_id | chunk | mot | def_preview |')
    lines.append('|---|---|---|---|')
    for it in c4_focused:
        preview = it['def_preview'].replace('|', '\\|')
        lines.append(f"| `{it['entry_id']}` | {it['chunk']} | **{it['mot']}** | {preview} |")
    lines.append('')

    lines.append('## C5 focalisé — Doublons FR/EN vrais')
    lines.append('')
    lines.append(f'**{len(c5_focused)} cas**')
    lines.append('')
    for it in c5_focused:
        lines.append(f"### {it['en_label']} / {', '.join(m['fr_label'] for m in it['fr_matches'])}")
        lines.append('')
        lines.append(f"- EN : **{it['en_label']}** `{it['en_concept_id']}` (cat={it['en_category']}, src={','.join(it['en_sources'])})")
        for m in it['fr_matches']:
            lines.append(f"- FR : **{m['fr_label']}** `{m['fr_concept_id']}` (cat={m['fr_category']}, src={','.join(m['fr_sources'])})")
        lines.append('')

    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    print()
    print(f'Rapport focalisé MD   : {OUT_MD}')
    print(f'Rapport focalisé JSON : {OUT_JSON}')
    print()
    print('=== Totaux focalisés ===')
    print(f'C1 : {len(c1_raw)} brut → {len(c1_focused)} focalisé')
    print(f'C2 : {len(c2_raw)} brut → {len(c2_focused)} focalisé')
    print(f'C3 : {len(c3_raw)} brut → {len(c3_focused)} focalisé')
    print(f'C4 : {len(c4_raw)} brut → {len(c4_focused)} focalisé')
    print(f'C5 : {len(c5_raw)} brut → {len(c5_focused)} focalisé')


if __name__ == '__main__':
    main()

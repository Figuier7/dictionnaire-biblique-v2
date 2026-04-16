#!/usr/bin/env python3
"""
fix_bym_capitalization.py — Capitalise les phrases après ponctuation
et les noms propres dans les définitions BYM.
"""

import json
import re
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(r"C:\Users\caeng\OneDrive\Documents\A l'ombre du figuier\dictionnaire-biblique-main")
BYM_PATH = BASE / "uploads/dictionnaires/bym/bym-lexicon.entries.json"

raw = BYM_PATH.read_bytes()
has_bom = raw[:3] == b'\xef\xbb\xbf'
bym = json.loads(raw.decode('utf-8-sig') if has_bom else raw.decode('utf-8'))
print(f"BYM: {len(bym)} entrées chargées")

# ══════════════════════════════════════════════════
# PHASE 1: Capitaliser après ponctuation ". "
# ══════════════════════════════════════════════════
print("\n── Phase 1: Capitaliser après ponctuation ──")

# Book abbreviations to skip (the period is part of the abbreviation)
ABBREVIATIONS = {
    'av', 'ap', 'env', 'cf', 'ch', 'v', 'ss', 'etc', 'vol',
    'no', 'ex', 'lé', 'ge', 'de', 'jo', 'ju', 'ru',
    'mt', 'mr', 'mc', 'lu', 'jn', 'ac', 'ro', 'ga', 'ep',
    'ph', 'col', 'ti', 'hé', 'ja', 'pi', 'da', 'os', 'am',
    'mi', 'na', 'ha', 'za', 'ma', 'ps', 'es', 'éz', 'jé',
    'pr', 'phm', 'co', 'th', 'r', 's', 'chr',
    # Number abbreviations
    'c.-à-d', 'p. ex',
}

def is_abbreviation(text_before_period):
    """Check if the period belongs to an abbreviation."""
    stripped = text_before_period.strip().lower()
    for ab in ABBREVIATIONS:
        if stripped.endswith(ab):
            return True
    # Check for verse references like "3:17" before the period
    if re.search(r'\d+:\d+$', stripped):
        return False  # This IS end of sentence (after a verse ref)
    # Check for ordinal numbers: "1er", "2e", etc.
    if re.search(r'\d+(er|e|ème)$', stripped):
        return True
    return False

phase1_count = 0
phase1_entries = 0

for entry in bym:
    d = entry.get("definition", "")
    if not d:
        continue

    new_d = list(d)
    changed = False

    # Find all ". X" patterns where X is lowercase
    for m in re.finditer(r'\. ([a-zéèêëàâäîïôöùûüç])', d):
        pos = m.start()  # position of the period
        char_pos = m.start(1)  # position of the lowercase letter

        # Get text before the period to check for abbreviations
        before = d[max(0, pos-10):pos]

        if is_abbreviation(before):
            continue

        # Skip if inside guillemets « »
        # Count open/close guillemets before this position
        before_full = d[:pos]
        open_g = before_full.count('«')
        close_g = before_full.count('»')
        if open_g > close_g:
            continue  # Inside guillemets

        # Capitalize
        new_d[char_pos] = d[char_pos].upper()
        changed = True
        phase1_count += 1

    if changed:
        entry["definition"] = ''.join(new_d)
        phase1_entries += 1

print(f"  Capitalisations: {phase1_count} dans {phase1_entries} entrées")

# ══════════════════════════════════════════════════
# PHASE 2: Capitaliser les noms propres
# ══════════════════════════════════════════════════
print("\n── Phase 2: Capitaliser les noms propres ──")

# Proper nouns map: lowercase -> correct capitalization
# Organized by category for clarity
PROPER_NOUNS = {
    # ── Noms divins / termes théologiques ──
    'elohîm': 'Elohîm',
    'yéhoshoua': 'Yéhoshoua',
    'yhwh': 'YHWH',
    'mashiah': 'Mashiah',
    'saint-esprit': 'Saint-Esprit',
    'torah': 'Torah',
    'satan': 'Satan',
    'christ': 'Christ',
    'dieu': 'Dieu',
    'seigneur': 'Seigneur',

    # ── Personnages bibliques majeurs ──
    'adam': 'Adam',
    'ève': 'Ève',
    'chavvah': 'Chavvah',
    'noé': 'Noé',
    'abraham': 'Abraham',
    'sarah': 'Sarah',
    'agar': 'Agar',
    'yitzhak': 'Yitzhak',
    'yaacov': 'Yaacov',
    'yéhouda': 'Yéhouda',
    'yishmael': 'Yishmael',
    'ismaël': 'Ismaël',
    'joseph': 'Joseph',
    'moshé': 'Moshé',
    'moïse': 'Moïse',
    'aaron': 'Aaron',
    'david': 'David',
    'salomon': 'Salomon',
    'élie': 'Élie',
    'éliyah': 'Éliyah',
    'éliyahou': 'Éliyahou',
    'élisée': 'Élisée',
    'isaïe': 'Isaïe',
    'jérémie': 'Jérémie',
    'ézéchiel': 'Ézéchiel',
    'daniel': 'Daniel',
    'jonas': 'Jonas',
    'osée': 'Osée',
    'joël': 'Joël',
    'amos': 'Amos',
    'michée': 'Michée',
    'habacuc': 'Habacuc',
    'sophonie': 'Sophonie',
    'aggée': 'Aggée',
    'zacharie': 'Zacharie',
    'malachie': 'Malachie',
    'abdias': 'Abdias',
    'samuel': 'Samuel',
    'saül': 'Saül',
    'josué': 'Josué',
    'ruth': 'Ruth',
    'boaz': 'Boaz',
    'esther': 'Esther',
    'job': 'Job',
    'esdras': 'Esdras',
    'néhémie': 'Néhémie',

    # ── Personnages NT ──
    'paulos': 'Paulos',
    'paul': 'Paul',
    'pierre': 'Pierre',
    'jean': 'Jean',
    'jacques': 'Jacques',
    'matthieu': 'Matthieu',
    'marc': 'Marc',
    'luc': 'Luc',
    'étienne': 'Étienne',
    'philippe': 'Philippe',
    'barnabas': 'Barnabas',
    'timothée': 'Timothée',
    'tite': 'Tite',
    'philémon': 'Philémon',
    'apollos': 'Apollos',
    'priscille': 'Priscille',
    'aquilas': 'Aquilas',
    'nicodème': 'Nicodème',
    'lazare': 'Lazare',
    'marthe': 'Marthe',
    'shaoul': 'Shaoul',
    'gamaliel': 'Gamaliel',

    # ── Personnages AT (suite) ──
    'qayin': 'Qayin',
    'caïn': 'Caïn',
    'jézabel': 'Jézabel',
    'korê': 'Korê',
    'roboam': 'Roboam',
    'jéroboam': 'Jéroboam',
    'josias': 'Josias',
    'ézéchias': 'Ézéchias',
    'neboukadnetsar': 'Neboukadnetsar',
    'hérode': 'Hérode',
    'pharaon': 'Pharaon',
    'pilate': 'Pilate',
    'caïphe': 'Caïphe',
    'absalom': 'Absalom',
    'jonathan': 'Jonathan',
    'josaphat': 'Josaphat',
    'yoab': 'Yoab',
    'josèphe': 'Josèphe',
    'naomi': 'Naomi',

    # ── Tribus ──
    'lévi': 'Lévi',
    'benjamin': 'Benjamin',
    'éphraïm': 'Éphraïm',
    'manassé': 'Manassé',
    'ruben': 'Ruben',

    # ── Lieux ──
    'israël': 'Israël',
    'yeroushalaim': 'Yeroushalaim',
    'jérusalem': 'Jérusalem',
    "kena'ân": "Kena'ân",
    'égypte': 'Égypte',
    'mitsrayim': 'Mitsrayim',
    'babylone': 'Babylone',
    'babel': 'Babel',
    'galilée': 'Galilée',
    'judée': 'Judée',
    'samarie': 'Samarie',
    'nazareth': 'Nazareth',
    'bethléhem': 'Bethléhem',
    'sinaï': 'Sinaï',
    'sion': 'Sion',
    'jourdain': 'Jourdain',
    'hébron': 'Hébron',
    'rome': 'Rome',
    'corinthe': 'Corinthe',
    'éphèse': 'Éphèse',
    'athènes': 'Athènes',
    'antioche': 'Antioche',
    'philippes': 'Philippes',
    'thessalonique': 'Thessalonique',
    'jéricho': 'Jéricho',
    'béthanie': 'Béthanie',
    'capharnaüm': 'Capharnaüm',
    'ninive': 'Ninive',
    'tyr': 'Tyr',

    # ── Titres / peuples ──
    'césar': 'César',
    'pharisiens': 'Pharisiens',
    'sadducéens': 'Sadducéens',
}

# Words that look like proper nouns but are common words in certain contexts
# We need to be careful with these — only capitalize when they're clearly proper nouns
CONTEXT_SENSITIVE = {
    'marie',      # Also "Je vous salue, marie" — but in BYM always a person
    'pierre',     # Also "pierre angulaire" — need context check
    'jean',       # Always a person in BYM
    'marc',       # Always a person in BYM
    'luc',        # Always a person in BYM
    'paul',       # Always a person in BYM
    'tite',       # Also "à titre de" — need context check
    'sion',       # Could be common in some contexts
    'dan',        # Also "dans" partial — need word boundary
    'gad',        # Name
    'job',        # Also "un job" — but in BYM always the person
    'rome',       # Always the city in BYM
    'babel',      # Could be "tour de babel" (lowercase ok?) — no, capitalize
    'agar',       # Always the person in BYM
    'ruth',       # Always the person in BYM
    'ève',        # Also "la veille" -> but "ève" is specifically Eve
    'osée',       # Also "j'ai osé" — need boundary check
    'dieu',       # Note: editorial line uses Elohîm, but "Dieu" should be capitalized
    'seigneur',   # Should be capitalized when referring to God/Yéhoshoua
}

# Patterns where certain words should NOT be capitalized
SKIP_PATTERNS = {
    'pierre': [r'pierre\s+angulaire', r'pierre\s+de\s+touche', r'pierre\s+précieuse',
               r'pierres?\s+précieuses', r'pierres?\s+de\s+construction',
               r'première\s+pierre', r'pierres?\s+taillées', r'cœur\s+de\s+pierre'],
    'tite': [r'à\s+titre', r'en\s+titre'],
    'sion': [],  # Always capitalize in BYM context
    'ève': [r"veille\s+d"],  # Not relevant, ève is always Eve
    'osée': [r"j'ai\s+osé", r"a\s+osé"],
}

phase2_count = 0
phase2_entries = 0

for entry in bym:
    d = entry.get("definition", "")
    if not d:
        continue

    new_d = d
    changed = False

    for lowercase, capitalized in PROPER_NOUNS.items():
        if lowercase not in new_d.lower():
            continue

        # Build regex pattern with word boundaries
        # Handle apostrophes in names like kena'ân
        escaped = re.escape(lowercase)
        # Word boundary: preceded by space, newline, start, punctuation, or after «
        # NOT preceded by another letter (to avoid matching substrings)
        pattern = r'(?<![a-zéèêëàâäîïôöùûüçA-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ])' + escaped + r'(?![a-zéèêëàâäîïôöùûüçA-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ])'

        # Check for skip patterns
        skip_pats = SKIP_PATTERNS.get(lowercase, [])

        change_flag = [changed]
        def replace_proper(match):
            start = match.start()
            # Check skip patterns
            for sp in skip_pats:
                # Check around match position
                context_start = max(0, start - 20)
                context_end = min(len(new_d), start + len(lowercase) + 30)
                context = new_d[context_start:context_end].lower()
                if re.search(sp, context):
                    return match.group(0)

            # Don't replace if already capitalized
            if match.group(0) == capitalized:
                return match.group(0)

            # Don't replace inside italic markers (etymology section)
            # Check if we're between _ markers
            before_text = new_d[:start]
            open_italics = before_text.count('_')
            if open_italics % 2 == 1:
                # We're inside italic/etymology — still capitalize
                pass

            change_flag[0] = True
            return capitalized

        new_d = re.sub(pattern, replace_proper, new_d, flags=re.IGNORECASE if lowercase == lowercase.lower() else 0)
        changed = change_flag[0]

    if changed:
        # Count actual changes
        old_chars = list(d)
        new_chars = list(new_d)
        diffs = sum(1 for a, b in zip(old_chars, new_chars) if a != b)
        phase2_count += diffs
        phase2_entries += 1
        entry["definition"] = new_d

print(f"  Noms propres capitalisés: ~{phase2_count} caractères dans {phase2_entries} entrées")

# ══════════════════════════════════════════════════
# Update definition_length
# ══════════════════════════════════════════════════
for entry in bym:
    entry["definition_length"] = len(entry.get("definition", ""))

# ══════════════════════════════════════════════════
# Save
# ══════════════════════════════════════════════════
text = json.dumps(bym, ensure_ascii=False, indent=2)
if has_bom:
    BYM_PATH.write_bytes(b'\xef\xbb\xbf' + text.encode('utf-8'))
else:
    BYM_PATH.write_bytes(text.encode('utf-8'))
print(f"\n  Sauvegardé: {BYM_PATH.name}")

# ══════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════
print("\n══════════════════════════════════════")
print("  RÉSUMÉ")
print("══════════════════════════════════════")
print(f"  Phase 1 — Après ponctuation: {phase1_count} caps dans {phase1_entries} entrées")
print(f"  Phase 2 — Noms propres:      ~{phase2_count} caps dans {phase2_entries} entrées")
print("══════════════════════════════════════")

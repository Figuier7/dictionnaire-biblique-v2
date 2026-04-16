#!/usr/bin/env python3
"""
Nettoyage éditorial BYM : remplace les termes interdits par les formes BYM.

Règles :
1. "Dieu" standalone → "Elohîm" (garde "Elohîm (Dieu)" en parenthèse tel quel)
2. "Jésus" standalone → "Yéhoshoua" (garde "Yéhoshoua (Jésus)" tel quel)
3. "Christ" standalone → "le Mashiah" (garde "Mashiah (Christ)" tel quel)
4. "Jésus-Christ" → "Yéhoshoua le Mashiah"
5. "l'Éternel" → "YHWH" (si jamais trouvé)

Attention spéciale :
- Ne PAS toucher les patterns entre parenthèses explicatives
- Ne PAS toucher les citations en anglais entre guillemets
- Ne PAS toucher "Antichrist" (composé)
- "de Dieu" → "d'Elohîm" (contraction correcte)
- "le Dieu" → "l'Elohîm" (contraction)
- "au Dieu" → "à l'Elohîm" (contraction)
- "du Dieu" → "de l'Elohîm" (cas rare)

Modes : dry-run (default) ou --apply
"""
import json
import sys
import re
import argparse
import glob
from pathlib import Path
from datetime import datetime
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
DICT_DIR = ROOT / "uploads" / "dictionnaires"
ISBE_DIR = DICT_DIR / "isbe"
AUDIT_DIR = ROOT / "work" / "audit"
LOG_JSON = AUDIT_DIR / "bym-editorial-fix-log.json"


def fix_dieu(text):
    """Replace standalone 'Dieu' with 'Elohîm' respecting French contractions."""
    result = text

    # Skip the "Elohîm (Dieu)" pattern — mark it temporarily
    result = re.sub(r'(Eloh[iî]m\s*)\(Dieu\)', r'\1(##DIEU_PATTERN##)', result)

    # Now replace all standalone "Dieu" with appropriate French contractions
    # Order matters: longest patterns first

    # "de Dieu" → "d'Elohîm"
    result = re.sub(r'\bde Dieu\b', "d'Elohîm", result)
    # "De Dieu" (start of sentence) → "D'Elohîm"
    result = re.sub(r'\bDe Dieu\b', "D'Elohîm", result)

    # "le Dieu" → "l'Elohîm"
    result = re.sub(r'\ble Dieu\b', "l'Elohîm", result)
    # "Le Dieu" → "L'Elohîm"
    result = re.sub(r'\bLe Dieu\b', "L'Elohîm", result)

    # "au Dieu" → "à l'Elohîm"  (= à + le Dieu)
    result = re.sub(r'\bau Dieu\b', "à l'Elohîm", result)
    # "Au Dieu" → "À l'Elohîm"
    result = re.sub(r'\bAu Dieu\b', "À l'Elohîm", result)

    # "du Dieu" → "de l'Elohîm" (= de + le Dieu)
    result = re.sub(r'\bdu Dieu\b', "de l'Elohîm", result)
    # "Du Dieu" → "De l'Elohîm"
    result = re.sub(r'\bDu Dieu\b', "De l'Elohîm", result)

    # "un Dieu" → "un Elohîm"
    result = re.sub(r'\bun Dieu\b', 'un Elohîm', result)

    # Remaining standalone "Dieu" → "Elohîm"
    result = re.sub(r'\bDieu\b', 'Elohîm', result)

    # Restore the pattern markers
    result = result.replace('(##DIEU_PATTERN##)', '(Dieu)')

    return result


def fix_jesus(text):
    """Replace standalone 'Jésus' with 'Yéhoshoua' respecting patterns."""
    result = text

    # Skip "Yéhoshoua (Jésus)" pattern
    result = re.sub(r'(Y[eé]hoshoua\s*)\(J[eé]sus[^)]*\)', r'\1(##JESUS_PATTERN##)', result)

    # "Jésus-Christ" → "Yéhoshoua le Mashiah"
    result = re.sub(r'\bJ[eé]sus[- ]Christ\b', 'Yéhoshoua le Mashiah', result)

    # "de Jésus" → "de Yéhoshoua"
    result = re.sub(r'\bde J[eé]sus\b', 'de Yéhoshoua', result)

    # "Jésus" standalone → "Yéhoshoua"
    result = re.sub(r'\bJ[eé]sus\b', 'Yéhoshoua', result)

    # Restore pattern
    result = result.replace('(##JESUS_PATTERN##)', '(Jésus)')

    # Fix any broken patterns from nested replacements
    result = re.sub(r'Y[eé]hoshoua Y[eé]hoshoua', 'Yéhoshoua', result)

    return result


def fix_christ(text):
    """Replace standalone 'Christ' with 'le Mashiah' respecting patterns."""
    result = text

    # Skip "Mashiah (Christ)" pattern
    result = re.sub(r'(Mashiah\s*)\(Christ\)', r'\1(##CHRIST_PATTERN##)', result)

    # Skip "Antichrist"
    result = re.sub(r'\bAntichrist\b', '##ANTICHRIST##', result)

    # "Jésus-Christ" already handled by fix_jesus
    # "du Christ" → "du Mashiah"
    result = re.sub(r'\bdu Christ\b', 'du Mashiah', result)
    # "de Christ" → "de Mashiah" (rare)
    result = re.sub(r'\bde Christ\b', 'du Mashiah', result)
    # "le Christ" → "le Mashiah"
    result = re.sub(r'\ble Christ\b', 'le Mashiah', result)
    # "Le Christ" → "Le Mashiah"
    result = re.sub(r'\bLe Christ\b', 'Le Mashiah', result)
    # "au Christ" → "au Mashiah"
    result = re.sub(r'\bau Christ\b', 'au Mashiah', result)
    # Remaining "Christ" → "Mashiah"
    result = re.sub(r'\bChrist\b', 'le Mashiah', result)

    # Restore patterns
    result = result.replace('(##CHRIST_PATTERN##)', '(Christ)')
    result = result.replace('##ANTICHRIST##', 'Antichrist')

    # Fix double articles from replacement
    result = result.replace('le le Mashiah', 'le Mashiah')
    result = result.replace('Le le Mashiah', 'Le Mashiah')

    return result


def fix_eternel(text):
    """Replace "l'Éternel" with "YHWH"."""
    result = text
    result = re.sub(r"l['\u2019][EÉ]ternel", 'YHWH', result)
    return result


def process_definition(defn):
    """Apply all BYM editorial fixes to a definition."""
    result = defn
    result = fix_dieu(result)
    result = fix_jesus(result)
    result = fix_christ(result)
    result = fix_eternel(result)
    return result


def process_file(filepath, encoding, apply_mode):
    """Process a single dictionary file. Returns (entries_changed, total_replacements)."""
    with open(filepath, encoding=encoding) as f:
        entries = json.load(f)

    entries_changed = 0
    total_diffs = 0

    for e in entries:
        defn = e.get('definition', '')
        if not defn:
            continue
        new_defn = process_definition(defn)
        if new_defn != defn:
            entries_changed += 1
            # Count actual word changes (rough)
            total_diffs += abs(len(new_defn) - len(defn)) + 1
            if apply_mode:
                e['definition'] = new_defn
                e['definition_length'] = len(new_defn)

    if apply_mode and entries_changed > 0:
        # Determine write encoding
        if encoding == 'utf-8-sig':
            with open(filepath, 'w', encoding='utf-8-sig') as f:
                if isinstance(entries, list) and filepath.name.startswith('isbe-'):
                    payload = json.dumps(entries, ensure_ascii=False, separators=(', ', ': '))
                    f.write(payload)
                else:
                    json.dump(entries, f, ensure_ascii=False, indent=2)
        else:
            with open(filepath, 'w', encoding=encoding) as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)

    return entries_changed, total_diffs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'Mode: {mode}')

    total_changed = 0
    total_diffs = 0

    # ISBE chunks
    print('\n=== ISBE ===')
    for fp in sorted(ISBE_DIR.glob('isbe-?.json')):
        changed, diffs = process_file(fp, 'utf-8-sig', args.apply)
        if changed:
            print(f'  {fp.name}: {changed} entries')
            total_changed += changed
            total_diffs += diffs

    # Easton
    print('\n=== Easton ===')
    fp = DICT_DIR / 'easton' / 'easton.entries.json'
    changed, diffs = process_file(fp, 'utf-8-sig', args.apply)
    print(f'  easton.entries.json: {changed} entries')
    total_changed += changed
    total_diffs += diffs

    # Smith
    print('\n=== Smith ===')
    fp = DICT_DIR / 'smith' / 'smith.entries.json'
    changed, diffs = process_file(fp, 'utf-8', args.apply)
    print(f'  smith.entries.json: {changed} entries')
    total_changed += changed
    total_diffs += diffs

    print(f'\n=== TOTAL ===')
    print(f'Entries changed: {total_changed}')

    # Post-apply verification
    if args.apply:
        # Quick recount
        remaining_dieu = 0
        remaining_jesus = 0
        remaining_christ = 0
        for fp in sorted(ISBE_DIR.glob('isbe-?.json')):
            with open(fp, encoding='utf-8-sig') as f:
                for e in json.load(f):
                    defn = e.get('definition', '')
                    # Count standalone (not in pattern)
                    for m in re.finditer(r'\bDieu\b', defn):
                        before = defn[max(0, m.start()-20):m.start()]
                        if 'Eloh' not in before:
                            remaining_dieu += 1
                    for m in re.finditer(r'\bJ[eé]sus\b', defn):
                        before = defn[max(0, m.start()-25):m.start()]
                        if 'hoshoua' not in before:
                            remaining_jesus += 1
                    for m in re.finditer(r'\bChrist\b', defn):
                        before = defn[max(0, m.start()-20):m.start()]
                        if 'Mashiah' not in before and 'Anti' not in before:
                            remaining_christ += 1

        print(f'\nPost-fix remaining (ISBE only):')
        print(f'  Dieu standalone:   {remaining_dieu}')
        print(f'  Jésus standalone:  {remaining_jesus}')
        print(f'  Christ standalone: {remaining_christ}')

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_JSON, 'w', encoding='utf-8') as f:
        json.dump({
            'mode': mode,
            'timestamp': datetime.now().isoformat(),
            'total_entries_changed': total_changed,
        }, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()

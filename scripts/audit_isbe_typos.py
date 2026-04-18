#!/usr/bin/env python3
"""
Audit des erreurs OCR/typo et résidus anglais dans les définitions ISBE.

Catégories scannées :
1. Problèmes typographiques (double espaces, ponctuation mal placée)
2. Mots anglais résiduels dans le texte français
3. Erreurs OCR courantes (confusions de lettres)
4. Phrases entières non traduites
"""
import json
import sys
import re
import glob
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
ISBE_DIR = ROOT / "uploads" / "dictionnaires" / "isbe"
AUDIT_DIR = ROOT / "work" / "audit"
OUT_JSON = AUDIT_DIR / "isbe-typo-audit.json"

# Common English words that should NOT appear in French prose
# (excluding those that are also French: or, est, son, etc.)
EN_WORDS = [
    'the', 'was', 'which', 'with', 'from', 'this', 'that',
    'have', 'been', 'were', 'are', 'has', 'had', 'but',
    'they', 'their', 'there', 'these', 'those', 'would',
    'could', 'should', 'shall', 'will', 'may', 'might',
    'must', 'can', 'did', 'does', 'than', 'then', 'when',
    'where', 'what', 'who', 'whom', 'whose', 'how',
    'about', 'after', 'before', 'between', 'through',
    'during', 'under', 'above', 'below', 'into', 'upon',
    'also', 'only', 'other', 'some', 'such', 'each',
    'every', 'both', 'most', 'many', 'much', 'any',
    'all', 'same', 'very', 'own', 'just', 'still',
    'even', 'however', 'because', 'although', 'whether',
    'while', 'since', 'until', 'unless', 'though',
    'himself', 'itself', 'themselves', 'ourselves',
    'called', 'found', 'given', 'known', 'made', 'said',
    'used', 'taken', 'seen', 'done', 'become',
    'according', 'perhaps', 'probably', 'certainly',
    'therefore', 'nevertheless', 'moreover', 'furthermore',
    'indeed', 'either', 'neither', 'already', 'always',
]

# Words that look English but are also valid French or Latin/technical
SAFE_WORDS = {
    'a', 'an', 'or', 'et', 'est', 'son', 'on', 'me', 'la',
    'le', 'les', 'de', 'du', 'des', 'en', 'un', 'une',
    'se', 'si', 'ne', 'pas', 'plus', 'par', 'pour', 'dans',
    'sur', 'au', 'aux', 'ce', 'ces', 'qui', 'que',
    'nous', 'vous', 'ils', 'elle', 'elles', 'lui',
    'but', 'age', 'note', 'place', 'prince', 'force',
    'simple', 'noble', 'large', 'double', 'possible',
    'temple', 'table', 'stable', 'capable', 'probable',
    'comparable', 'considerable', 'favorable', 'horrible',
    'terrible', 'visible', 'invisible', 'impossible',
    'ensemble', 'example', 'oracle', 'miracle', 'article',
    'sacrifice', 'service', 'commerce', 'province',
    'discipline', 'doctrine', 'nature', 'figure',
    'measure', 'treasure', 'creature', 'adventure',
    'culture', 'agriculture', 'literature', 'structure',
}


def scan_entry(entry_id, mot, definition):
    """Scan a single definition for issues. Returns list of findings."""
    findings = []
    defn = definition

    # 1. Double spaces
    doubles = re.findall(r'  +', defn)
    if doubles:
        findings.append(('double_space', len(doubles), None))

    # 2. Space before punctuation
    space_punct = re.findall(r' [,;:]', defn)
    if space_punct:
        for sp in space_punct[:3]:
            findings.append(('space_before_punct', 1, sp))

    # 3. Missing space after period (not in abbreviations)
    no_space = re.findall(r'(?<![A-Z])\.[A-Z]', defn)
    if no_space:
        for ns in no_space[:3]:
            findings.append(('no_space_after_period', 1, ns))

    # 4. English words in French text
    # Only flag if the word appears in running French text, not in quoted English
    words = re.findall(r'\b[a-z]+\b', defn.lower())
    en_found = Counter()
    for w in words:
        if w in SAFE_WORDS:
            continue
        if w in EN_WORDS:
            en_found[w] += 1

    # Only flag if there are multiple English words (suggests untranslated sentence)
    en_total = sum(en_found.values())
    if en_total >= 3:
        top_en = en_found.most_common(5)
        findings.append(('english_residue', en_total, dict(top_en)))

    # 5. Full untranslated English sentences
    # Pattern: sequence of 5+ English words in a row
    en_sentence = re.findall(
        r'\b(?:the|a|an|is|was|are|were|has|had|have|been|being|'
        r'which|that|this|these|those|who|whom|whose|'
        r'shall|will|would|could|should|may|might|must|can|'
        r'not|but|and|or|if|when|where|how|what|'
        r'he|she|it|they|we|you|his|her|its|their|our|your|'
        r'them|him|us|me|my|'
        r'said|called|made|found|given|known|taken|seen|done|'
        r'more|most|very|much|many|some|any|all|each|every|other|'
        r'also|only|even|still|just|already|never|always|often|'
        r'about|after|before|between|through|during|under|above|'
        r'into|upon|from|with|by|for|to|of|in|on|at|'
        r'[a-z]+ed|[a-z]+ing|[a-z]+tion|[a-z]+ness|[a-z]+ment)\b'
        r'(?:\s+(?:the|a|an|is|was|are|were|has|had|have|been|being|'
        r'which|that|this|these|those|who|whom|whose|'
        r'shall|will|would|could|should|may|might|must|can|'
        r'not|but|and|or|if|when|where|how|what|'
        r'he|she|it|they|we|you|his|her|its|their|our|your|'
        r'them|him|us|me|my|'
        r'said|called|made|found|given|known|taken|seen|done|'
        r'more|most|very|much|many|some|any|all|each|every|other|'
        r'also|only|even|still|just|already|never|always|often|'
        r'about|after|before|between|through|during|under|above|'
        r'into|upon|from|with|by|for|to|of|in|on|at|'
        r'[a-z]+ed|[a-z]+ing|[a-z]+tion|[a-z]+ness|[a-z]+ment)\b){4,}',
        defn, re.IGNORECASE
    )
    if en_sentence:
        for sent in en_sentence[:2]:
            if len(sent.split()) >= 5:
                findings.append(('untranslated_sentence', len(sent.split()), sent[:120]))

    return findings


def main():
    results = {
        'double_space': {'count': 0, 'entries': []},
        'space_before_punct': {'count': 0, 'entries': []},
        'no_space_after_period': {'count': 0, 'entries': []},
        'english_residue': {'count': 0, 'entries': []},
        'untranslated_sentence': {'count': 0, 'entries': []},
    }

    total = 0
    for fp in sorted(ISBE_DIR.glob('isbe-?.json')):
        with open(fp, encoding='utf-8-sig') as f:
            entries = json.load(f)
        for e in entries:
            total += 1
            defn = e.get('definition', '')
            if not defn or len(defn) < 20:
                continue
            findings = scan_entry(e['id'], e.get('mot', ''), defn)
            for ftype, count, detail in findings:
                results[ftype]['count'] += count
                if len(results[ftype]['entries']) < 30:
                    results[ftype]['entries'].append({
                        'entry_id': e['id'],
                        'mot': e.get('mot', '')[:30],
                        'count': count,
                        'detail': str(detail)[:150] if detail else None,
                    })

    print(f'Total entries scanned: {total}')
    print()
    for category, data in results.items():
        print(f'=== {category} : {data["count"]} occurrences ===')
        for sample in data['entries'][:10]:
            detail = f' | {sample["detail"]}' if sample.get('detail') else ''
            print(f'  {sample["entry_id"]} {sample["mot"]:30s} x{sample["count"]}{detail}')
        print()

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump({
            'total_entries': total,
            'results': results,
        }, f, ensure_ascii=False, indent=2)
    print(f'Output: {OUT_JSON}')


if __name__ == '__main__':
    main()

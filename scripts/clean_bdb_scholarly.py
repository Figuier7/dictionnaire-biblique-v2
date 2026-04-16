#!/usr/bin/env python3
"""
Nettoie les def_full_fr du lexique hebreu biblique de leurs artefacts scholarly BDB.

Transformations :
1. Retire les parentheses contenant des refs auteur (Lag, Dl, BeRy, Ol, etc.)
2. Expand abreviations de langues (Ar. -> arabe, As. -> akkadien, etc.)
3. Retire les conventions obscures (q.v., s.v., HA <num>, § <num>)
4. Expand symboles (∥ -> parallele a)
5. Nettoyage ponctuation residuelle
6. Retire trailing status markers (ref/fait/base)

Usage :
    python3 clean_bdb_scholarly.py --test   # teste sur H3/H6/H10/H12
    python3 clean_bdb_scholarly.py          # affiche avant/apres sur un echantillon
"""

import re
import sys
import json
import argparse
from pathlib import Path

# ============================================================
# REGEX RULES
# ============================================================

# Noms d'auteurs scholarly cités dans BDB (liste etendue)
# Inclut abreviations courtes (Sta = Stade, Kö = Köhler) ET longues
SCHOLARLY_AUTHORS = (
    r'(?:Lag|Dl|BeRy|Ol|Ges|Gesen|Brock|Köh|Kö|Wetz|Jenni|Barth|Levy|Jastrow|'
    r'Stade|Sta|Wellh|Kau|GK|Dr|Nöld|Nö|Müll|Müller|Dillm|Dillmann|Ew|Ewald|'
    r'Hi|Hitzig|Sm|Smend|Duh|Duhm|Klo|Klost|Marti|Kit|Kittel|Pra|Praetorius|'
    r'Wright|Lane|Hengst|Hengstenberg|Gei|Geiger|Stz|Siegfried|Volck|Knauf|'
    r'BDB|Buhl|Reng|Stenning|Gressmann|Gray|Erman|Bewer|Ryssel|Olshausen)'
)
_AUTHOR_IN_TEXT = re.compile(r'\b' + SCHOLARLY_AUTHORS + r'\b')


def strip_author_parens(text):
    """Retire les parentheses balanced qui contiennent un nom d'auteur scholarly.
    Supporte l'imbrication. Les parentheses internes sans auteur sont preservees.
    """
    result = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == '(':
            # Trouver la parenthese fermante balanced
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                if text[j] == '(':
                    depth += 1
                elif text[j] == ')':
                    depth -= 1
                j += 1
            # j pointe apres la fermante (ou n si non-matche)
            content_with_parens = text[i:j]
            if _AUTHOR_IN_TEXT.search(content_with_parens):
                # Skip entirement cette parenthese
                # Eat optional leading/trailing space
                while result and result[-1] == ' ':
                    result.pop()
                i = j
                # Skip space apres
                while i < n and text[i] == ' ':
                    i += 1
                result.append(' ')
                continue
            else:
                # Recursivement nettoyer le contenu interne
                inner = text[i+1:j-1] if j > i+1 else ''
                cleaned_inner = strip_author_parens(inner)
                if cleaned_inner.strip():
                    result.append('(' + cleaned_inner + ')')
                # sinon skip (parenthese vide)
                i = j
                continue
        else:
            result.append(text[i])
            i += 1
    return ''.join(result)

# Segment "Dl HA 65", "Dl W 184", "BeRy § 215", "Ba NB 49, 487" non parenthese
_INLINE_AUTHOR_REF = re.compile(
    r'\s*\b' + SCHOLARLY_AUTHORS + r'\s+[A-Z]{1,3}\s*\d+[\w.,\s§]*?(?=[;\.\)]|\s[A-Z][a-z]|\Z)',
    re.MULTILINE
)

# Codes internes BDB (apparats critiques, sources source-critique, etc.)
_BDB_INTERNAL = [
    re.compile(r'\bHA\s+\d+\b'),
    re.compile(r'\bNB\s+\d+(?:,\s*\d+)*\b'),
    re.compile(r'\bM\s+I\b(?=\s)'),  # "M I" abbreviation
    re.compile(r'\bibb\b'),
    re.compile(r'\bWisdLt\b'),
    re.compile(r'§\s*\d+[a-z]?(?:\.\d+)?'),  # § 215 b.1
    re.compile(r'\bPr\s+\d{2,4}\b(?!\s*:)'),  # "Pr 114" isole (pas "Pr 11:14" qui est Proverbes)
    re.compile(r'\+\s*\d+\s*t\.', re.IGNORECASE),  # "+ 4 t." = "+ 4 times"
    # Source-critique Wellhausen/Graf (J/E/D/P sources du Pentateuque)
    re.compile(r'\bJED?P?\b'),  # JED, JEDP, JE
    re.compile(r'\b(?:seulement|only)\s+[JEDP]+\b'),
    # References pages / volumes
    re.compile(r'\bR\.\s*\d+(?:\.\d+)?\b'),  # R.2, R.3.1
    re.compile(r'\be\s+\d+\s*nn?\b'),  # "e 1 nn"
    re.compile(r'\b[IVX]+,\s*\d+(?:\s*[a-z])?\b'),  # "I, 414" "II, 578 f"
]

# Abreviations de langues -> expanser
_LANG_ABBREV = [
    # Deduplication "Ar. arabe" -> "arabe"
    (re.compile(r'\bAr\.\s+arabe\b', re.IGNORECASE), 'arabe'),
    (re.compile(r'\bAs\.\s+(?:akkadien|assyrien)\b', re.IGNORECASE), 'akkadien'),
    (re.compile(r'\bAram\.\s+aram[ée]en\b', re.IGNORECASE), 'araméen'),
    (re.compile(r'\bSyr\.\s+syriaque\b', re.IGNORECASE), 'syriaque'),
    # Expansion simple
    (re.compile(r'\bAr\.', re.IGNORECASE), 'arabe'),
    (re.compile(r'\bAs\.', re.IGNORECASE), 'akkadien'),
    (re.compile(r'\bAram\.', re.IGNORECASE), 'araméen'),
    (re.compile(r'\bSyr\.', re.IGNORECASE), 'syriaque'),
    (re.compile(r'\bGr\.', re.IGNORECASE), 'grec'),
    (re.compile(r'\bLat\.', re.IGNORECASE), 'latin'),
    (re.compile(r'\bPhoen\.', re.IGNORECASE), 'phénicien'),
    (re.compile(r'\bUgar\.', re.IGNORECASE), 'ougaritique'),
    (re.compile(r'\bEth\.', re.IGNORECASE), 'éthiopien'),
]

# Autres abreviations lexicographiques
_OTHER_ABBREV = [
    (re.compile(r'\bmng\.'), 'signification'),
    (re.compile(r'\bconcr\.'), 'concret'),
    (re.compile(r'\babstr\.'), 'abstrait'),
    (re.compile(r'\bpropr\.'), 'proprement'),
    (re.compile(r'\bfig\.'), 'figuré'),
    (re.compile(r'\bspec\.'), 'spécifiquement'),
    (re.compile(r'\bopp\.'), 'opposé'),
    (re.compile(r'\bexp\.'), 'expression'),
    (re.compile(r'\bexc\.'), 'excepté'),
    (re.compile(r'\bincl\.'), 'incluant'),
    (re.compile(r'\bexcl\.'), 'excluant'),
    (re.compile(r'\bsq\.'), 'suivi de'),
    (re.compile(r'\bHex\.'), 'Hexateuque'),
    (re.compile(r'\bPent\.'), 'Pentateuque'),
    (re.compile(r'\bl?\.c\.'), ''),  # loc. cit. obscur
    # Obscurites a retirer
    (re.compile(r'\s*\(q\.v\.\)\s*'), ' '),
    (re.compile(r'\bq\.v\.'), ''),
    (re.compile(r'\bs\.v\.'), ''),
    (re.compile(r'\bib\.'), ''),
    (re.compile(r'\bid\.'), 'idem'),
    (re.compile(r'\betc\.\s*;'), 'etc.'),
]

# Symboles scholarly
_SYMBOLS = [
    (re.compile(r'\s*∥\s*'), ' parallèle à '),  # parallele biblique
    (re.compile(r'\s*[†‡]\s*'), ' '),  # dagger
    (re.compile(r'\s*[𝔊𝔖𝔗𝔙]\s*'), ' '),  # LXX/Peshitta/Targum/Vulgate
    (re.compile(r'\bψ\s*(\d)'), r'Ps \1'),  # psi -> Ps pour Psaumes
    # Orphans residuels apres retrait
    (re.compile(r'\bSeulement dans\s*;'), 'Seulement dans'),
]

# Trailing status (ref/fait/base/done)
_TRAILING_STATUS = re.compile(
    r'\s*[.\s]*\b(ref|base|fait|done)\b\.?\s*$',
    re.IGNORECASE
)

# Nettoyage ponctuation finale
_CLEANUP = [
    (re.compile(r'\s+'), ' '),                    # multiple spaces
    (re.compile(r'\s+([;,.:])'), r'\1'),          # space before punct
    (re.compile(r'\(\s*\)'), ''),                  # empty parens
    (re.compile(r'\(\s*([,;.])'), r'('),           # "( ,"
    (re.compile(r'([,;.])\s*\)'), r')'),           # ", )"
    (re.compile(r';\s*;'), ';'),                   # double ;
    (re.compile(r',\s*,'), ','),                   # double ,
    (re.compile(r'\s*,\s*\.'), '.'),               # ",."
    (re.compile(r'\.\s*\.'), '.'),                 # ".."
    (re.compile(r'\s*(?:\+\s*)+\s*;'), ';'),       # "+ ;" residuel
    (re.compile(r'^\s*[\.;,]+\s*'), ''),           # debut avec ponctuation
]


def clean_bdb_scholarly(text):
    """Applique toutes les regles de nettoyage."""
    if not text or not text.strip():
        return text

    s = text

    # 1. Retirer les parentheses d'auteurs (balanced parens, imbrication preservee)
    s = strip_author_parens(s)

    # 2. Retirer refs auteur hors parentheses
    s = _INLINE_AUTHOR_REF.sub('', s)

    # 3. Retirer codes internes BDB
    for rx in _BDB_INTERNAL:
        s = rx.sub('', s)

    # 4. Expansion langues
    for rx, repl in _LANG_ABBREV:
        s = rx.sub(repl, s)

    # 5. Expansion autres abreviations
    for rx, repl in _OTHER_ABBREV:
        s = rx.sub(repl, s)

    # 6. Symboles
    for rx, repl in _SYMBOLS:
        s = rx.sub(repl, s)

    # 7. Trailing status
    prev = None
    while s != prev:
        prev = s
        s = _TRAILING_STATUS.sub('', s).rstrip(' .,;—-\t\n')

    # 8. Cleanup ponctuation
    for rx, repl in _CLEANUP:
        s = rx.sub(repl, s)

    return s.strip()


# ============================================================
# TEST
# ============================================================

SAMPLES = {
    'H3': "[אֵב] n.[m.] fraîcheur, vert frais (Lag B N 207 inf. ibb; d'où concr., cf. Ar. arabe; ci-dessus tige & mng. mieux que √ אנב (printemps) cf. As. inbu, fruit, Aram. אִנְבֵּהּ (q.v.) Dl HA 65, Pr 114) עֹדֶנּוּ בְאִבּוֹ tandis qu'il est frais (c'est-à-dire אָחוּ, roseau) Jb 8:12; concr., pl. jeunes pousses בְּאִבֵּי הַנַּחַל Ct 6:11 (∥ הֲפָֽרְחָה הַגֶּפֶן הֵנֵצוּ הָרִמֹּנִֽים׃). ref",

    'H10': "אֲבַדּוֹן n.f. ? Pr 27:20 abstr. presque = n.pr. (lieu de) Destruction, Ruin, ’Abaddôn (cf. syriaque 𝔖 Jb 28:22 etc.)—אֲבַדּֽוֹן Jb 26:6 (+ 4 t.) ; abrév. אבדה Kt אֲבַדּֽוֹ Qr Pr 27:20.—Lieu de ruine dans Shᵉʼôl pour les morts perdus ou ruinés, comme développement de la distinction antérieure de condition dans Shᵉʼôl (v. שְׁאוֹל). Seulement dans WisdLt ; Jb 31:12 ; ∥ שׁאול Jb 26:6 Pr 15:11 27:20 ; ∥ מות Jb 28:22 ; ∥ קבר ψ 88:12. fait",

    'H12': "אַבְדָ֑ן, & אׇבְדַן (cstr.) n.[m.] destruction (Syr. syriaque) Est 9:5 (מַכַּת־חֶרֶב וְהֶרֶג וְא׳), 8:8 ; (sur la forme v. BeRy ; Ol § 215 b.1 Ba NB 49, 487). ref",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Test sur echantillons')
    parser.add_argument('--bulk', action='store_true', help='Applique a tout hebrew-lexicon-fr.json, genere .clean.json')
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding='utf-8')

    if args.test:
        for sid, raw in SAMPLES.items():
            cleaned = clean_bdb_scholarly(raw)
            print(f'{"="*70}')
            print(f'{sid}')
            print(f'{"="*70}')
            print(f'AVANT ({len(raw)} chars):')
            print(f'  {raw}')
            print()
            print(f'APRES ({len(cleaned)} chars):')
            print(f'  {cleaned}')
            print()
        return

    print("Usage: --test pour voir avant/apres, --bulk pour appliquer (non implemente ici)")


if __name__ == '__main__':
    main()

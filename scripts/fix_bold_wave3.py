#!/usr/bin/env python3
"""
fix_bold_wave3.py — Vague 3 : gras structurel ciblé.

V3-A  BYM désambiguïsation : gras sur l'identifiant de chaque personne/sens
V3-B  BYM liste de termes (AMOUR) : gras sur les en-têtes de section
V3-C  Easton inline (N) : gras sur les marqueurs numérotés (4 entrées sûres)

Approche : remplacement exact par ID d'entrée, aucune regex globale.
"""

import json
import re
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(r"C:\Users\caeng\OneDrive\Documents\A l'ombre du figuier\dictionnaire-biblique-main")
EASTON_PATH = BASE / "uploads/dictionnaires/easton/easton.entries.json"
BYM_PATH = BASE / "uploads/dictionnaires/bym/bym-lexicon.entries.json"

def load_json(path):
    raw = path.read_bytes()
    return json.loads(raw.decode('utf-8-sig') if raw[:3] == b'\xef\xbb\xbf' else raw.decode('utf-8'))

def save_json(path, data, bom=False):
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if bom:
        path.write_bytes(b'\xef\xbb\xbf' + text.encode('utf-8'))
    else:
        path.write_bytes(text.encode('utf-8'))

bym = load_json(BYM_PATH)
easton = load_json(EASTON_PATH)

bym_bom = BYM_PATH.read_bytes()[:3] == b'\xef\xbb\xbf'
easton_bom = EASTON_PATH.read_bytes()[:3] == b'\xef\xbb\xbf'

# Build index by ID for fast lookup
bym_idx = {e["id"]: e for e in bym}
easton_idx = {e["id"]: e for e in easton}

# ═══════════════════════════════════════════════════
# V3-A: BYM Désambiguïsation — gras sur identifiants
# ═══════════════════════════════════════════════════
print("── V3-A: BYM désambiguïsation → gras ──")

# For each entry: list of (old_text, new_text) replacements
# Bold the shortest identifying phrase at the start of each person section
BYM_DISAMBIG = {
    # YAACOV — 5 persons
    "bym-000479": [
        ("Yaacov (jacob), fils de Yitzhak (Isaac) et de ribqah (rébecca) et frère jumeau d'ésav\n(ésaü).",
         "**Yaacov (Jacob), fils de Yitzhak (Isaac) et de Ribqah (Rébecca)** et frère jumeau d'Ésav\n(Ésaü)."),
        ("Yaacov (Jacques), fils de zabdi (zébédée) et frère de yohanan (Jean).",
         "**Yaacov (Jacques), fils de Zabdi (Zébédée)** et frère de Yohanan (Jean)."),
        ("Yaacov (Jacques), fils d' alphaios (alphée), un des douze apôtres",
         "**Yaacov (Jacques), fils d'Alphaios (Alphée),** un des douze apôtres"),
        ("Yaacov (Jacques), frère du Seigneur et apôtre",
         "**Yaacov (Jacques), frère du Seigneur** et apôtre"),
        ("Yaacov (Jacques), frère de Yéhouda (jude) Non l'iscariot",
         "**Yaacov (Jacques), frère de Yéhouda (Jude)** Non l'iscariot"),
    ],
    # MYRIAM — 4 persons
    "bym-000315": [
        ("sœur de Moshé (Moïse) et d' Aaron, pro phétesse",
         "**Sœur de Moshé (Moïse) et d'Aaron,** pro phétesse"),
        ("mère de Yéhoshoua (jésus):",
         "**Mère de Yéhoshoua (Jésus) :**"),
        ("myriam de Béthanie :",
         "**Myriam de Béthanie :**"),
        ("myriam-magdeleine (marie de magdala) :",
         "**Myriam-Magdeleine (Marie de Magdala) :**"),
    ],
    # YÉHOUDA — 4 persons
    "bym-000488": [
        ("fils de Yaacov (jacob) et léah",
         "**Fils de Yaacov (Jacob) et Léah,**"),
        ("un des douze apôtres, non l'iscariot",
         "**Un des douze apôtres, non l'iscariot,**"),
        ("prophète également appelé barsabas",
         "**Prophète également appelé Barsabas,**"),
        ("frère du Seigneur, auteur d'une épître",
         "**Frère du Seigneur,** auteur d'une épître"),
    ],
    # YOHANAN — 2 persons
    "bym-000503": [
        ("fils de zabdi (zébédée), frère de Yaacov (Jacques) et disciple aimé du Seigneur.",
         "**Fils de Zabdi (Zébédée), frère de Yaacov (Jacques) et disciple aimé du Seigneur.**"),
        ("fils de zekaryah (Zacharie) et éliysheba (élisabeth), cousin de Yéhoshoua (jésus).",
         "**Fils de Zekaryah (Zacharie) et Éliysheba (Élisabeth), cousin de Yéhoshoua (Jésus).**"),
    ],
    # YOSSEF — 2 persons
    "bym-000508": [
        ("fils de Yaacov et rachel.",
         "**Fils de Yaacov et Rachel.**"),
        ("fils d'éli, charpentier originaire de la tribu de Yéhouda.",
         "**Fils d'Éli, charpentier originaire de la tribu de Yéhouda.**"),
    ],
    # CHANANYAH — 4 persons
    "bym-000096": [
        ("le pieux ami de daniye'l que neboukad netsar appela shadrac",
         "**Le pieux ami de Daniye'l** que Neboukad netsar appela Shadrac"),
        ("grand-prêtre, beau-père de kaïaphas (Caïphe).",
         "**Grand-prêtre, beau-père de Kaïaphas (Caïphe).**"),
        ("chrétien ayant vendu un champ avec sa femme saphira",
         "**Chrétien ayant vendu un champ avec sa femme Saphira**"),
        ("homme pieux vivant à damas",
         "**Homme pieux vivant à Damas**"),
    ],
    # ZEKARYAH — 3 persons
    "bym-000510": [
        ("fils de yarobam (Jéroboam), roi d'Israël",
         "**Fils de Yarobam (Jéroboam), roi d'Israël,**"),
        ("prophète et prêtre, fils de berekyah",
         "**Prophète et prêtre, fils de Berekyah**"),
        ("prêtre et père de yohanan le baptiste (Jean baptiste)",
         "**Prêtre et père de Yohanan le baptiste (Jean-Baptiste)**"),
    ],
    # PHILIPPOS — 2 persons
    "bym-000363": [
        ("Homme de bethsaïda, il fut l'un des douze apôtres choisis par Yéhoshoua.",
         "**Homme de Bethsaïda, l'un des douze apôtres** choisis par Yéhoshoua."),
        ("un des sept diacres élus au sein de l'as semblée de Yeroushalaim (Jérusalem).",
         "**Un des sept diacres élus au sein de l'assemblée de Yeroushalaim (Jérusalem).**"),
    ],
    # MENASHÈ — 2 persons
    "bym-000295": [
        ("fils aîné de yossef et d' asnath",
         "**Fils aîné de Yossef et d'Asnath,**"),
        ("fils d'hizqiyah (Ézéchias) et de hephtsiba",
         "**Fils d'Hizqiyah (Ézéchias) et de Hephtsiba,**"),
    ],
    # YÉHOSHOUA — 2 persons
    "bym-000487": [
        ("fils de noun de la tribu d'Éphraïm",
         "**Fils de Noun de la tribu d'Éphraïm,**"),
        ("Fils d'humain et fils d'Elohîm, Yéhoshoua (jésus) est l'Elohîm vivant manifesté en chair.",
         "**Fils d'humain et fils d'Elohîm,** Yéhoshoua (Jésus) est l'Elohîm vivant manifesté en chair."),
    ],
}

v3a_count = 0
v3a_replacements = 0

for entry_id, replacements in BYM_DISAMBIG.items():
    entry = bym_idx.get(entry_id)
    if not entry:
        print(f"  ⚠ Entrée {entry_id} introuvable!")
        continue

    d = entry["definition"]
    applied = 0

    for old_text, new_text in replacements:
        if old_text in d:
            d = d.replace(old_text, new_text, 1)
            applied += 1
        else:
            # Try case-insensitive search for debugging
            print(f"  ⚠ {entry_id}: texte non trouvé: «{old_text[:60]}...»")

    if applied > 0:
        entry["definition"] = d
        v3a_count += 1
        v3a_replacements += applied
        print(f"  ✓ {entry['mot']}: {applied} sections en gras")

print(f"\n  Total V3-A: {v3a_count} entrées, {v3a_replacements} sections")

# ═══════════════════════════════════════════════════
# V3-B: BYM AMOUR — gras sur en-têtes de section
# ═══════════════════════════════════════════════════
print("\n── V3-B: BYM AMOUR → gras en-têtes ──")

v3b_count = 0

amour = bym_idx.get("bym-000028")
if amour:
    d = amour["definition"]
    replacements_b = [
        ("les termes hébreux désignant l'amour :",
         "**Les termes hébreux désignant l'amour :**"),
        ("- Les termes grecs désignant l'amour :",
         "- **Les termes grecs désignant l'amour :**"),
    ]
    applied = 0
    for old_text, new_text in replacements_b:
        if old_text in d:
            d = d.replace(old_text, new_text, 1)
            applied += 1
        else:
            print(f"  ⚠ AMOUR: texte non trouvé: «{old_text}»")

    if applied > 0:
        amour["definition"] = d
        v3b_count = applied
        print(f"  ✓ AMOUR: {applied} en-têtes en gras")

print(f"  Total V3-B: {v3b_count} en-têtes")

# ═══════════════════════════════════════════════════
# V3-C: Easton inline (N) — 4 entrées sûres
# ═══════════════════════════════════════════════════
print("\n── V3-C: Easton inline (N) → gras ──")

v3c_count = 0
v3c_markers = 0

# André (easton-000236): inline (1) (2) (3) in final sentence
andre = easton_idx.get("easton-000236")
if andre:
    d = andre["definition"]
    # Bold the three inline markers in the last sentence
    replacements_c = [
        (", (1) Pierre", ", **(1)** Pierre"),
        ("; (2) le jeune garçon", "; **(2)** le jeune garçon"),
        ("; et (3) certains Grecs", "; et **(3)** certains Grecs"),
    ]
    applied = 0
    for old_t, new_t in replacements_c:
        if old_t in d:
            d = d.replace(old_t, new_t, 1)
            applied += 1
    if applied > 0:
        andre["definition"] = d
        v3c_count += 1
        v3c_markers += applied
        print(f"  ✓ André: {applied} marqueurs")

# Ésaïe (easton-001895): section markers (1.) through (5.)
esaie = easton_idx.get("easton-001895")
if esaie:
    d = esaie["definition"]
    # Bold all (N.) markers — these are person/meaning delimiters
    replacements_c = [
        ("). (1.) Fils d'Amots", "). **(1.)** Fils d'Amots"),
        ("\n\n(2.) L'un des chefs", "\n\n**(2.)** L'un des chefs"),
        ("\n\n(3.) Un lévite", "\n\n**(3.)** Un lévite"),
        ("(4.) Esdras", "**(4.)** Esdras"),
        ("(5.) Néh.", "**(5.)** Néh."),
    ]
    applied = 0
    for old_t, new_t in replacements_c:
        if old_t in d:
            d = d.replace(old_t, new_t, 1)
            applied += 1
        else:
            print(f"  ⚠ Ésaïe: texte non trouvé: «{old_t[:50]}»")
    if applied > 0:
        esaie["definition"] = d
        v3c_count += 1
        v3c_markers += applied
        print(f"  ✓ Ésaïe: {applied} marqueurs")

# Repentance (easton-003105): two numbered lists
repentance = easton_idx.get("easton-003105")
if repentance:
    d = repentance["definition"]
    # First list: Greek words (1) (2) (3)
    # Second list: components of repentance (1) (2) (3) (4)
    # Be precise with context to avoid wrong replacements
    replacements_c = [
        # First list
        ("repentance. (1) Le verbe", "repentance. **(1)** Le verbe"),
        ("\n\n(2) Metanoeo,", "\n\n**(2)** Metanoeo,"),
        ("avec (3) le substantif", "avec **(3)** le substantif"),
        # Second list
        ("consiste en (1) un véritable", "consiste en **(1)** un véritable"),
        ("péché ; (2) une appréhension", "péché ; **(2)** une appréhension"),
        ("; (3) une haine effective", "; **(3)** une haine effective"),
        ("; et (4) un effort", "; et **(4)** un effort"),
    ]
    applied = 0
    for old_t, new_t in replacements_c:
        if old_t in d:
            d = d.replace(old_t, new_t, 1)
            applied += 1
        else:
            print(f"  ⚠ Repentance: texte non trouvé: «{old_t[:50]}»")
    if applied > 0:
        repentance["definition"] = d
        v3c_count += 1
        v3c_markers += applied
        print(f"  ✓ Repentance: {applied} marqueurs")

# Bonnes œuvres (easton-003835): inline (1) (2.) (3)
bonnes = easton_idx.get("easton-003835")
if bonnes:
    d = bonnes["definition"]
    replacements_c = [
        ("quand, (1) elles jaillissent", "quand, **(1)** elles jaillissent"),
        ("(2.) Les bonnes œuvres ont la gloire", "**(2.)** Les bonnes œuvres ont la gloire"),
        ("; et (3) elles ont la volonté", "; et **(3)** elles ont la volonté"),
    ]
    applied = 0
    for old_t, new_t in replacements_c:
        if old_t in d:
            d = d.replace(old_t, new_t, 1)
            applied += 1
        else:
            print(f"  ⚠ Bonnes œuvres: texte non trouvé: «{old_t[:50]}»")
    if applied > 0:
        bonnes["definition"] = d
        v3c_count += 1
        v3c_markers += applied
        print(f"  ✓ Bonnes œuvres: {applied} marqueurs")

print(f"\n  Total V3-C: {v3c_count} entrées, {v3c_markers} marqueurs")

# ═══════════════════════════════════════════════════
# Update definition_length
# ═══════════════════════════════════════════════════
for dataset in [bym, easton]:
    for entry in dataset:
        entry["definition_length"] = len(entry.get("definition", ""))

# ═══════════════════════════════════════════════════
# Save
# ═══════════════════════════════════════════════════
print("\n── Sauvegarde ──")
save_json(BYM_PATH, bym, bom=bym_bom)
print(f"  {BYM_PATH.name}")
save_json(EASTON_PATH, easton, bom=easton_bom)
print(f"  {EASTON_PATH.name}")

# ═══════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════
total_entries = v3a_count + (1 if v3b_count > 0 else 0) + v3c_count
total_markers = v3a_replacements + v3b_count + v3c_markers
print(f"\n══════════════════════════════════════")
print(f"  RÉSUMÉ GRAS STRUCTUREL — VAGUE 3")
print(f"══════════════════════════════════════")
print(f"  V3-A BYM désambiguïsation:  {v3a_count} entrées, {v3a_replacements} sections")
print(f"  V3-B BYM AMOUR en-têtes:    {v3b_count} en-têtes")
print(f"  V3-C Easton inline (N):     {v3c_count} entrées, {v3c_markers} marqueurs")
print(f"  ──────────────────────────────────")
print(f"  TOTAL: {total_entries} entrées, {total_markers} modifications")
print(f"══════════════════════════════════════")

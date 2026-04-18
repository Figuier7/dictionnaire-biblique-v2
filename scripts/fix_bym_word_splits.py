#!/usr/bin/env python3
"""
fix_bym_word_splits.py — Corrige les scissions de mots (OCR/PDF) dans BYM.

Les définitions du BYM contiennent des mots coupés par un espace au milieu,
artefacts de l'extraction PDF originale (coupure de ligne → espace).

Approche : dictionnaire exhaustif de toutes les scissions connues,
appliquées par remplacement exact, insensible à la casse pour la recherche
mais préservant la casse de la correction.
"""

import json
import re
import sys
import io
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(r"C:\Users\caeng\OneDrive\Documents\A l'ombre du figuier\dictionnaire-biblique-main")
BYM_PATH = BASE / "uploads" / "dictionnaires" / "bym" / "bym-lexicon.entries.json"

def load_json(path):
    raw = path.read_bytes()
    return json.loads(raw.decode('utf-8-sig') if raw[:3] == b'\xef\xbb\xbf' else raw.decode('utf-8'))

def save_json(path, data, bom=False):
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if bom:
        path.write_bytes(b'\xef\xbb\xbf' + text.encode('utf-8'))
    else:
        path.write_bytes(text.encode('utf-8'))

# ═══════════════════════════════════════════════════
# Dictionnaire de scissions → corrections
# ═══════════════════════════════════════════════════
# Format : "texte scindé" → "texte corrigé"
# La recherche est sensible à la casse sauf indication contraire.
# Ordonné du plus long au plus court pour éviter les collisions.

SPLITS = {
    # ── Noms propres ──
    "yého shoua": "yéhoshoua",
    "yé hoshoua": "yéhoshoua",
    "yé houda": "yéhouda",
    "jéru salem": "jérusalem",
    "jérusa lem": "jérusalem",
    "jour dain": "jourdain",
    "ra chel": "rachel",
    "sha phat": "shaphat",
    "aa ron": "aaron",
    "bar nabas": "barnabas",
    "bar talmay": "bartalmay",
    "barthé lemy": "barthélemy",
    "be nyamin": "benyamin",
    "benja min": "benjamin",
    "benya mite": "benyamite",
    "cor neil": "corneil",
    "dar yavesh": "daryavesh",
    "jo sué": "josué",
    "ma nassé": "manassé",
    "mala chie": "malachie",
    "mat thieu": "matthieu",
    "miy kayah": "miykayah",
    "mor dekay": "mordekay",
    "na ziyr": "naziyr",
    "sal manasar": "salmanasar",
    "ye hezkel": "yehezkel",
    "ye huwdah": "yehuwdah",
    "za bulon": "zabulon",
    "ézé quiel": "ézéquiel",
    "neboukad netsar": "neboukadnetsar",

    # ── Termes bibliques / hébreux / grecs ──
    "elo hîm": "elohîm",
    "shab bat": "shabbat",
    "apo kalupsis": "apokalupsis",
    "dia theke": "diatheke",
    "dou los": "doulos",
    "ano then": "anothen",
    "gil luwl": "gilluwl",
    "pro phetes": "prophetes",

    # ── Mots courants français (2+ occurrences) ──
    "assem blée": "assemblée",
    "as semblée": "assemblée",
    "ser vice": "service",
    "ser vices": "services",
    "al liance": "alliance",
    "couver ture": "couverture",
    "ac compagné": "accompagné",
    "ac compagna": "accompagna",
    "ac compli": "accompli",
    "ac cordée": "accordée",
    "ac cordé": "accordé",
    "ac corda": "accorda",
    "ac cusateur": "accusateur",
    "ac tion": "action",
    "appar tenant": "appartenant",
    "apparte nance": "appartenance",
    "campe ment": "campement",
    "chré tiens": "chrétiens",
    "chré tien": "chrétien",
    "com pagnon": "compagnon",
    "com mencé": "commencé",
    "contem porain": "contemporain",
    "contem porains": "contemporains",
    "cou ronne": "couronne",
    "domes tique": "domestique",
    "do mestique": "domestique",
    "fon dée": "fondée",
    "gou verneur": "gouverneur",
    "gouver neur": "gouverneur",
    "généra lement": "généralement",
    "générale ment": "généralement",
    "géné ralement": "généralement",
    "inté rieur": "intérieur",
    "inté rieure": "intérieure",
    "pro phétesse": "prophétesse",
    "terri toire": "territoire",
    "tra duit": "traduit",
    "tra ditions": "traditions",
    "tradi tion": "tradition",
    "évan géliste": "évangéliste",

    # ── Mots courants français (1 occurrence) ──
    "pré sentée": "présentée",
    "pré sent": "présent",
    "pré sente": "présente",
    "ado rateur": "adorateur",
    "ado rateurs": "adorateurs",
    "an nonce": "annonce",
    "an noncé": "annoncé",
    "ani maux": "animaux",
    "anti quité": "antiquité",
    "asso ciation": "association",
    "ave nant": "avenant",
    "be lette": "belette",
    "bri seurs": "briseurs",
    "ca tholique": "catholique",
    "caracté ris": "caractéris",
    "cer taines": "certaines",
    "choi sit": "choisit",
    "compensa tion": "compensation",
    "conduc teurs": "conducteurs",
    "connais sance": "connaissance",
    "conser vateur": "conservateur",
    "cor rompre": "corrompre",
    "cé lébrer": "célébrer",
    "diff érence": "différence",
    "direc tement": "directement",
    "dis cours": "discours",
    "divi nité": "divinité",
    "droi ture": "droiture",
    "déploie ment": "déploiement",
    "em menant": "emmenant",
    "em pêcher": "empêcher",
    "expéri menter": "expérimenter",
    "fi gurait": "figurait",
    "finale ment": "finalement",
    "grou pement": "groupement",
    "habita tion": "habitation",
    "hau teur": "hauteur",
    "hono rable": "honorable",
    "hé braïque": "hébraïque",
    "hé ros": "héros",
    "hé roïque": "héroïque",
    "im pulsé": "impulsé",
    "in vestigation": "investigation",
    "indi gnité": "indignité",
    "infi délité": "infidélité",
    "inon dation": "inondation",
    "intermé diaire": "intermédiaire",
    "li bertés": "libertés",
    "ma nière": "manière",
    "mau vaise": "mauvaise",
    "no tamment": "notamment",
    "nou velle": "nouvelle",
    "obs curité": "obscurité",
    "obs tacle": "obstacle",
    "ori ginaire": "originaire",
    "ouverte ment": "ouvertement",
    "per pétuité": "perpétuité",
    "per sonne": "personne",
    "por tion": "portion",
    "pro fesseur": "professeur",
    "prédomi nance": "prédominance",
    "qua lifié": "qualifié",
    "quar tier": "quartier",
    "ra pide": "rapide",
    "re bellés": "rebellés",
    "re commandations": "recommandations",
    "re latifs": "relatifs",
    "re pos": "repos",
    "re prises": "reprises",
    "re trouve": "retrouve",
    "ren contre": "rencontre",
    "res pectivement": "respectivement",
    "res ponsable": "responsable",
    "res semblant": "ressemblant",
    "réfor mateur": "réformateur",
    "secré taire": "secrétaire",
    "sei gneur": "seigneur",
    "si tuée": "située",
    "sim plement": "simplement",
    "sor tie": "sortie",
    "spécia lement": "spécialement",
    "suc cession": "succession",
    "trans gression": "transgression",
    "vic time": "victime",
    "visita tion": "visitation",
    "édi fient": "édifient",
    "égale ment": "également",

    # ── Scissions supplémentaires trouvées dans l'audit ──
    "compas Sion": "compassion",
    "pro phétique": "prophétique",
    "pro phète": "prophète",
    "pro phéties": "prophéties",
    "tra vail": "travail",
    "rébel lion": "rébellion",
    "discerne ment": "discernement",
    "fa mille": "famille",
    "shadrac da": "shadrac da",  # skip — this is "shadrac" + "da." (book reference)
}

# Remove the shadrac entry (not a real split)
del SPLITS["shadrac da"]

# ═══════════════════════════════════════════════════
# Multi-line splits (word broken across lines with \n)
# ═══════════════════════════════════════════════════
MULTILINE_SPLITS = {
    "elo\nhîm": "elohîm",
    "elo-\nhîm": "elohîm",
}

# ═══════════════════════════════════════════════════
# Apply corrections
# ═══════════════════════════════════════════════════
print("── Correction des scissions de mots dans BYM ──\n")

bym = load_json(BYM_PATH)
bom = BYM_PATH.read_bytes()[:3] == b'\xef\xbb\xbf'

total_fixes = 0
entries_fixed = 0
fix_log = []

# Sort splits by length (longest first) to avoid partial matches
sorted_splits = sorted(SPLITS.items(), key=lambda x: -len(x[0]))

for entry in bym:
    d = entry.get("definition", "")
    if not d:
        continue

    original = d
    entry_fixes = []

    # Apply single-line splits (case-insensitive search, preserve context)
    for split_text, correction in sorted_splits:
        # Build case-insensitive pattern with word-ish boundaries
        # We use re.IGNORECASE and match the exact split pattern
        pattern = re.compile(re.escape(split_text), re.IGNORECASE)
        matches = list(pattern.finditer(d))
        if matches:
            for match in reversed(matches):  # reverse to preserve positions
                found = match.group()
                # Preserve leading case: if found starts uppercase, capitalize correction
                if found[0].isupper() and correction[0].islower():
                    fixed = correction[0].upper() + correction[1:]
                elif found[0].islower() and correction[0].islower():
                    fixed = correction
                else:
                    fixed = correction
                # Check for ALL CAPS case
                if found.isupper():
                    fixed = correction.upper()
                d = d[:match.start()] + fixed + d[match.end():]
                entry_fixes.append(f"  «{found}» → «{fixed}»")

    # Apply multi-line splits
    for split_text, correction in MULTILINE_SPLITS.items():
        if split_text in d:
            count = d.count(split_text)
            d = d.replace(split_text, correction)
            for _ in range(count):
                entry_fixes.append(f"  «{split_text.replace(chr(10), '⏎')}» → «{correction}»")

    if d != original:
        entry["definition"] = d
        entry["definition_length"] = len(d)
        entries_fixed += 1
        n = len(entry_fixes)
        total_fixes += n
        fix_log.append((entry["id"], entry["mot"], n, entry_fixes))
        if n <= 5:
            print(f"  ✓ {entry['mot']} ({entry['id']}): {n} correction(s)")
            for f in entry_fixes:
                print(f"    {f}")
        else:
            print(f"  ✓ {entry['mot']} ({entry['id']}): {n} corrections")
            for f in entry_fixes[:3]:
                print(f"    {f}")
            print(f"    ... et {n-3} autres")

# ═══════════════════════════════════════════════════
# Save
# ═══════════════════════════════════════════════════
print(f"\n── Sauvegarde ──")
save_json(BYM_PATH, bym, bom=bom)
print(f"  {BYM_PATH.name}")

# ═══════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════
print(f"\n══════════════════════════════════════════════")
print(f"  RÉSUMÉ — SCISSIONS DE MOTS BYM")
print(f"══════════════════════════════════════════════")
print(f"  Entrées corrigées:    {entries_fixed}")
print(f"  Corrections totales:  {total_fixes}")
print(f"  Patterns utilisés:    {len(SPLITS) + len(MULTILINE_SPLITS)}")
print(f"══════════════════════════════════════════════")

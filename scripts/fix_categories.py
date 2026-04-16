#!/usr/bin/env python3
"""Fix categorization errors in concepts.json for evenement, institution, doctrine categories."""
import json
import unicodedata
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "uploads" / "dictionnaires"

with open(BASE / "concepts.json", "r", encoding="utf-8-sig") as f:
    concepts = json.load(f)

with open(BASE / "smith" / "smith.entries.json", "r", encoding="utf-8-sig") as f:
    smith_entries = json.load(f)
smith_by_id = {e["id"]: e for e in smith_entries}

def normalize(s):
    s = s.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s

# Known word lists for heuristic matching
MONTH_NAMES = {"ab", "adar", "abib", "chisleu", "ethanim", "marcheshvan", "sivan", "tebeth", "elul", "nisan", "bul"}
TIME_WORDS = ["heure", "hour", "jour", "day", "nuit", "night", "mois", "month", "chronolog", "semaine", "week"]
ANIMAL_WORDS = ["araignee", "spider", "belette", "weasel", "engoulevent", "nighthawk", "lezard", "lizard",
                "tortue", "turtle", "greyhound", "poux", "lice", "chameau", "camel"]
OBJECT_WORDS = ["arrows", "fleche", "battleaxe", "hache", "couch", "divan", "clou", "nail", "massue", "club",
                "chariot", "wagon", "rasoir", "razor", "candlestick", "chandelier", "censer", "encensoir",
                "charger", "chest", "coffre", "firepan", "banner", "banniere", "tente", "tent", "corsage"]
FOOD_WORDS = ["food", "nourriture", "vinaigre", "vinegar", "dime", "dixieme", "tithe"]
CRAFT_WORDS = ["fuller", "foulon", "forgeron", "carving", "sculpture", "ceiling", "plafond", "tissage", "weaving"]

# Smith definition heuristics
PERSON_SIGNALS = ["fils de", "fille de", "pere de", "mere de", "descendant", "roi de", "reine",
                  "prophete", "pretre", "sacrificateur", "apotre", "disciple", "prince",
                  "levite", "famille de", "souverain", "gouverneur", "pharisien", "grand pretre",
                  "epouse de", "femme de", "frere de", "chef de"]
PLACE_SIGNALS = ["ville", "cite", "mont ", "montagne", "riviere", "fleuve", "vallee", "plaine",
                 "region ", "pays ", "territoire", "desert", "lac ", "mer "]
PEOPLE_SIGNALS = ["peuple", "nation", "habitants", "descendants de", "tribu", "clan"]
DIVINE_SIGNALS = ["divinite", "dieu ", "idole", "ange ", "seraph", "cherubin"]
BOOK_SIGNALS = ["livre de", "epitre", "evangile", "prophecies", "prophetie", "psaume", "pentateuque"]
RITE_SIGNALS = ["ceremonie", "rituel", "offrande", "sacrifice ", "purification", "circoncision",
                "consecration", "onction", "benediction", "salutation", "prosternation"]

corrections = {}
fix_log = []

for concept in concepts:
    cid = concept.get("concept_id", "")
    cat = concept.get("category", "")
    label = concept.get("label", "")
    label_restore = concept.get("label_restore", "")
    label_norm = normalize(label)
    restore_norm = normalize(label_restore) if label_restore else ""

    if cat not in ("evenement", "institution", "doctrine"):
        continue

    # 1. Month names
    if label_norm in MONTH_NAMES or restore_norm in MONTH_NAMES:
        corrections[cid] = "mesures_et_temps"
        fix_log.append(f"{cid}: {label} ({cat} -> mesures_et_temps) [month]")
        continue

    # 2. Time concepts
    if any(t in label_norm or t in restore_norm for t in TIME_WORDS):
        corrections[cid] = "mesures_et_temps"
        fix_log.append(f"{cid}: {label} ({cat} -> mesures_et_temps) [time]")
        continue

    # 3. Animals
    if any(a in label_norm for a in ANIMAL_WORDS):
        corrections[cid] = "animal"
        fix_log.append(f"{cid}: {label} ({cat} -> animal) [animal]")
        continue

    # 4. Objects
    if any(o in label_norm for o in OBJECT_WORDS):
        corrections[cid] = "objets_et_vetements"
        fix_log.append(f"{cid}: {label} ({cat} -> objets_et_vetements) [object]")
        continue

    # 5. Food
    if any(f in label_norm for f in FOOD_WORDS):
        corrections[cid] = "alimentation_et_agriculture"
        fix_log.append(f"{cid}: {label} ({cat} -> alimentation_et_agriculture) [food]")
        continue

    # 6. Crafts
    if any(c in label_norm for c in CRAFT_WORDS):
        corrections[cid] = "matiere"
        fix_log.append(f"{cid}: {label} ({cat} -> matiere) [craft]")
        continue

    # 7. Check Smith definition for person/place/people signals
    entries = concept.get("entries", [])
    smith_entry = None
    for e in entries:
        if e.get("dictionary") == "smith":
            smith_entry = smith_by_id.get(e.get("entry_id"))
            break

    if smith_entry:
        defn = normalize(smith_entry.get("definition", "")[:600])

        is_person = any(s in defn for s in PERSON_SIGNALS)
        is_place = any(s in defn for s in PLACE_SIGNALS)
        is_people = any(s in defn for s in PEOPLE_SIGNALS) and not is_person
        is_divine = any(s in defn for s in DIVINE_SIGNALS)
        is_book = any(s in defn for s in BOOK_SIGNALS)
        is_rite = any(s in defn for s in RITE_SIGNALS)

        if is_person and not is_place:
            corrections[cid] = "personnage"
            fix_log.append(f"{cid}: {label} ({cat} -> personnage) [smith-defn]")
        elif is_place and not is_person:
            corrections[cid] = "lieu"
            fix_log.append(f"{cid}: {label} ({cat} -> lieu) [smith-defn]")
        elif is_people:
            corrections[cid] = "peuple"
            fix_log.append(f"{cid}: {label} ({cat} -> peuple) [smith-defn]")
        elif is_divine:
            corrections[cid] = "etre_divin"
            fix_log.append(f"{cid}: {label} ({cat} -> etre_divin) [smith-defn]")
        elif is_book:
            corrections[cid] = "livre_biblique"
            fix_log.append(f"{cid}: {label} ({cat} -> livre_biblique) [smith-defn]")
        elif is_rite:
            corrections[cid] = "rite"
            fix_log.append(f"{cid}: {label} ({cat} -> rite) [smith-defn]")

# Apply
applied = 0
for concept in concepts:
    cid = concept.get("concept_id", "")
    if cid in corrections:
        concept["category"] = corrections[cid]
        applied += 1

# Save
with open(BASE / "concepts.json", "w", encoding="utf-8") as f:
    json.dump(concepts, f, ensure_ascii=False, indent=2)

print(f"Total corrections applied: {applied}")
print(f"\nBy target category:")
for cat, count in Counter(corrections.values()).most_common():
    print(f"  {cat}: {count}")

print(f"\nAll fixes:")
for line in fix_log:
    print(f"  {line}")

# Show remaining uncorrected in evenement/institution/doctrine
remaining = {"evenement": 0, "institution": 0, "doctrine": 0}
for concept in concepts:
    cat = concept.get("category", "")
    if cat in remaining:
        remaining[cat] += 1
print(f"\nRemaining after fix:")
for cat, count in remaining.items():
    print(f"  {cat}: {count}")

#!/usr/bin/env python3
"""
Link Smith entries to existing concepts or create new concepts for unmatched ones.
Updates concepts.json and concept-entry-links.json.
"""
import json
import re
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "uploads" / "dictionnaires"

def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize(s):
    """Normalize a string for matching: lowercase, strip accents, remove punctuation."""
    s = s.lower().strip()
    # Remove content in parentheses
    s = re.sub(r'\s*\(.*?\)', '', s)
    # Normalize unicode
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    # Remove punctuation except hyphens
    s = re.sub(r"[^a-z0-9\s\-]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def make_slug(s):
    """Create a URL-safe slug."""
    s = s.lower().strip()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s

def make_concept_id(title):
    """Create concept_id from English title."""
    s = title.lower().strip()
    s = re.sub(r'\s*\(.*?\)', '', s)  # remove parenthetical
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s

def guess_category(title, definition=""):
    """Guess category from title/definition patterns."""
    title_lower = title.lower()
    def_lower = definition[:500].lower() if definition else ""

    if re.search(r'\b(fils|fille|père|mère|frère|soeur|famille|descendant|tribu|clan)\b', def_lower):
        if re.search(r'\b(tribu|clan|peuple|nation)\b', def_lower):
            return "peuples_tribus"

    if re.search(r'\b(ville|cité|village|région|pays|montagne|mont|vallée|plaine|fleuve|rivière|mer|lac|désert|île)\b', def_lower):
        return "lieux"

    if re.search(r'\b(roi|reine|prêtre|prophète|juge|apôtre|disciple)\b', def_lower):
        return "personnages"

    if re.search(r'\b(Gen\.|Ex\.|Lev\.|Num\.|Deut\.|Jos\.|Jug\.|Ruth|Sam\.|Rois|Chr\.|Esd\.|Néh\.|Est\.)\b', def_lower):
        pass  # references don't determine category alone

    # Check if it's a person name (capitalized, short)
    if len(title.split()) <= 3 and title[0].isupper():
        if re.search(r'\b(fils de|fille de|père de|descendant)\b', def_lower):
            return "personnages"

    return "non_classifie"

def get_letter(title):
    s = unicodedata.normalize('NFD', title.strip())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    for c in s:
        if c.isalpha():
            return c.upper()
    return "#"

def main():
    print("Loading data...")
    smith_entries = load_json(BASE / "smith" / "smith.entries.json")
    concepts = load_json(BASE / "concepts.json")
    links = load_json(BASE / "concept-entry-links.json")

    # Also load easton for cross-reference
    easton_entries = load_json(BASE / "easton" / "easton.entries.json")

    print(f"  Smith entries: {len(smith_entries)}")
    print(f"  Concepts: {len(concepts)}")
    print(f"  Links: {len(links)}")
    print(f"  Easton entries: {len(easton_entries)}")

    # Build indexes for matching
    # 1. Concept by normalized label
    concept_by_label = {}
    concept_by_id = {}
    for c in concepts:
        concept_by_id[c['concept_id']] = c
        norm = normalize(c['label'])
        if norm not in concept_by_label:
            concept_by_label[norm] = c
        # Also index by display_titles
        dt = c.get('display_titles', {})
        for key in ['primary', 'secondary']:
            if key in dt and dt[key]:
                n2 = normalize(dt[key])
                if n2 not in concept_by_label:
                    concept_by_label[n2] = c
        # Also index by aliases
        for alias in c.get('aliases', []):
            na = normalize(alias)
            if na not in concept_by_label:
                concept_by_label[na] = c

    # 2. Easton source_title_en → concept_id (via links)
    easton_by_id = {e['id']: e for e in easton_entries}
    easton_title_to_concept = {}
    for link in links:
        eid = link['entry_id']
        if eid.startswith('easton-') and eid in easton_by_id:
            en_title = normalize(easton_by_id[eid].get('source_title_en', ''))
            if en_title:
                easton_title_to_concept[en_title] = link['concept_id']
            # Also French title
            fr_title = normalize(easton_by_id[eid].get('mot', ''))
            if fr_title:
                easton_title_to_concept[fr_title] = link['concept_id']

    print(f"  Concept label index: {len(concept_by_label)} entries")
    print(f"  Easton title->concept index: {len(easton_title_to_concept)} entries")

    # Match Smith entries
    matched = 0
    created = 0
    new_links = []
    new_concepts = []
    used_concept_ids = set(c['concept_id'] for c in concepts)

    strategies_count = {}

    for se in smith_entries:
        smith_id = se['id']
        en_title = se.get('source_title_en', se['mot'])
        fr_title = se.get('mot', '')
        norm_en = normalize(en_title)
        norm_fr = normalize(fr_title)

        concept_id = None
        strategy = None
        confidence = 0.0

        # Strategy 1: Exact match on English title via Easton cross-reference
        if norm_en in easton_title_to_concept:
            concept_id = easton_title_to_concept[norm_en]
            strategy = "english_title_via_easton"
            confidence = 0.95

        # Strategy 2: Match on concept label (normalized)
        if not concept_id and norm_en in concept_by_label:
            concept_id = concept_by_label[norm_en]['concept_id']
            strategy = "concept_label_exact"
            confidence = 0.90

        # Strategy 3: Match French title to concept label
        if not concept_id and norm_fr in concept_by_label:
            concept_id = concept_by_label[norm_fr]['concept_id']
            strategy = "french_label_match"
            confidence = 0.85

        # Strategy 4: Match French title via easton index
        if not concept_id and norm_fr in easton_title_to_concept:
            concept_id = easton_title_to_concept[norm_fr]
            strategy = "french_title_via_easton"
            confidence = 0.85

        # Strategy 5: Base form match (remove trailing numbers, ", The", etc.)
        if not concept_id:
            base_en = re.sub(r',?\s*(the|a|an)$', '', norm_en).strip()
            base_en = re.sub(r'\s+\d+$', '', base_en).strip()
            if base_en != norm_en:
                if base_en in easton_title_to_concept:
                    concept_id = easton_title_to_concept[base_en]
                    strategy = "english_base_via_easton"
                    confidence = 0.80
                elif base_en in concept_by_label:
                    concept_id = concept_by_label[base_en]['concept_id']
                    strategy = "concept_label_base"
                    confidence = 0.80

        if concept_id and concept_id in concept_by_id:
            matched += 1
            # Add to existing concept's entries
            concept = concept_by_id[concept_id]
            # Check if smith entry already exists
            existing_ids = {e['entry_id'] for e in concept['entries']}
            if smith_id not in existing_ids:
                concept['entries'].append({
                    "entry_id": smith_id,
                    "dictionary": "smith",
                    "display_role": "detailed_reference",
                    "is_primary_for_role": True
                })
        else:
            # Create new concept for this Smith entry
            created += 1
            strategy = "new_concept"
            confidence = 1.0

            cid = make_concept_id(en_title)
            # Ensure unique
            orig_cid = cid
            counter = 2
            while cid in used_concept_ids:
                cid = f"{orig_cid}_{counter}"
                counter += 1
            used_concept_ids.add(cid)
            concept_id = cid

            letter = get_letter(fr_title or en_title)
            category = guess_category(en_title, se.get('definition', ''))

            new_concept = {
                "concept_id": cid,
                "label": fr_title or en_title,
                "label_restore": en_title if fr_title != en_title else "",
                "display_titles": {
                    "strategy": "source_title",
                    "primary": fr_title or en_title,
                    "secondary": en_title if fr_title != en_title else ""
                },
                "public_forms": {
                    "restored_reference": "",
                    "french_reference": fr_title or en_title,
                    "other_forms": [],
                    "english_labels": [en_title] if fr_title and fr_title != en_title else [],
                    "aliases_public": []
                },
                "aliases": [en_title] if fr_title and fr_title != en_title else [],
                "category": category,
                "alpha_letter": letter,
                "status": "ready",
                "entries": [{
                    "entry_id": smith_id,
                    "dictionary": "smith",
                    "display_role": "detailed_reference",
                    "is_primary_for_role": True
                }],
                "related_concepts": []
            }
            new_concepts.append(new_concept)
            concept_by_id[cid] = new_concept

        strategies_count[strategy] = strategies_count.get(strategy, 0) + 1

        # Create link
        new_links.append({
            "entry_id": smith_id,
            "concept_id": concept_id,
            "link_type": "primary",
            "confidence": confidence,
            "match_strategy": strategy,
            "notes": ""
        })

    print(f"\nResults:")
    print(f"  Matched to existing concepts: {matched}")
    print(f"  New concepts created: {created}")
    print(f"  Total new links: {len(new_links)}")
    print(f"\nStrategies:")
    for s, count in sorted(strategies_count.items(), key=lambda x: -x[1]):
        print(f"  {s}: {count}")

    # Merge new concepts into concepts list
    all_concepts = concepts + new_concepts

    # Merge new links into links list
    all_links = links + new_links

    print(f"\nFinal totals:")
    print(f"  Concepts: {len(all_concepts)} (was {len(concepts)})")
    print(f"  Links: {len(all_links)} (was {len(links)})")

    # Count cross-source concepts
    cross_source = 0
    for c in all_concepts:
        dicts = set(e['dictionary'] for e in c.get('entries', []))
        if len(dicts) > 1:
            cross_source += 1
    print(f"  Cross-source concepts: {cross_source}")

    # Save
    print("\nSaving...")
    save_json(BASE / "concepts.json", all_concepts)
    save_json(BASE / "concept-entry-links.json", all_links)
    print("Done!")

    # Return stats for manifest update
    return {
        "concepts_count": len(all_concepts),
        "cross_source": cross_source,
        "smith_attached": matched,
        "smith_new": created,
        "total_links": len(all_links)
    }

if __name__ == "__main__":
    stats = main()
    # Save stats for later use
    save_json(BASE.parent.parent / "work" / "reports" / "smith_linking_stats.json", stats)

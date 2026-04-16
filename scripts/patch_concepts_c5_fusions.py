#!/usr/bin/env python3
"""
Fusions C5 : merge de concepts doublons après correction des labels.

Fusions à effectuer :
  ancients   → anciens    (source ISBE doublon)
  archangel  → archanges  (sources Easton + ISBE doublon du BYM)
  fete       → feasts     (source Easton merge dans concept Smith+ISBE + patch label Fêtes)

Pour chaque fusion (SOURCE → CIBLE) :
1. Dans concepts.json :
   - Déplacer les entries[] de SOURCE dans CIBLE (dédup)
   - Ajouter le label de SOURCE aux aliases de CIBLE
   - Ajouter les english_labels de SOURCE à CIBLE
   - Supprimer le concept SOURCE
   - Optionnellement : post_fusion_patch pour remplacer label/display/aliases de la CIBLE
2. Dans concept-meta.json : supprimer l'entrée SOURCE + patcher CIBLE si post_fusion_patch
3. Dans concept-entry-links.json : réécrire concept_id de SOURCE → CIBLE
4. Dans slug-map.json : ajouter SOURCE comme slug pointant vers CIBLE
   (pour préserver l'URL /dictionnaire-biblique/ancients/ qui continue
    de fonctionner via fallback "slug → concept_id")
5. concept-url-slugs.json : PAS TOUCHÉ (la CIBLE garde son propre slug u)

Modes : dry-run (défaut) ou --apply.
"""
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
DICT_DIR = ROOT / "uploads" / "dictionnaires"
AUDIT_DIR = ROOT / "work" / "audit"
BACKUP_DIR = ROOT / "work" / "backups"

CONCEPTS_JSON = DICT_DIR / "concepts.json"
CONCEPT_META_JSON = DICT_DIR / "concept-meta.json"
CONCEPT_LINKS_JSON = DICT_DIR / "concept-entry-links.json"
SLUG_MAP_JSON = DICT_DIR / "slug-map.json"
URL_SLUGS_JSON = DICT_DIR / "concept-url-slugs.json"
LOG_JSON = AUDIT_DIR / "isbe-c5-fusion-log.json"

# ─── FUSIONS VALIDÉES ───
FUSIONS = [
    {
        'source': 'ancients',
        'target': 'anciens',
        'rationale': 'Concept ancients (ISBE deep_read) sémantiquement identique à anciens (BYM peuple)',
        'add_slug_redirect': True,  # URL /dictionnaire-biblique/ancients/ → anciens
    },
    {
        'source': 'archangel',
        'target': 'archanges',
        'rationale': 'Concept archangel (Easton+ISBE) = archanges (BYM) au singulier vs pluriel',
        'add_slug_redirect': True,
    },
    {
        'source': 'fete',
        'target': 'feasts',
        'rationale': 'Concept fete (Easton singulier) fusionné dans concept feasts (Smith+ISBE), puis patch label → Fêtes',
        'add_slug_redirect': True,  # URL /dictionnaire-biblique/fete/ → feasts
        'post_fusion_patch': {
            'label': 'Fêtes',
            'primary': 'Fêtes',
            'secondary': 'Feasts',
            'english_labels_add': ['Feasts'],
        },
    },
]


def check_backup():
    if not BACKUP_DIR.exists():
        return False
    backups = sorted(BACKUP_DIR.glob("dictionnaires-*.zip"))
    if not backups:
        return False
    print(f"✓ Backup : {backups[-1].name}")
    return True


def dedup_entries(target_entries, source_entries):
    """Merge source_entries into target_entries, dedup par (entry_id, dictionary)."""
    seen = {(e['entry_id'], e.get('dictionary', '')) for e in target_entries}
    merged = list(target_entries)
    added = []
    for e in source_entries:
        key = (e['entry_id'], e.get('dictionary', ''))
        if key not in seen:
            merged.append(e)
            seen.add(key)
            added.append(e['entry_id'])
    return merged, added


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Apply changes (default: dry-run)')
    args = parser.parse_args()

    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'Mode : {mode}')
    print()

    if args.apply and not check_backup():
        print("ERREUR : backup manquant")
        sys.exit(1)

    # Load all 4 files
    print("Chargement des fichiers...")
    with open(CONCEPTS_JSON, 'r', encoding='utf-8-sig') as f:
        concepts = json.load(f)
    concept_by_id = {c['concept_id']: c for c in concepts}

    with open(CONCEPT_META_JSON, 'r', encoding='utf-8-sig') as f:
        meta = json.load(f)

    with open(CONCEPT_LINKS_JSON, 'r', encoding='utf-8-sig') as f:
        links = json.load(f)

    with open(SLUG_MAP_JSON, 'r', encoding='utf-8-sig') as f:
        slug_map = json.load(f)

    print(f"  concepts          : {len(concepts)}")
    print(f"  meta              : {len(meta)}")
    print(f"  concept-entry-links : {len(links)}")
    print(f"  slug-map          : {len(slug_map)}")
    print()

    # ─── Apply each fusion ───
    fusion_reports = []
    for fusion in FUSIONS:
        src_id = fusion['source']
        tgt_id = fusion['target']
        src = concept_by_id.get(src_id)
        tgt = concept_by_id.get(tgt_id)

        if not src:
            print(f"  ⚠ Fusion {src_id}→{tgt_id} : source INTROUVABLE")
            continue
        if not tgt:
            print(f"  ⚠ Fusion {src_id}→{tgt_id} : cible INTROUVABLE")
            continue

        print(f"  ✓ Fusion {src_id} → {tgt_id}")
        src_label = src.get('label', '')
        src_english_labels = list(src.get('public_forms', {}).get('english_labels', []) or [])
        src_aliases = list(src.get('aliases', []) or [])
        src_secondary = src.get('display_titles', {}).get('secondary', '')
        src_entries = list(src.get('entries', []) or [])
        src_related = list(src.get('related_concepts', []) or [])

        # Build merged target (dry or apply)
        merged_entries, added_entry_ids = dedup_entries(tgt.get('entries', []), src_entries)

        # Merge aliases / english_labels
        tgt_aliases = list(tgt.get('aliases', []) or [])
        for candidate in src_aliases + [src_label] + ([src_secondary] if src_secondary else []):
            if candidate and candidate not in tgt_aliases:
                tgt_aliases.append(candidate)

        tgt_pf = tgt.get('public_forms', {}) or {}
        tgt_english = list(tgt_pf.get('english_labels', []) or [])
        for en in src_english_labels + ([src_secondary] if src_secondary else []):
            if en and en not in tgt_english:
                tgt_english.append(en)

        # Merge related_concepts (dedup by concept_id)
        tgt_related = list(tgt.get('related_concepts', []) or [])
        tgt_related_ids = {r.get('concept_id') for r in tgt_related}
        added_related = []
        for r in src_related:
            rid = r.get('concept_id')
            if rid and rid not in tgt_related_ids and rid != tgt_id:
                tgt_related.append(r)
                tgt_related_ids.add(rid)
                added_related.append(rid)

        # Optional post-fusion patch on target (label/primary/secondary/etc.)
        post_patch = fusion.get('post_fusion_patch')
        post_patch_applied = None
        if post_patch:
            new_label = post_patch.get('label')
            new_primary = post_patch.get('primary', new_label)
            new_secondary = post_patch.get('secondary', '')
            extra_en = post_patch.get('english_labels_add', [])

            post_patch_applied = {
                'old_label': tgt.get('label', ''),
                'new_label': new_label,
                'new_primary': new_primary,
                'new_secondary': new_secondary,
                'extra_en_labels': extra_en,
            }

            # Add post-patch labels to aliases + english_labels for merge continuity
            for cand in [new_label, new_secondary] + extra_en:
                if cand and cand not in tgt_aliases:
                    tgt_aliases.append(cand)
            for en in extra_en + ([new_secondary] if new_secondary else []):
                if en and en not in tgt_english:
                    tgt_english.append(en)

        fusion_reports.append({
            'source': src_id,
            'target': tgt_id,
            'rationale': fusion['rationale'],
            'source_label': src_label,
            'target_label_before': tgt.get('label', ''),
            'entries_moved': added_entry_ids,
            'entries_total_after': len(merged_entries),
            'aliases_after': tgt_aliases,
            'english_labels_after': tgt_english,
            'related_added': added_related,
            'post_fusion_patch': post_patch_applied,
        })

        if args.apply:
            # Update target concept in-place
            tgt['entries'] = merged_entries
            tgt['aliases'] = tgt_aliases
            tgt_pf['english_labels'] = tgt_english
            tgt['public_forms'] = tgt_pf
            tgt['related_concepts'] = tgt_related

            if post_patch:
                # Apply label / display_titles patch on target
                tgt['label'] = post_patch.get('label', tgt['label'])
                dt = tgt.get('display_titles', {}) or {}
                dt['primary'] = post_patch.get('primary', dt.get('primary', ''))
                new_sec = post_patch.get('secondary', '')
                if new_sec:
                    dt['secondary'] = new_sec
                    dt['strategy'] = 'french_first'
                tgt['display_titles'] = dt
                # public_forms.french_reference
                tgt_pf['french_reference'] = post_patch.get('label', tgt_pf.get('french_reference', ''))
                tgt['public_forms'] = tgt_pf
                # Mirror in concept-meta.json
                if tgt_id in meta:
                    meta[tgt_id]['l'] = post_patch.get('label', meta[tgt_id].get('l', ''))
                    meta[tgt_id]['p'] = post_patch.get('primary', meta[tgt_id].get('p', ''))
                    meta[tgt_id]['s'] = post_patch.get('secondary', meta[tgt_id].get('s', ''))

    if args.apply:
        # ─── Remove source concepts from concepts.json ───
        to_remove = {f['source'] for f in FUSIONS if concept_by_id.get(f['source'])}
        before_count = len(concepts)
        concepts = [c for c in concepts if c['concept_id'] not in to_remove]
        after_count = len(concepts)
        print(f"  → concepts.json : {before_count} → {after_count} (-{before_count - after_count})")

        # ─── Remove source concepts from concept-meta.json ───
        meta_before = len(meta)
        for src_id in to_remove:
            if src_id in meta:
                del meta[src_id]
        print(f"  → concept-meta.json : {meta_before} → {len(meta)} (-{meta_before - len(meta)})")

        # ─── Update concept-entry-links.json ───
        link_remap = {f['source']: f['target'] for f in FUSIONS}
        changed_links = 0
        for link in links:
            if link.get('concept_id') in link_remap:
                link['concept_id'] = link_remap[link['concept_id']]
                changed_links += 1
        print(f"  → concept-entry-links.json : {changed_links} liens remappés")

        # ─── Update slug-map.json : add redirect from old slug to new concept_id ───
        added_slugs = 0
        for fusion in FUSIONS:
            if fusion.get('add_slug_redirect'):
                src_slug = fusion['source']
                tgt_id = fusion['target']
                if src_slug not in slug_map:
                    slug_map[src_slug] = tgt_id
                    added_slugs += 1
        print(f"  → slug-map.json : {added_slugs} redirects ajoutés")

        # ─── Write all 4 files SANS BOM (PHP json_decode strict) ───
        # concept-entry-links.json garde son BOM historique (consommé par JS uniquement)
        print("  Écriture concepts.json...")
        with open(CONCEPTS_JSON, 'w', encoding='utf-8') as f:
            json.dump(concepts, f, ensure_ascii=False, indent=2)

        print("  Écriture concept-meta.json...")
        with open(CONCEPT_META_JSON, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))

        print("  Écriture concept-entry-links.json...")
        with open(CONCEPT_LINKS_JSON, 'w', encoding='utf-8-sig') as f:
            json.dump(links, f, ensure_ascii=False, indent=2)

        print("  Écriture slug-map.json...")
        with open(SLUG_MAP_JSON, 'w', encoding='utf-8') as f:
            json.dump(slug_map, f, ensure_ascii=False, indent=2)

        # Save log
        log = {
            'applied_at': datetime.now().isoformat(),
            'fusions': fusion_reports,
            'concepts_before': before_count,
            'concepts_after': after_count,
            'meta_removed': meta_before - len(meta),
            'links_remapped': changed_links,
            'slug_redirects_added': added_slugs,
        }
        with open(LOG_JSON, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
        print(f"\nLog : {LOG_JSON}")
    else:
        # Dry-run report
        print("=== DRY-RUN ===")
        for fr in fusion_reports:
            print()
            print(f"Fusion {fr['source']} → {fr['target']}")
            print(f"  Rationale : {fr['rationale']}")
            print(f"  Source label    : {fr['source_label']!r}")
            print(f"  Target label    : {fr['target_label_before']!r}")
            print(f"  Entries moved   : {fr['entries_moved']}")
            print(f"  Entries total   : {fr['entries_total_after']}")
            print(f"  Aliases after   : {fr['aliases_after']}")
            print(f"  English labels  : {fr['english_labels_after']}")
            if fr.get('post_fusion_patch'):
                pp = fr['post_fusion_patch']
                print(f"  POST-FUSION PATCH :")
                print(f"    label    : {pp['old_label']!r} → {pp['new_label']!r}")
                print(f"    primary  : {pp['new_primary']!r}")
                print(f"    secondary: {pp['new_secondary']!r}")

    print()
    print(f"Fusions {'appliquées' if args.apply else 'simulées'} : {len(fusion_reports)}")


if __name__ == '__main__':
    main()

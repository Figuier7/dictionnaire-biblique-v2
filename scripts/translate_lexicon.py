#!/usr/bin/env python3
"""
Translate hebrew-lexicon-en.json → hebrew-lexicon-fr.json
using OpenAI GPT-4o-mini API.

Batch translation: groups entries into chunks to minimize API calls.
Translates: definition_short, definition_full, usage, source, defs_strong,
            bdb_defs, li_def, and all sense defs/text recursively.

Usage:
    export OPENAI_API_KEY="sk-..."
    python3 translate_lexicon.py [--resume] [--batch-size 25] [--max-entries 0]

    --resume      Resume from last checkpoint
    --batch-size  Entries per API call (default: 25)
    --max-entries Limit total entries (0 = all, for testing use e.g. 50)
"""

import argparse
import json
import os
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

def _import_openai():
    """Import openai, installing if needed."""
    try:
        from openai import OpenAI
        return OpenAI
    except ImportError:
        print("Installing openai package...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "openai", "--break-system-packages", "-q"])
        from openai import OpenAI
        return OpenAI

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "hebrew-lexicon-en.json"
OUTPUT_FILE = BASE_DIR / "hebrew-lexicon-fr.json"
CHECKPOINT_FILE = BASE_DIR / "scripts" / ".translate_checkpoint.json"

# ─── Translation prompt ───
SYSTEM_PROMPT = """Tu es un traducteur spécialisé en lexicographie biblique hébraïque.
Tu traduis de l'anglais vers le français des définitions issues du dictionnaire Brown-Driver-Briggs (BDB) et du lexique Strong.

Règles strictes :
1. Traduis UNIQUEMENT les textes anglais. Ne touche JAMAIS aux mots hébreux, grecs, araméens, ou translittérations.
2. Conserve les abréviations bibliographiques telles quelles (Qal, Pi, Hiph, Inf, Pf, Impf, Pt, etc.).
3. Conserve les références bibliques telles quelles (Gn 24:5, Ex 10:27, etc.).
4. Traduis les noms de livres bibliques si présents en toutes lettres : Genesis → Genèse, Exodus → Exode, etc.
5. Conserve le registre académique/lexicographique.
6. Pour les noms propres hébreux, garde le nom hébreu et traduis la description.
7. Sois concis : ne rajoute pas de texte superflu.

Tu reçois un JSON avec des champs à traduire. Renvoie EXACTEMENT la même structure JSON avec les valeurs traduites."""

USER_PROMPT_TEMPLATE = """Traduis les champs textuels de ces entrées lexicographiques de l'anglais vers le français.
Chaque entrée a un "id" (à conserver tel quel) et des champs textuels à traduire.

{entries_json}

Renvoie un JSON array avec la même structure, mêmes "id", avec les valeurs traduites en français."""


def extract_translatable(entry):
    """Extract translatable text fields from an entry."""
    fields = {
        "id": entry["strong"],
        "definition_short": entry.get("definition_short", ""),
        "usage": entry.get("usage", ""),
        "source": entry.get("source", ""),
        "li_def": entry.get("li_def", ""),
    }

    # defs_strong
    defs_s = entry.get("defs_strong", [])
    if defs_s:
        fields["defs_strong"] = defs_s

    # bdb_defs
    bdb_defs = entry.get("bdb_defs", [])
    if bdb_defs:
        fields["bdb_defs"] = bdb_defs

    # Flatten BDB senses into a simpler structure for translation
    senses = entry.get("bdb_senses", [])
    if senses:
        fields["senses"] = _flatten_senses(senses)

    # definition_full — only the first 500 chars to keep cost/token usage reasonable
    full = entry.get("definition_full", "")
    if full:
        fields["definition_full"] = full[:500]

    return fields


def _flatten_senses(senses, prefix=""):
    """Flatten nested senses to a list of {path, def, text} for translation."""
    result = []
    for i, s in enumerate(senses):
        path = f"{prefix}{s.get('n', i+1)}"
        stem = s.get("stem", "")
        if stem:
            path = f"{stem}.{path}" if s.get("n") else stem

        item = {"path": path}
        d = s.get("def", "")
        if d:
            item["def"] = d
        defs = s.get("defs", [])
        if defs:
            item["defs"] = defs

        result.append(item)

        # Recurse into sub-senses
        sub = s.get("senses", [])
        if sub:
            result.extend(_flatten_senses(sub, prefix=f"{path}."))

    return result


def apply_translations(entry, translated):
    """Apply translated fields back to the entry."""
    entry_out = dict(entry)  # shallow copy

    if "definition_short" in translated:
        entry_out["definition_short_fr"] = translated["definition_short"]
    if "usage" in translated:
        entry_out["usage_fr"] = translated["usage"]
    if "source" in translated:
        entry_out["source_fr"] = translated["source"]
    if "li_def" in translated:
        entry_out["li_def_fr"] = translated["li_def"]
    if "defs_strong" in translated:
        entry_out["defs_strong_fr"] = translated["defs_strong"]
    if "bdb_defs" in translated:
        entry_out["bdb_defs_fr"] = translated["bdb_defs"]
    if "definition_full" in translated:
        entry_out["definition_full_fr"] = translated["definition_full"]

    # Apply sense translations back into bdb_senses
    if "senses" in translated and entry_out.get("bdb_senses"):
        sense_map = {}
        for st in translated["senses"]:
            path = st.get("path", "")
            sense_map[path] = st
        _apply_sense_translations(entry_out["bdb_senses"], sense_map, "")

    return entry_out


def _apply_sense_translations(senses, sense_map, prefix):
    """Recursively apply translations to the sense tree."""
    for i, s in enumerate(senses):
        path = f"{prefix}{s.get('n', i+1)}"
        stem = s.get("stem", "")
        if stem:
            path = f"{stem}.{path}" if s.get("n") else stem

        tr = sense_map.get(path, {})
        if "def" in tr:
            s["def_fr"] = tr["def"]
        if "defs" in tr:
            s["defs_fr"] = tr["defs"]

        sub = s.get("senses", [])
        if sub:
            _apply_sense_translations(sub, sense_map, f"{path}.")


def translate_batch(client, entries_to_translate, model="gpt-4o-mini"):
    """Send a batch of entries to GPT-4o-mini for translation."""
    entries_json = json.dumps(entries_to_translate, ensure_ascii=False, indent=None)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(entries_json=entries_json)},
        ],
        temperature=0.2,
        max_tokens=16000,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    # Parse response — might be wrapped in {"entries": [...]} or just [...]
    parsed = json.loads(content)
    if isinstance(parsed, dict):
        # Try common wrapper keys
        for key in ("entries", "results", "data", "translations"):
            if key in parsed:
                parsed = parsed[key]
                break
        else:
            # Single entry dict? Wrap in list
            if "id" in parsed:
                parsed = [parsed]
            else:
                # Take first array value
                for v in parsed.values():
                    if isinstance(v, list):
                        parsed = v
                        break

    if not isinstance(parsed, list):
        raise ValueError(f"Unexpected response format: {type(parsed)}")

    # Build lookup by id
    result = {}
    for item in parsed:
        eid = item.get("id", "")
        if eid:
            result[eid] = item

    usage = response.usage
    return result, usage.prompt_tokens, usage.completion_tokens


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--max-entries", type=int, default=0, help="0 = all")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--api-key", default=None, help="OpenAI API key (or use OPENAI_API_KEY env var)")
    parser.add_argument("--workers", type=int, default=10, help="Concurrent API requests (default: 10)")
    parser.add_argument("--dry-run", action="store_true", help="Parse & prepare but don't call API")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key and not args.dry_run:
        print("ERROR: Set OPENAI_API_KEY environment variable")
        sys.exit(1)

    # Load input
    print(f"Loading {INPUT_FILE}...")
    with open(INPUT_FILE, encoding="utf-8") as f:
        lexicon = json.load(f)
    print(f"  -> {len(lexicon)} entries loaded")

    # Limit entries if requested
    if args.max_entries > 0:
        lexicon = lexicon[:args.max_entries]
        print(f"  -> Limited to {len(lexicon)} entries")

    # Load checkpoint if resuming
    translated_ids = set()
    results_map = {}
    if args.resume and CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, encoding="utf-8") as f:
            checkpoint = json.load(f)
        results_map = {r["strong"]: r for r in checkpoint.get("results", [])}
        translated_ids = set(results_map.keys())
        print(f"  -> Resuming: {len(translated_ids)} already translated")

    # Filter entries that need translation
    to_translate = [e for e in lexicon if e["strong"] not in translated_ids]
    print(f"  -> {len(to_translate)} entries to translate")

    if args.dry_run:
        # Show what would be sent
        sample = extract_translatable(to_translate[0]) if to_translate else {}
        print("\n=== DRY RUN — Sample payload ===")
        print(json.dumps(sample, ensure_ascii=False, indent=2)[:2000])

        # Estimate tokens (rough: 1 token ≈ 4 chars)
        total_chars = 0
        for e in to_translate:
            payload = extract_translatable(e)
            total_chars += len(json.dumps(payload, ensure_ascii=False))
        est_tokens = total_chars / 4
        n_batches = (len(to_translate) + args.batch_size - 1) // args.batch_size
        print(f"\nEstimated input tokens: ~{est_tokens:,.0f}")
        print(f"Batches: {n_batches}")
        print(f"Estimated cost (GPT-4o-mini @ $0.15/1M in + $0.60/1M out):")
        est_out_tokens = est_tokens * 1.1  # translations usually slightly longer
        cost = (est_tokens / 1_000_000 * 0.15) + (est_out_tokens / 1_000_000 * 0.60)
        print(f"  ~${cost:.2f} USD")
        return

    # Translate in batches (parallel)
    OpenAI = _import_openai()
    client = OpenAI(api_key=api_key, timeout=60.0)
    total_prompt = 0
    total_completion = 0
    errors = 0
    lock = threading.Lock()
    completed_batches = 0

    batches = []
    for i in range(0, len(to_translate), args.batch_size):
        batches.append((i // args.batch_size, to_translate[i:i + args.batch_size]))

    n_workers = min(args.workers, len(batches))
    print(f"\nTranslating {len(batches)} batches of ~{args.batch_size} entries with {n_workers} workers...")

    def process_batch(batch_idx, batch):
        nonlocal total_prompt, total_completion, errors, completed_batches
        payloads = [extract_translatable(e) for e in batch]
        try:
            translated, p_tok, c_tok = translate_batch(client, payloads, model=args.model)
            with lock:
                total_prompt += p_tok
                total_completion += c_tok
                for e in batch:
                    sid = e["strong"]
                    if sid in translated:
                        results_map[sid] = apply_translations(e, translated[sid])
                    else:
                        # Don't add to results_map — will be retried on --resume
                        errors += 1
                completed_batches += 1
                done = len(results_map)
                pct = 100 * done / len(lexicon)
                cost = (total_prompt / 1_000_000 * 0.15) + (total_completion / 1_000_000 * 0.60)
                print(f"  Batch {completed_batches}/{len(batches)} -- {done}/{len(lexicon)} ({pct:.1f}%) -- tokens: {total_prompt+total_completion:,} -- ${cost:.3f}")
                if completed_batches % 20 == 0:
                    _save_checkpoint(results_map, lexicon)
            return True
        except Exception as ex:
            with lock:
                errors += 1
                completed_batches += 1
                # Don't add failed entries to results_map — will be retried on --resume
                print(f"  ERROR batch {batch_idx+1}: {ex}")
                _save_checkpoint(results_map, lexicon)
            return False

    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = {executor.submit(process_batch, idx, batch): idx for idx, batch in batches}
        for future in as_completed(futures):
            future.result()

    # Final save
    _save_checkpoint(results_map, lexicon)

    # Build final output in original order
    final = []
    for e in lexicon:
        sid = e["strong"]
        if sid in results_map:
            final.append(results_map[sid])
        else:
            final.append(e)

    print(f"\nWriting {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    cost = (total_prompt / 1_000_000 * 0.15) + (total_completion / 1_000_000 * 0.60)
    print(f"\n=== Translation Complete ===")
    print(f"Entries translated: {len(results_map)}")
    print(f"Errors: {errors}")
    print(f"Total tokens: {total_prompt + total_completion:,} (prompt: {total_prompt:,}, completion: {total_completion:,})")
    print(f"Total cost: ~${cost:.3f}")
    print(f"Output size: {size_mb:.1f} MB")


def _save_checkpoint(results_map, lexicon):
    """Save translation checkpoint."""
    checkpoint = {
        "translated": len(results_map),
        "total": len(lexicon),
        "results": list(results_map.values()),
    }
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False)
    print(f"    [checkpoint saved: {len(results_map)} entries]")


if __name__ == "__main__":
    main()

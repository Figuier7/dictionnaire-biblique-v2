#!/usr/bin/env python3
"""Translate remaining entries with small batches and robust error handling."""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from translate_lexicon import (
    extract_translatable, translate_batch, apply_translations,
    CHECKPOINT_FILE, _save_checkpoint, INPUT_FILE, OUTPUT_FILE
)
from openai import OpenAI

BATCH_SIZE = 10  # Smaller batches for reliability

def main():
    # Load checkpoint
    cp = json.load(open(CHECKPOINT_FILE, "r", encoding="utf-8"))
    results_map = {r["strong"]: r for r in cp["results"]}

    # Load lexicon
    lexicon = json.load(open(INPUT_FILE, "r", encoding="utf-8"))
    remaining = [e for e in lexicon if e["strong"] not in results_map]

    print(f"Checkpoint: {len(results_map)} done, {len(remaining)} remaining")
    if not remaining:
        print("Nothing to translate!")
        return

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=90.0)
    errors = 0
    total_p = total_c = 0

    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(remaining), BATCH_SIZE):
        batch = remaining[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        ids = [e["strong"] for e in batch]

        for attempt in range(3):  # 3 retries per batch
            try:
                payloads = [extract_translatable(e) for e in batch]
                translated, p_tok, c_tok = translate_batch(client, payloads)
                total_p += p_tok
                total_c += c_tok

                for e in batch:
                    sid = e["strong"]
                    if sid in translated:
                        results_map[sid] = apply_translations(e, translated[sid])

                done = len(results_map)
                pct = 100 * done / len(lexicon)
                print(f"  {batch_num}/{total_batches} -- {done}/{len(lexicon)} ({pct:.1f}%) -- {ids[0]}-{ids[-1]}")

                # Save checkpoint after EVERY batch
                _save_checkpoint(results_map, lexicon)
                time.sleep(0.3)
                break  # Success, move to next batch

            except Exception as ex:
                print(f"  RETRY {attempt+1}/3 batch {batch_num} ({ids[0]}-{ids[-1]}): {ex}")
                if attempt < 2:
                    time.sleep(5 * (attempt + 1))
                else:
                    errors += 1
                    print(f"  FAILED batch {batch_num}")

    # Write output
    final = [results_map.get(e["strong"], e) for e in lexicon]
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    with_fr = sum(1 for e in final if any(k.endswith("_fr") for k in e.keys()))
    size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"\nDone! {with_fr}/{len(final)} with _fr, {errors} failed batches")
    print(f"Tokens: {total_p+total_c:,} -- Cost: ${(total_p/1e6*0.15)+(total_c/1e6*0.60):.3f}")
    print(f"Output: {size_mb:.1f} MB")

if __name__ == "__main__":
    main()

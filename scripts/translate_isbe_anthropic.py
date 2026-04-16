#!/usr/bin/env python3
"""
translate_isbe_anthropic.py
============================
Translate ISBE chunks using the Anthropic API (Claude Opus 4.6).

Modes:
  --mode batch     Create an Anthropic Message Batch (50% cheaper, async)
  --mode direct    Translate chunks one by one with streaming (for testing or small runs)
  --mode status    Check batch status
  --mode collect   Collect batch results

Usage:
    # Full batch (recommended for production)
    python scripts/translate_isbe_anthropic.py --mode batch

    # Translate a few chunks directly (testing)
    python scripts/translate_isbe_anthropic.py --mode direct --start 1 --end 5

    # Check batch status
    python scripts/translate_isbe_anthropic.py --mode status --batch-id msgbatch_xxx

    # Collect results
    python scripts/translate_isbe_anthropic.py --mode collect --batch-id msgbatch_xxx
"""

import argparse
import json
import sys
import time
from pathlib import Path

import anthropic

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = ROOT / "work" / "codex_local_isbe"
SOURCE_DIR = WORK_DIR / "source_chunks"
TRANSLATED_DIR = WORK_DIR / "translated_chunks"
MANIFEST_PATH = WORK_DIR / "manifests" / "chunk_manifest.json"
BATCH_DIR = WORK_DIR / "batch"
REPORTS_DIR = BATCH_DIR / "reports"

MODEL = "claude-opus-4-6"
MAX_TOKENS = 64_000  # generous for long translations

# ---------------------------------------------------------------------------
# System instructions (same as in prepare_isbe_translation.py)
# ---------------------------------------------------------------------------

SYSTEM_INSTRUCTIONS = """\
Tu traduis des chunks de l'encyclopedie biblique ISBE (International Standard Bible Encyclopedia) \
vers le francais pour un pipeline JSON strict.
Retourner uniquement un objet JSON exact sous la forme {"chunk_id":"...","entries":[...]}.
Contraintes absolues:
- chunk_id identique a la source.
- entries doit garder exactement le meme nombre d'elements, le meme ordre et les memes ids.
- Chaque element doit etre strictement {"id":0,"mot":"...","definition":"...","proper_nouns_unknown":[]}.
- mot est un invariant absolu: ne jamais le modifier.
- Traduire integralement definition, sans troncage, sans resume, sans ajout.
- L'ISBE est une encyclopedie savante: conserver le ton encyclopedique, les sections numerotees, \
les signatures d'auteurs, les prononciations (ar'-un, a-bad'-on, etc.).
- Conserver toutes les translitterations hebraiques et grecques entre parentheses.
- Renvois internes: traduire le mot introducteur (See -> Voir, compare -> comparer) \
mais JAMAIS la cible du renvoi (ALEPH, APOLLYON, PRIEST, III, etc.) qui doit rester en forme source.
- Conserver inchanges comme sigles savants: Heb., Gr., LXX, cf., comp., ibid., q.v.
- Franciser: i.e. -> c.-a-d.; e.g. -> par ex.; viz. -> a savoir; No. -> no.
- References bibliques en formes courtes francaises stables: Gen., Ex., Lev., Nomb., Deut., Jos., \
Jug., 1 Sam., 2 Sam., 1 Rois, 2 Rois, 1 Chr., 2 Chr., Esdr., Neh., Esth., Job, Ps., Prov., \
Eccl., Cant., Esa., Jer., Lam., Ez., Dan., Matt., Marc, Luc, Jean, Actes, Rom., 1 Cor., 2 Cor., \
Gal., Eph., Phil., Col., 1 Thess., 2 Thess., 1 Tim., 2 Tim., Tite, Philem., Heb., Jacq., \
1 Pi., 2 Pi., 1 Jean, 2 Jean, 3 Jean, Jude, Apoc.
- Authorized Version -> Version autorisee; Revised Version -> Version revisee; \
in our version -> dans notre version; margin/in the margin -> marge/en marge.
- American Standard Revised Version / A.S.V. -> Version Standard Americaine Revisee.
- Si un mot ou groupe de mots anglais est conserve parce qu'il est l'objet meme d'une remarque \
editoriale ou textuelle, conserver uniquement cette forme anglaise citee, avec sa casse source, \
entre guillemets si elle est citee dans la source, et traduire entierement la phrase autour.
- God -> Elohim; LORD/Jehovah/Yahweh/the LORD -> YHWH; the Lord -> le Seigneur; \
Jesus -> Yehoshoua (Jesus) si necessaire; Christ/Messiah -> Mashiah (Christ) ou Mashiah; \
Holy Spirit/Holy Ghost -> Saint-Esprit.
- B.C. -> av. J.-C.; A.D. -> apr. J.-C.
- Ne laisser aucun anglais residuel non cite, sauf sigles savants ou citation anglaise \
explicitement objet de la remarque.
- Si un nom propre n'est pas clairement arbitre en francais, conserver provisoirement la forme \
source et l'ajouter dans proper_nouns_unknown.
- proper_nouns_unknown doit lister uniquement les noms propres conserves en forme source par \
prudence; sinon liste vide.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_manifest() -> list[dict]:
    with open(MANIFEST_PATH, encoding="utf-8-sig") as f:
        return json.load(f)


def load_source_chunk(chunk_id: str) -> list[dict]:
    path = SOURCE_DIR / f"{chunk_id}.source.json"
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def build_user_payload(chunk: dict, entries: list[dict]) -> str:
    payload = {
        "task": "Traduire ce chunk ISBE en francais selon les regles du pipeline.",
        "chunk_id": chunk["chunk_id"],
        "chunk_mode": chunk["chunk_mode"],
        "entry_count": chunk["entry_count"],
        "output_contract": {
            "chunk_id": chunk["chunk_id"],
            "entries": [
                {"id": "int", "mot": "string (invariant)",
                 "definition": "string (traduit)", "proper_nouns_unknown": ["string"]}
            ]
        },
        "entries": entries,
    }
    return json.dumps(payload, ensure_ascii=False)


def save_translated_chunk(chunk_id: str, entries: list[dict]) -> None:
    TRANSLATED_DIR.mkdir(parents=True, exist_ok=True)
    path = TRANSLATED_DIR / f"{chunk_id}.json"
    with open(path, "w", encoding="utf-8-sig") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def already_translated(chunk_id: str) -> bool:
    return (TRANSLATED_DIR / f"{chunk_id}.json").exists()


# ---------------------------------------------------------------------------
# Mode: direct (one-by-one with streaming)
# ---------------------------------------------------------------------------

def translate_direct(client: anthropic.Anthropic, manifest: list[dict],
                     start: int, end: int, force: bool = False) -> None:
    chunks = manifest[start - 1:end]
    total = len(chunks)
    print(f"Translating chunks {start}-{end} ({total} chunks) in direct mode...")

    for i, chunk in enumerate(chunks, 1):
        chunk_id = chunk["chunk_id"]

        if not force and already_translated(chunk_id):
            print(f"  [{i}/{total}] {chunk_id} -- already translated, skipping")
            continue

        entries = load_source_chunk(chunk_id)
        user_content = build_user_payload(chunk, entries)
        source_chars = sum(len(e.get("definition", "")) for e in entries)

        print(f"  [{i}/{total}] {chunk_id} ({chunk['entry_count']} entries, "
              f"{source_chars:,} chars) ...", end=" ", flush=True)

        try:
            # Use streaming to avoid timeouts on large chunks
            collected_text = []
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                thinking={"type": "adaptive"},
                system=SYSTEM_INSTRUCTIONS,
                messages=[{"role": "user", "content": user_content}],
            ) as stream:
                for text in stream.text_stream:
                    collected_text.append(text)

            response_text = "".join(collected_text)

            # Parse JSON response
            result = json.loads(response_text)
            translated_entries = result.get("entries", [])

            if len(translated_entries) != chunk["entry_count"]:
                print(f"WARNING: expected {chunk['entry_count']} entries, "
                      f"got {len(translated_entries)}")

            save_translated_chunk(chunk_id, translated_entries)
            print(f"OK ({len(response_text):,} chars)")

        except json.JSONDecodeError as e:
            print(f"JSON ERROR: {e}")
            # Save raw response for debugging
            error_dir = BATCH_DIR / "raw_errors" / "direct"
            error_dir.mkdir(parents=True, exist_ok=True)
            (error_dir / f"{chunk_id}.raw.txt").write_text(
                response_text, encoding="utf-8")
            print(f"    Raw response saved to {error_dir / chunk_id}.raw.txt")

        except anthropic.RateLimitError as e:
            retry_after = int(e.response.headers.get("retry-after", "60"))
            print(f"RATE LIMITED, waiting {retry_after}s...")
            time.sleep(retry_after)
            # Re-queue this chunk by decrementing i (handled by retry below)

        except anthropic.APIError as e:
            print(f"API ERROR: {e}")


# ---------------------------------------------------------------------------
# Mode: batch (Anthropic Message Batches API - 50% cheaper)
# ---------------------------------------------------------------------------

def create_batch(client: anthropic.Anthropic, manifest: list[dict],
                 start: int, end: int, force: bool = False) -> None:
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    chunks = manifest[start - 1:end]
    print(f"Preparing batch for chunks {start}-{end} ({len(chunks)} chunks)...")

    requests = []
    skipped = 0
    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        if not force and already_translated(chunk_id):
            skipped += 1
            continue

        entries = load_source_chunk(chunk_id)
        user_content = build_user_payload(chunk, entries)

        requests.append(
            Request(
                custom_id=chunk_id,
                params=MessageCreateParamsNonStreaming(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_INSTRUCTIONS,
                    messages=[{"role": "user", "content": user_content}],
                )
            )
        )

    if skipped:
        print(f"  Skipped {skipped} already-translated chunks")

    if not requests:
        print("  No chunks to translate. Use --force to re-translate.")
        return

    print(f"  Submitting {len(requests)} requests to Anthropic Batch API...")

    # Anthropic batches: max 100,000 requests or 256 MB
    # Submit in sub-batches of 500 to stay manageable
    SUBBATCH_SIZE = 500
    batch_ids = []

    for sb_start in range(0, len(requests), SUBBATCH_SIZE):
        sb_end = min(sb_start + SUBBATCH_SIZE, len(requests))
        sb_requests = requests[sb_start:sb_end]

        batch = client.messages.batches.create(requests=sb_requests)
        batch_ids.append(batch.id)
        print(f"    Sub-batch {sb_start + 1}-{sb_end}: {batch.id} "
              f"(status: {batch.processing_status})")

    # Save batch IDs for later collection
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "batch_ids.json"
    existing = []
    if report_path.exists():
        existing = json.loads(report_path.read_text(encoding="utf-8"))
    existing.extend(batch_ids)
    report_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    print(f"\n  Batch IDs saved to {report_path}")
    print(f"  Monitor with: python scripts/translate_isbe_anthropic.py --mode status --batch-id {batch_ids[0]}")


# ---------------------------------------------------------------------------
# Mode: status
# ---------------------------------------------------------------------------

def check_status(client: anthropic.Anthropic, batch_id: str) -> None:
    batch = client.messages.batches.retrieve(batch_id)
    counts = batch.request_counts
    print(f"Batch: {batch_id}")
    print(f"  Status: {batch.processing_status}")
    print(f"  Processing: {counts.processing}")
    print(f"  Succeeded: {counts.succeeded}")
    print(f"  Errored: {counts.errored}")
    print(f"  Canceled: {counts.canceled}")
    print(f"  Expired: {counts.expired}")


def check_all_status(client: anthropic.Anthropic) -> None:
    report_path = REPORTS_DIR / "batch_ids.json"
    if not report_path.exists():
        print("No batch IDs found. Run --mode batch first.")
        return
    batch_ids = json.loads(report_path.read_text(encoding="utf-8"))
    for bid in batch_ids:
        check_status(client, bid)
        print()


# ---------------------------------------------------------------------------
# Mode: collect
# ---------------------------------------------------------------------------

def collect_results(client: anthropic.Anthropic, batch_id: str) -> None:
    batch = client.messages.batches.retrieve(batch_id)
    if batch.processing_status != "ended":
        print(f"Batch {batch_id} not yet finished (status: {batch.processing_status})")
        return

    print(f"Collecting results from {batch_id}...")
    succeeded = 0
    errored = 0
    parse_errors = 0

    for result in client.messages.batches.results(batch_id):
        chunk_id = result.custom_id

        if result.result.type == "succeeded":
            msg = result.result.message
            # Extract text content
            text = next((b.text for b in msg.content if b.type == "text"), "")

            try:
                parsed = json.loads(text)
                entries = parsed.get("entries", [])
                save_translated_chunk(chunk_id, entries)
                succeeded += 1
            except json.JSONDecodeError:
                parse_errors += 1
                error_dir = BATCH_DIR / "raw_errors" / "batch"
                error_dir.mkdir(parents=True, exist_ok=True)
                (error_dir / f"{chunk_id}.raw.txt").write_text(text, encoding="utf-8")

        elif result.result.type == "errored":
            errored += 1
            print(f"  ERROR {chunk_id}: {result.result.error.type}")

        elif result.result.type in ("canceled", "expired"):
            errored += 1
            print(f"  {result.result.type.upper()} {chunk_id}")

    print(f"\nResults: {succeeded} succeeded, {errored} errored, {parse_errors} parse errors")


def collect_all_results(client: anthropic.Anthropic) -> None:
    report_path = REPORTS_DIR / "batch_ids.json"
    if not report_path.exists():
        print("No batch IDs found.")
        return
    batch_ids = json.loads(report_path.read_text(encoding="utf-8"))
    for bid in batch_ids:
        collect_results(client, bid)
        print()


# ---------------------------------------------------------------------------
# Mode: merge (assemble final isbe.fr.json)
# ---------------------------------------------------------------------------

def merge_translations() -> None:
    """Merge all translated chunks into final isbe.fr.json."""
    manifest = load_manifest()

    # Load original for mot fields
    isbe_path = ROOT / "isbe.json"
    with open(isbe_path, encoding="utf-8") as f:
        original = json.load(f)

    print(f"Merging {len(manifest)} chunks...")

    result = [None] * len(original)
    translated_count = 0
    missing_chunks = []

    for chunk in manifest:
        chunk_id = chunk["chunk_id"]
        translated_path = TRANSLATED_DIR / f"{chunk_id}.json"

        if not translated_path.exists():
            missing_chunks.append(chunk_id)
            # Use original (untranslated) entries as fallback
            for entry_id in chunk["entry_ids"]:
                result[entry_id] = original[entry_id]
            continue

        with open(translated_path, encoding="utf-8-sig") as f:
            entries = json.load(f)

        for entry in entries:
            eid = entry["id"]
            result[eid] = {
                "mot": original[eid]["mot"],  # Always use original mot
                "definition": entry.get("definition", ""),
            }
            translated_count += 1

    # Check for gaps
    gaps = [i for i, r in enumerate(result) if r is None]
    if gaps:
        print(f"  WARNING: {len(gaps)} entries have no translation (filling with original)")
        for i in gaps:
            result[i] = original[i]

    # Write final output
    out_path = ROOT / "isbe.fr.json"
    with open(out_path, "w", encoding="utf-8-sig") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n  Translated entries: {translated_count}/{len(original)}")
    if missing_chunks:
        print(f"  Missing chunks: {len(missing_chunks)}")
        if len(missing_chunks) <= 20:
            print(f"    {missing_chunks}")
    print(f"  Output: {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Translate ISBE using Anthropic Claude API")
    parser.add_argument("--mode", choices=["direct", "batch", "status", "collect", "merge"],
                        default="direct", help="Operation mode")
    parser.add_argument("--start", type=int, default=1, help="First chunk number (1-based)")
    parser.add_argument("--end", type=int, default=0, help="Last chunk number (0=all)")
    parser.add_argument("--batch-id", type=str, default="", help="Batch ID for status/collect")
    parser.add_argument("--force", action="store_true", help="Re-translate already done chunks")
    args = parser.parse_args()

    if args.mode == "merge":
        merge_translations()
        return

    client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
    manifest = load_manifest()

    if args.end == 0:
        args.end = len(manifest)
    args.end = min(args.end, len(manifest))

    print(f"ISBE Translation Pipeline (Anthropic Claude {MODEL})")
    print(f"  Manifest: {len(manifest)} chunks")
    print(f"  Already translated: {sum(1 for c in manifest if already_translated(c['chunk_id']))}")
    print()

    if args.mode == "direct":
        translate_direct(client, manifest, args.start, args.end, args.force)

    elif args.mode == "batch":
        create_batch(client, manifest, args.start, args.end, args.force)

    elif args.mode == "status":
        if args.batch_id:
            check_status(client, args.batch_id)
        else:
            check_all_status(client)

    elif args.mode == "collect":
        if args.batch_id:
            collect_results(client, args.batch_id)
        else:
            collect_all_results(client)


if __name__ == "__main__":
    main()

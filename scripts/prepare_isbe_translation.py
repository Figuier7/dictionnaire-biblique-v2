#!/usr/bin/env python3
"""
Prepare or resume the dedicated ISBE OpenAI batch pipeline.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from isbe_batch_common import (
    DEFAULT_BUDGET,
    DEFAULT_MODEL,
    DEFAULT_SUBBATCH_SIZE,
    ISBE_JSON,
    MANIFEST_PATH,
    REQUESTS_DIR,
    SOURCE_DIR,
    TRANSLATED_DIR,
    V1_MANIFEST_PATH,
    build_batch_request,
    chunk_id_from_number,
    collect_inventory,
    load_chunk_manifest,
    load_v1_chunks,
    parse_chunk_number,
    read_json,
    source_chunk_path,
    write_json,
    write_jsonl,
)

DEFAULT_REQUEST_OUTPUTS = {
    "all": "all_chunk_requests.isbe.jsonl",
    "include": "selected_chunk_requests.isbe.jsonl",
    "missing": "missing_chunk_requests.isbe.jsonl",
    "invalid": "invalid_chunk_requests.isbe.jsonl",
    "resume": "resume_chunk_requests.isbe.jsonl",
    "v1-remaining": "v1_remaining_chunk_requests.isbe.jsonl",
    "phase2": "phase2_chunk_requests.isbe.jsonl",
}


def chunk_entries(entries: list[dict], budget: int) -> list[dict]:
    chunks = []
    current_entries = []
    current_chars = 0
    chunk_num = 0

    for index, entry in enumerate(entries):
        entry_chars = len(entry.get("definition", ""))

        if entry_chars > budget:
            if current_entries:
                chunk_num += 1
                chunks.append(_make_chunk(chunk_num, current_entries, "grouped"))
                current_entries = []
                current_chars = 0

            chunk_num += 1
            mode = "isolated_large" if entry_chars > 80_000 else "isolated"
            chunks.append(_make_chunk(chunk_num, [{"id": index, **entry}], mode))
            continue

        if current_chars + entry_chars > budget and current_entries:
            chunk_num += 1
            chunks.append(_make_chunk(chunk_num, current_entries, "grouped"))
            current_entries = []
            current_chars = 0

        current_entries.append({"id": index, **entry})
        current_chars += entry_chars

    if current_entries:
        chunk_num += 1
        chunks.append(_make_chunk(chunk_num, current_entries, "grouped"))

    return chunks


def _make_chunk(num: int, entries: list[dict], mode: str) -> dict:
    return {
        "chunk_id": chunk_id_from_number(num),
        "chunk_mode": mode,
        "entry_count": len(entries),
        "entry_ids": [entry["id"] for entry in entries],
        "entries": entries,
    }


def write_source_chunks(chunks: list[dict], source_dir: Path) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    for chunk in chunks:
        path = source_dir / f"{chunk['chunk_id']}.source.json"
        write_json(path, chunk["entries"])


def write_manifest(chunks: list[dict], manifest_path: Path) -> None:
    manifest = []
    for chunk in chunks:
        manifest.append(
            {
                "chunk_id": chunk["chunk_id"],
                "chunk_mode": chunk["chunk_mode"],
                "entry_count": chunk["entry_count"],
                "entry_ids": chunk["entry_ids"],
                "status": "pending",
            }
        )
    write_json(manifest_path, manifest)


def parse_chunk_id_list(value: str) -> list[str]:
    return [token.strip() for token in value.split(",") if token.strip()]


def select_chunks_for_requests(
    manifest: list[dict],
    request_mode: str,
    *,
    include_chunk_ids: list[str],
    inventory: dict,
    v1_chunks: list[dict] | None,
) -> list[dict]:
    chunk_map = {chunk["chunk_id"]: chunk for chunk in manifest}
    valid_set = set(inventory["valid_chunk_ids"])
    invalid_set = {row["chunk_id"] for row in inventory["invalid_chunks"]}
    missing_set = set(inventory["missing_chunk_ids"])

    if request_mode == "all":
        selected_ids = [chunk["chunk_id"] for chunk in manifest]
    elif request_mode == "include":
        if not include_chunk_ids:
            raise ValueError("--include-chunk-ids is required when --request-mode include")
        missing_ids = [chunk_id for chunk_id in include_chunk_ids if chunk_id not in chunk_map]
        if missing_ids:
            raise ValueError(f"Unknown chunk ids: {', '.join(missing_ids)}")
        selected_ids = include_chunk_ids
    elif request_mode == "missing":
        selected_ids = sorted(missing_set, key=parse_chunk_number)
    elif request_mode == "invalid":
        selected_ids = sorted(invalid_set, key=parse_chunk_number)
    elif request_mode == "resume":
        selected_ids = sorted(missing_set | invalid_set, key=parse_chunk_number)
    elif request_mode == "v1-remaining":
        if not v1_chunks:
            raise ValueError("A V1 manifest is required for --request-mode v1-remaining")
        selected_ids = [chunk["chunk_id"] for chunk in v1_chunks if chunk["chunk_id"] not in valid_set]
    elif request_mode == "phase2":
        if not v1_chunks:
            raise ValueError("A V1 manifest is required for --request-mode phase2")
        v1_set = {chunk["chunk_id"] for chunk in v1_chunks}
        selected_ids = [chunk["chunk_id"] for chunk in manifest if chunk["chunk_id"] not in v1_set and chunk["chunk_id"] not in valid_set]
    else:
        raise ValueError(f"Unsupported request mode: {request_mode}")

    return [chunk_map[chunk_id] for chunk_id in selected_ids]


def build_requests_for_chunks(
    chunks: list[dict],
    *,
    source_dir: Path,
    model: str,
) -> tuple[list[dict], list[dict]]:
    requests = []
    plan_rows = []

    for chunk in chunks:
        source_entries = read_json(source_chunk_path(chunk["chunk_id"], source_dir))
        requests.append(build_batch_request(chunk, source_entries, model=model))
        plan_rows.append(
            {
                "chunk_id": chunk["chunk_id"],
                "chunk_mode": chunk["chunk_mode"],
                "entry_count": chunk["entry_count"],
                "entry_ids": chunk["entry_ids"],
                "source_file": str(source_chunk_path(chunk["chunk_id"], source_dir)),
            }
        )

    return requests, plan_rows


def write_request_batches(
    requests: list[dict],
    *,
    out_jsonl: Path,
    out_plan: Path,
    plan_rows: list[dict],
    subbatch_size: int,
    metadata: dict,
) -> None:
    write_jsonl(out_jsonl, requests)

    subbatch_files = []
    if requests:
        base_name = out_jsonl.name[:-6] if out_jsonl.name.endswith(".jsonl") else out_jsonl.stem
        for start in range(0, len(requests), subbatch_size):
            batch_slice = requests[start : start + subbatch_size]
            first_id = batch_slice[0]["custom_id"]
            last_id = batch_slice[-1]["custom_id"]
            subbatch_name = f"{base_name}.part{(start // subbatch_size) + 1:02d}.{first_id}_{last_id}.jsonl"
            subbatch_path = out_jsonl.parent / subbatch_name
            write_jsonl(subbatch_path, batch_slice)
            subbatch_files.append(str(subbatch_path))

    plan = {
        "metadata": metadata,
        "request_count": len(requests),
        "requests": plan_rows,
        "subbatch_files": subbatch_files,
    }
    write_json(out_plan, plan)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare or resume the ISBE OpenAI batch pipeline")
    parser.add_argument("--mode", choices=["prepare", "requests"], default="prepare")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model to use")
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET, help="Character budget per chunk in prepare mode")
    parser.add_argument("--subbatch-size", type=int, default=DEFAULT_SUBBATCH_SIZE, help="Requests per subbatch JSONL file")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH), help="Chunk manifest path")
    parser.add_argument("--v1-manifest", default=str(V1_MANIFEST_PATH), help="V1 manifest path")
    parser.add_argument("--source-dir", default=str(SOURCE_DIR), help="Source chunk directory")
    parser.add_argument("--translated-dir", default=str(TRANSLATED_DIR), help="Translated chunk directory")
    parser.add_argument("--request-mode", choices=sorted(DEFAULT_REQUEST_OUTPUTS), default="all", help="Chunk selection mode in requests mode")
    parser.add_argument("--include-chunk-ids", default="", help="Comma-separated chunk ids when using request-mode include")
    parser.add_argument("--out-jsonl", default="", help="Consolidated JSONL output path")
    parser.add_argument("--out-plan", default="", help="Request plan JSON path")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit on selected chunks")
    return parser.parse_args()


def run_prepare_mode(args: argparse.Namespace) -> None:
    source_dir = Path(args.source_dir)
    manifest_path = Path(args.manifest)

    print(f"Loading {ISBE_JSON} ...")
    with ISBE_JSON.open(encoding="utf-8") as handle:
        entries = json.load(handle)
    print(f"  {len(entries)} entries, {sum(len(item.get('definition', '')) for item in entries):,} chars total")

    print(f"\nChunking with budget={args.budget:,} chars ...")
    chunks = chunk_entries(entries, args.budget)
    grouped = [chunk for chunk in chunks if chunk["chunk_mode"] == "grouped"]
    isolated = [chunk for chunk in chunks if chunk["chunk_mode"] == "isolated"]
    isolated_large = [chunk for chunk in chunks if chunk["chunk_mode"] == "isolated_large"]
    print(f"  Total chunks: {len(chunks)}")
    print(f"    grouped: {len(grouped)}")
    print(f"    isolated: {len(isolated)}")
    print(f"    isolated_large (>80k): {len(isolated_large)}")

    print(f"\nWriting source chunks to {source_dir} ...")
    write_source_chunks(chunks, source_dir)
    print(f"  {len(chunks)} chunk files written")

    print(f"\nWriting manifest to {manifest_path} ...")
    write_manifest(chunks, manifest_path)

    requests, plan_rows = build_requests_for_chunks(chunks, source_dir=source_dir, model=args.model)
    out_jsonl = Path(args.out_jsonl) if args.out_jsonl else REQUESTS_DIR / DEFAULT_REQUEST_OUTPUTS["all"]
    out_plan = Path(args.out_plan) if args.out_plan else out_jsonl.with_suffix(".plan.json")
    metadata = {
        "mode": args.mode,
        "request_mode": "all",
        "manifest": str(manifest_path),
        "source_dir": str(source_dir),
        "translated_dir": str(Path(args.translated_dir)),
        "model": args.model,
        "budget": args.budget,
    }
    print(f"\nGenerating batch JSONL (model={args.model}) ...")
    write_request_batches(
        requests,
        out_jsonl=out_jsonl,
        out_plan=out_plan,
        plan_rows=plan_rows,
        subbatch_size=args.subbatch_size,
        metadata=metadata,
    )
    print(f"  Consolidated: {out_jsonl}")
    print(f"  Plan: {out_plan}")
    print("\n[OK] ISBE translation pipeline ready.")


def run_requests_mode(args: argparse.Namespace) -> None:
    manifest_path = Path(args.manifest)
    source_dir = Path(args.source_dir)
    translated_dir = Path(args.translated_dir)
    v1_manifest_path = Path(args.v1_manifest)

    manifest = load_chunk_manifest(manifest_path)
    v1_chunks = load_v1_chunks(v1_manifest_path) if v1_manifest_path.exists() else None
    inventory = collect_inventory(manifest, source_dir=source_dir, translated_dir=translated_dir, v1_chunks=v1_chunks)
    include_chunk_ids = parse_chunk_id_list(args.include_chunk_ids)
    selected_chunks = select_chunks_for_requests(
        manifest,
        args.request_mode,
        include_chunk_ids=include_chunk_ids,
        inventory=inventory,
        v1_chunks=v1_chunks,
    )
    if args.limit > 0:
        selected_chunks = selected_chunks[: args.limit]

    if not selected_chunks:
        raise ValueError("No chunk selected for request generation.")

    requests, plan_rows = build_requests_for_chunks(selected_chunks, source_dir=source_dir, model=args.model)
    default_name = DEFAULT_REQUEST_OUTPUTS[args.request_mode]
    out_jsonl = Path(args.out_jsonl) if args.out_jsonl else REQUESTS_DIR / default_name
    out_plan = Path(args.out_plan) if args.out_plan else out_jsonl.with_suffix(".plan.json")
    metadata = {
        "mode": args.mode,
        "request_mode": args.request_mode,
        "manifest": str(manifest_path),
        "v1_manifest": str(v1_manifest_path),
        "source_dir": str(source_dir),
        "translated_dir": str(translated_dir),
        "model": args.model,
        "selected_chunk_count": len(selected_chunks),
        "selected_chunk_ids_preview": [chunk["chunk_id"] for chunk in selected_chunks[:20]],
        "inventory_summary": inventory["summary"],
    }
    write_request_batches(
        requests,
        out_jsonl=out_jsonl,
        out_plan=out_plan,
        plan_rows=plan_rows,
        subbatch_size=args.subbatch_size,
        metadata=metadata,
    )

    print(json.dumps(inventory["summary"], ensure_ascii=False, indent=2))
    print(f"\nSelected {len(selected_chunks)} chunks for request-mode={args.request_mode}")
    print(f"Consolidated: {out_jsonl}")
    print(f"Plan: {out_plan}")


def main() -> None:
    args = parse_args()
    if args.mode == "prepare":
        run_prepare_mode(args)
    else:
        run_requests_mode(args)


if __name__ == "__main__":
    main()

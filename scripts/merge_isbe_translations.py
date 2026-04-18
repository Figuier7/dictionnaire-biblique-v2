#!/usr/bin/env python3
"""
Merge the translated ISBE chunks into uploads/dictionnaires/isbe/isbe.fr.json.
"""

from __future__ import annotations

import argparse
import json
from json import JSONDecodeError
from pathlib import Path

from isbe_batch_common import (
    ISBE_JSON,
    MANIFEST_PATH,
    MERGED_PATH,
    PRIORITY_CIRCLES_PATH,
    TRANSLATED_DIR,
    UPLOADS_ISBE_DIR,
    load_chunk_manifest,
    load_priority_circle_map,
    read_json,
    translated_chunk_path,
    transpose_c4_definition,
    validate_chunk_structure,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge ISBE translated chunks into the final target JSON")
    parser.add_argument("--source", default=str(ISBE_JSON), help="Source isbe.json path")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH), help="Chunk manifest")
    parser.add_argument("--translated-dir", default=str(TRANSLATED_DIR), help="Translated chunk directory")
    parser.add_argument("--priority-circles", default=str(PRIORITY_CIRCLES_PATH), help="ISBE circle classification file")
    parser.add_argument("--out", default=str(MERGED_PATH), help="Final merged JSON path")
    parser.add_argument("--report", default=str(UPLOADS_ISBE_DIR / "isbe.merge_report.json"), help="Merge report path")
    parser.add_argument(
        "--allow-c4-fallback",
        action="store_true",
        help="Allow deterministic fallback for untranslated C4 redirects and empty stubs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_entries = read_json(Path(args.source))
    manifest = load_chunk_manifest(Path(args.manifest))
    translated_dir = Path(args.translated_dir)
    out_path = Path(args.out)
    report_path = Path(args.report)

    circle_map = load_priority_circle_map(Path(args.priority_circles))
    translated_by_id: dict[int, dict[str, str]] = {}
    merge_sources: dict[int, str] = {}
    translated_chunk_count = 0
    invalid_chunks: list[dict[str, str]] = []

    for chunk in manifest:
        chunk_id = chunk["chunk_id"]
        translated_path = translated_chunk_path(chunk_id, translated_dir)
        if not translated_path.exists():
            continue

        try:
            translated_entries = read_json(translated_path)
        except (JSONDecodeError, ValueError) as exc:
            invalid_chunks.append(
                {
                    "chunk_id": chunk_id,
                    "path": str(translated_path),
                    "reason": f"unparseable_json: {exc}",
                }
            )
            continue

        source_chunk_entries = [
            {"id": entry_id, "mot": source_entries[entry_id]["mot"], "definition": source_entries[entry_id]["definition"]}
            for entry_id in chunk["entry_ids"]
        ]
        normalized_entries, issues = validate_chunk_structure(source_chunk_entries, translated_entries)
        if issues:
            invalid_chunks.append(
                {
                    "chunk_id": chunk_id,
                    "path": str(translated_path),
                    "reason": issues[0]["message"],
                }
            )
            continue

        translated_chunk_count += 1
        for entry in normalized_entries:
            translated_by_id[entry["id"]] = {"mot": entry["mot"], "definition": entry["definition"]}
            merge_sources[entry["id"]] = "translated_chunk"

    merged_entries: list[dict[str, str]] = []
    c4_fallback_count = 0
    missing_ids: list[int] = []

    for entry_id, source_entry in enumerate(source_entries):
        translated = translated_by_id.get(entry_id)
        if translated is not None:
            merged_entries.append(translated)
            continue

        if args.allow_c4_fallback and circle_map.get(entry_id) == "C4":
            merged_entries.append(
                {
                    "mot": source_entry["mot"],
                    "definition": transpose_c4_definition(source_entry.get("definition", "")),
                }
            )
            merge_sources[entry_id] = "c4_fallback"
            c4_fallback_count += 1
            continue

        missing_ids.append(entry_id)

    report = {
        "summary": {
            "entry_count": len(merged_entries),
            "translated_chunk_count": translated_chunk_count,
            "c4_fallback_count": c4_fallback_count,
            "invalid_chunk_count": len(invalid_chunks),
            "missing_id_count": len(missing_ids),
        },
        "invalid_chunks": invalid_chunks,
        "missing_ids": missing_ids,
        "merge_sources": merge_sources,
    }

    if missing_ids:
        write_json(report_path, report)
        preview = ", ".join(str(item) for item in missing_ids[:20])
        raise ValueError(
            f"Cannot merge final ISBE output. Missing translated ids: {preview}. "
            f"Invalid chunks: {len(invalid_chunks)}. Report written to {report_path}"
        )

    write_json(out_path, merged_entries)
    write_json(report_path, report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"\nSaved merged ISBE file to {out_path}")


if __name__ == "__main__":
    main()

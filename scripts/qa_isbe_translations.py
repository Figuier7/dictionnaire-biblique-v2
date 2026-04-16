#!/usr/bin/env python3
"""
Run structural and ratio QA on selected ISBE translated chunks.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from isbe_batch_common import (
    MANIFEST_PATH,
    REPORTS_DIR,
    SOURCE_DIR,
    TRANSLATED_DIR,
    load_chunk_manifest,
    parse_chunk_number,
    qa_chunk_translation,
    read_json,
    source_chunk_path,
    translated_chunk_path,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QA current ISBE translated chunks")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH), help="Full chunk manifest")
    parser.add_argument("--source-dir", default=str(SOURCE_DIR), help="Source chunk directory")
    parser.add_argument("--translated-dir", default=str(TRANSLATED_DIR), help="Translated chunk directory")
    parser.add_argument("--include-chunk-ids", default="", help="Comma-separated chunk ids to QA")
    parser.add_argument("--min-ratio-hard", type=float, default=0.35, help="Hard minimum translated/source ratio")
    parser.add_argument("--min-ratio-warn", type=float, default=0.5, help="Warning minimum translated/source ratio")
    parser.add_argument("--max-ratio-warn", type=float, default=2.2, help="Warning maximum translated/source ratio")
    parser.add_argument("--max-ratio-hard", type=float, default=3.0, help="Hard maximum translated/source ratio")
    parser.add_argument(
        "--report",
        default=str(REPORTS_DIR / "isbe_qa_latest.json"),
        help="Path of the QA JSON report",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = load_chunk_manifest(Path(args.manifest))
    source_dir = Path(args.source_dir)
    translated_dir = Path(args.translated_dir)
    report_path = Path(args.report)

    include_set = {item.strip() for item in args.include_chunk_ids.split(",") if item.strip()}
    chunks = [chunk for chunk in manifest if not include_set or chunk["chunk_id"] in include_set]
    chunks = sorted(chunks, key=lambda chunk: parse_chunk_number(chunk["chunk_id"]))

    qa_rows: list[dict[str, object]] = []
    missing_chunk_ids: list[str] = []

    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        translated_path = translated_chunk_path(chunk_id, translated_dir)
        if not translated_path.exists():
            missing_chunk_ids.append(chunk_id)
            qa_rows.append(
                {
                    "chunk_id": chunk_id,
                    "status": "missing",
                    "summary": {
                        "source_entry_count": chunk["entry_count"],
                        "translated_entry_count": 0,
                        "error_count": 1,
                        "warning_count": 0,
                    },
                    "chunk_issues": [{"code": "missing_translated_chunk", "message": "Translated chunk file is missing."}],
                    "entries": [],
                }
            )
            continue

        try:
            translated_entries = read_json(translated_path)
        except Exception as exc:  # noqa: BLE001
            qa_rows.append(
                {
                    "chunk_id": chunk_id,
                    "status": "error",
                    "summary": {
                        "source_entry_count": chunk["entry_count"],
                        "translated_entry_count": 0,
                        "error_count": 1,
                        "warning_count": 0,
                    },
                    "chunk_issues": [{"code": "invalid_translated_json", "message": str(exc)}],
                    "entries": [],
                }
            )
            continue

        source_entries = read_json(source_chunk_path(chunk_id, source_dir))
        qa_rows.append(
            qa_chunk_translation(
                chunk_id,
                source_entries,
                translated_entries,
                min_ratio_hard=args.min_ratio_hard,
                min_ratio_warn=args.min_ratio_warn,
                max_ratio_warn=args.max_ratio_warn,
                max_ratio_hard=args.max_ratio_hard,
            )
        )

    summary = {
        "selected_chunk_count": len(chunks),
        "ok_chunk_count": sum(1 for row in qa_rows if row["status"] == "ok"),
        "warning_chunk_count": sum(1 for row in qa_rows if row["status"] == "warning"),
        "error_chunk_count": sum(1 for row in qa_rows if row["status"] == "error"),
        "missing_chunk_count": len(missing_chunk_ids),
        "missing_chunk_ids": missing_chunk_ids,
    }
    report = {"summary": summary, "chunks": qa_rows}
    write_json(report_path, report)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nSaved QA report to {report_path}")


if __name__ == "__main__":
    main()

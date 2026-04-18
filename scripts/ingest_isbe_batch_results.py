#!/usr/bin/env python3
"""
Ingest OpenAI Batch JSONL results into work/codex_local_isbe/translated_chunks.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from isbe_batch_common import (
    MANIFEST_PATH,
    RAW_ERRORS_DIR,
    REPORTS_DIR,
    SOURCE_DIR,
    TRANSLATED_DIR,
    extract_result_text,
    load_chunk_manifest,
    parse_batch_envelope,
    read_json,
    read_jsonl,
    source_chunk_path,
    translated_chunk_path,
    validate_chunk_structure,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest ISBE OpenAI Batch results")
    parser.add_argument("--results-jsonl", required=True, help="Batch results JSONL file")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH), help="Full chunk manifest")
    parser.add_argument("--source-dir", default=str(SOURCE_DIR), help="Directory containing source chunk files")
    parser.add_argument("--translated-dir", default=str(TRANSLATED_DIR), help="Directory where translated chunks are written")
    parser.add_argument(
        "--report",
        default=str(REPORTS_DIR / "isbe_ingest_latest.json"),
        help="Path of the ingest JSON report",
    )
    parser.add_argument(
        "--raw-error-dir",
        default=str(RAW_ERRORS_DIR / "chunk"),
        help="Directory where invalid raw payloads are dumped",
    )
    parser.add_argument("--overwrite-existing", action="store_true", help="Allow overwriting existing translated chunks")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results_path = Path(args.results_jsonl)
    manifest = load_chunk_manifest(Path(args.manifest))
    source_dir = Path(args.source_dir)
    translated_dir = Path(args.translated_dir)
    report_path = Path(args.report)
    raw_error_dir = Path(args.raw_error_dir)

    manifest_map = {chunk["chunk_id"]: chunk for chunk in manifest}
    rows = read_jsonl(results_path)
    report_rows: list[dict[str, object]] = []

    for row in rows:
        custom_id = str(row.get("custom_id", "")).strip()
        status = "ok"
        message = ""
        status_code = None
        wrapper_type = ""
        target_file = ""
        entry_count = 0

        if not custom_id:
            report_rows.append(
                {
                    "custom_id": custom_id,
                    "status": "error",
                    "status_code": None,
                    "wrapper_type": "",
                    "entry_count": 0,
                    "target_file": "",
                    "message": "Batch result row has no custom_id.",
                }
            )
            continue

        content, status_code, error_message = extract_result_text(row)

        if custom_id not in manifest_map:
            status = "error"
            message = f"Unknown chunk_id in results: {custom_id}"
        elif error_message:
            status = "error"
            message = error_message
        elif not content:
            status = "error"
            message = "No usable response content found."

        if status == "ok":
            target_path = translated_chunk_path(custom_id, translated_dir)
            target_file = str(target_path)
            if target_path.exists() and not args.overwrite_existing:
                status = "error"
                message = f"Target file already exists: {target_path}"

        if status == "ok":
            try:
                parsed_entries, wrapper_type = parse_batch_envelope(content, custom_id)
                source_entries = read_json(source_chunk_path(custom_id, source_dir))
                normalized_entries, structure_issues = validate_chunk_structure(source_entries, parsed_entries)
                if structure_issues:
                    raise ValueError(structure_issues[0]["message"])
                write_json(Path(target_file), normalized_entries)
                entry_count = len(normalized_entries)
            except Exception as exc:  # noqa: BLE001
                status = "error"
                message = str(exc)
                raw_error_dir.mkdir(parents=True, exist_ok=True)
                (raw_error_dir / f"{custom_id}.raw.txt").write_text(content or "", encoding="utf-8")

        report_rows.append(
            {
                "custom_id": custom_id,
                "status": status,
                "status_code": status_code,
                "wrapper_type": wrapper_type,
                "entry_count": entry_count,
                "target_file": target_file,
                "message": message,
            }
        )

    summary = {
        "results_jsonl": str(results_path),
        "total_count": len(report_rows),
        "success_count": sum(1 for row in report_rows if row["status"] == "ok"),
        "error_count": sum(1 for row in report_rows if row["status"] == "error"),
    }
    report = {"summary": summary, "results": report_rows}
    write_json(report_path, report)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nSaved ingest report to {report_path}")


if __name__ == "__main__":
    main()

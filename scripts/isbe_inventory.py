#!/usr/bin/env python3
"""
Build an actionable inventory of the current ISBE translation workspace.
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
    V1_MANIFEST_PATH,
    collect_inventory,
    load_chunk_manifest,
    load_v1_chunks,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect the current ISBE translation inventory")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH), help="Full ISBE chunk manifest")
    parser.add_argument("--v1-manifest", default=str(V1_MANIFEST_PATH), help="Optional V1 chunk manifest")
    parser.add_argument("--source-dir", default=str(SOURCE_DIR), help="Directory containing source chunk files")
    parser.add_argument("--translated-dir", default=str(TRANSLATED_DIR), help="Directory containing translated chunk files")
    parser.add_argument(
        "--report",
        default=str(REPORTS_DIR / "isbe_inventory_latest.json"),
        help="Path of the JSON inventory report to write",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = load_chunk_manifest(Path(args.manifest))
    v1_chunks = load_v1_chunks(Path(args.v1_manifest)) if Path(args.v1_manifest).exists() else None
    inventory = collect_inventory(
        manifest,
        source_dir=Path(args.source_dir),
        translated_dir=Path(args.translated_dir),
        v1_chunks=v1_chunks,
    )
    report_path = Path(args.report)
    write_json(report_path, inventory)
    print(json.dumps(inventory["summary"], ensure_ascii=False, indent=2))
    print(f"\nSaved inventory report to {report_path}")


if __name__ == "__main__":
    main()

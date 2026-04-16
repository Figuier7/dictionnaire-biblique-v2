#!/usr/bin/env python3
"""Merge batch + repair outputs into eastons_fr.json and proper_nouns_unknown.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="eastons.json")
    parser.add_argument("--batch-results", default="out/results.jsonl")
    parser.add_argument("--repair-results", default="out/repair_results.jsonl")
    parser.add_argument("--out", default="eastons_fr.json")
    parser.add_argument("--out-proper", default="proper_nouns_unknown.json")
    return parser.parse_args()


def extract_content(obj: dict[str, Any]) -> tuple[str | None, str | None]:
    cid = obj.get("custom_id")
    response = obj.get("response", {})
    body = response.get("body", {}) if isinstance(response, dict) else {}
    choices = body.get("choices", []) if isinstance(body, dict) else []
    if not choices:
        return cid, None
    message = choices[0].get("message", {})
    content = message.get("content")
    if isinstance(content, str):
        return cid, content
    if isinstance(content, list):
        return cid, "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return cid, None


def read_jsonl_map(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            cid, raw = extract_content(obj)
            if cid is None or raw is None:
                continue
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not all(k in parsed for k in ("id", "mot", "definition", "proper_nouns_unknown")):
                continue
            if not isinstance(parsed.get("mot"), str) or not isinstance(parsed.get("definition"), str):
                continue
            if not isinstance(parsed.get("proper_nouns_unknown"), list):
                continue
            out[cid] = parsed
    return out


def main() -> None:
    args = parse_args()
    source = json.loads(Path(args.source).read_text(encoding="utf-8"))

    batch_map = read_jsonl_map(Path(args.batch_results))
    repair_map = read_jsonl_map(Path(args.repair_results))

    final_entries: list[dict[str, str]] = []
    proper_nouns: set[str] = set()

    for idx, _src in enumerate(source):
        cid = str(idx)
        translated = repair_map.get(cid) or batch_map.get(cid)
        if translated is None:
            raise ValueError(f"Missing valid translation for id={cid}")

        final_entries.append({"mot": translated["mot"], "definition": translated["definition"]})

        for noun in translated["proper_nouns_unknown"]:
            if isinstance(noun, str) and noun.strip():
                proper_nouns.add(noun.strip())

    Path(args.out).write_text(json.dumps(final_entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.out_proper).write_text(
        json.dumps(sorted(proper_nouns), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Wrote {len(final_entries)} entries to {args.out}")
    print(f"Wrote {len(proper_nouns)} proper nouns to {args.out_proper}")


if __name__ == "__main__":
    main()

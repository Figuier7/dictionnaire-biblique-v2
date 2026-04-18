#!/usr/bin/env python3
"""QA checker for OpenAI batch translation results."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

FORBIDDEN_PATTERNS = [
    ("residual_av_rv", "A.V."),
    ("residual_av_rv", "R.V."),
    ("residual_av_rv", "Authorized Version"),
    ("residual_av_rv", "Revised Version"),
    ("forbidden_name", "Dieu"),
    ("forbidden_name", "l’Éternel"),
    ("forbidden_name", "l'Eternel"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="eastons.json")
    parser.add_argument("--results", default="out/results.jsonl")
    parser.add_argument("--out", default="out/qa_report.csv")
    parser.add_argument("--min-ratio", type=float, default=0.55, help="Min char-length ratio FR/source")
    return parser.parse_args()


def extract_content(result_line: dict[str, Any]) -> tuple[str | None, str | None]:
    custom_id = result_line.get("custom_id")
    response = result_line.get("response", {})
    body = response.get("body", {}) if isinstance(response, dict) else {}
    choices = body.get("choices", []) if isinstance(body, dict) else []
    if not choices:
        return custom_id, None
    message = choices[0].get("message", {})
    content = message.get("content")
    if isinstance(content, str):
        return custom_id, content
    if isinstance(content, list):
        text_chunks = [c.get("text", "") for c in content if isinstance(c, dict)]
        return custom_id, "".join(text_chunks)
    return custom_id, None


def load_results(path: Path) -> dict[str, str | None]:
    outputs: dict[str, str | None] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            cid, content = extract_content(obj)
            if cid is not None:
                outputs[cid] = content
    return outputs


def issue_row(rows: list[list[str]], cid: str, mot: str, issue: str, details: str) -> None:
    rows.append([cid, mot, issue, details])


def main() -> None:
    args = parse_args()
    source_entries = json.loads(Path(args.source).read_text(encoding="utf-8"))
    results_map = load_results(Path(args.results))

    rows: list[list[str]] = []
    for idx, src in enumerate(source_entries):
        cid = str(idx)
        mot_source = src.get("mot", "")
        src_def = src.get("definition", "")
        raw = results_map.get(cid)

        if raw is None:
            issue_row(rows, cid, mot_source, "missing_or_empty_response", "No usable content in batch output")
            continue

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            issue_row(rows, cid, mot_source, "invalid_json", str(exc))
            continue

        missing = [k for k in ("id", "mot", "definition", "proper_nouns_unknown") if k not in parsed]
        if missing:
            issue_row(rows, cid, mot_source, "missing_fields", ",".join(missing))
            continue

        fr_def = parsed.get("definition")
        if not isinstance(fr_def, str):
            issue_row(rows, cid, mot_source, "invalid_definition_type", type(fr_def).__name__)
            continue

        src_len = max(len(src_def.strip()), 1)
        ratio = len(fr_def.strip()) / src_len
        if ratio < args.min_ratio:
            issue_row(rows, cid, mot_source, "suspected_truncation", f"ratio={ratio:.3f} < {args.min_ratio}")

        for issue, token in FORBIDDEN_PATTERNS:
            if token in fr_def:
                issue_row(rows, cid, mot_source, issue, f'Found token: "{token}"')

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "mot_source", "issue", "details"])
        writer.writerows(rows)

    print(f"Wrote QA report with {len(rows)} issues to {out_path}")


if __name__ == "__main__":
    main()

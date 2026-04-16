#!/usr/bin/env python3
"""Build repair batch JSONL from QA failures."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

SYSTEM_INSTRUCTIONS = """Mode réparation. Refaire la traduction COMPLÈTE de l'entrée.
Contraintes strictes:
- Zéro troncage, zéro ajout, zéro résumé.
- Respect strict des règles AGENTS: Elohîm/YHWH, LORD vs Lord, A.V./R.V. King James, refs Ostervald, Revelation, règles Yehoshoua/Mashiah.
- Interdits dans definition: "Dieu" (majuscule), "l'Éternel".
- Retourner uniquement un JSON valide exactement: {"id":"...","mot":"...","definition":"...","proper_nouns_unknown":[]}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="eastons.json")
    parser.add_argument("--qa", default="out/qa_report.csv")
    parser.add_argument("--out", default="out/repair_batch.jsonl")
    parser.add_argument("--model", default="gpt-5-mini")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_entries = json.loads(Path(args.source).read_text(encoding="utf-8"))

    failed_ids: set[str] = set()
    with Path(args.qa).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            failed_ids.add(str(row["id"]))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as out:
        for cid in sorted(failed_ids, key=lambda x: int(x)):
            src = source_entries[int(cid)]
            prompt = {
                "id": cid,
                "mot_source": src["mot"],
                "definition_source": src["definition"],
                "task": "Réparer en retraduisant toute l'entrée, sans patch partiel.",
            }
            req = {
                "custom_id": cid,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": args.model,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                        {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                    ],
                },
            }
            out.write(json.dumps(req, ensure_ascii=False) + "\n")

    print(f"Wrote {len(failed_ids)} repair requests to {out_path}")


if __name__ == "__main__":
    main()

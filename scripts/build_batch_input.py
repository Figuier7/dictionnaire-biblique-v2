#!/usr/bin/env python3
"""Build OpenAI Batch JSONL input from eastons.json (1 request per entry)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SYSTEM_INSTRUCTIONS = """Tu es un traducteur théologique expert. Respecte STRICTEMENT ces règles:
- Traduire intégralement chaque définition, zéro troncage, zéro ajout.
- Conserver ponctuation, guillemets, parenthèses, abréviations, renvois "Comp.", "marg.", et retours à la ligne utiles.
- Sortie JSON stricte: {"id":"...","mot":"...","definition":"...","proper_nouns_unknown":[]}.
- Champ mot: traduire en français classique; exception unique: si mot source == "God", sortir "El".
- Dans definition (nom propre biblique): God=>Elohîm; LORD/the LORD/Jehovah/Yahweh=>YHWH; Jah=>Yah; LORD God=>YHWH Elohîm.
- Dans definition (nom commun païen): god/gods=>dieu/dieux (minuscule).
- Distinction: LORD=>YHWH; Lord=>Seigneur. Ne jamais utiliser "l'Éternel".
- Interdit dans definition: "Dieu" (majuscule) et "l'Éternel".
- Références bibliques style Ostervald: garder abrégé vs entier comme source anglaise, adapter noms de livres en français Ostervald, conserver chapitres/versets/plages exacts.
- Revelation (livre) => Apoc./Apocalypse; sinon revelation => révélation.
- A.V. => "dans la version autorisée de la King James".
- R.V. => "dans la version révisée de la King James".
- Authorized Version => "la version autorisée de la King James".
- Revised Version => "la version révisée de la King James".
- Règles Yehoshoua/Mashiah en ordre strict (du plus spécifique au plus général):
  Jesus Christ=>Yehoshoua Mashiah (Jésus-Christ);
  Jesus the Christ=>Yehoshoua (Jésus) le Mashiah (Christ);
  Jesus, the Christ=>Yehoshoua (Jésus), le Mashiah (Christ);
  Jesus the Messiah=>Yehoshoua (Jésus) le Messie;
  Jesus, the Messiah=>Yehoshoua (Jésus), le Messie;
  Christ Jesus=>Mashiah (Christ) Yehoshoua (Jésus);
  the Christ/The Christ=>le/Le Mashiah (Christ);
  the Messiah/The Messiah=>le/Le Messie;
  Jesus' ou Jesus's=>de Yehoshoua (Jésus);
  Christ' ou Christ's=>du Mashiah (Christ);
  Jesus=>Yehoshoua (Jésus);
  Christ=>Mashiah (Christ);
  Messiah=>Messie.
- Cas possessifs composés: Jesus Christ's=>de Yehoshoua Mashiah (Jésus-Christ); Christ Jesus's=>de Mashiah (Christ) Yehoshoua (Jésus).
- Ne jamais produire "Yehoshoua (Jésus) Mashiah (Christ)" pour "Jesus Christ".
- Ne pas altérer les références bibliques.
- Idempotence: si les formes FR cibles existent déjà, ne pas les modifier.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="eastons.json", help="Path to source Easton JSON")
    parser.add_argument("--out", default="out/batch_input.jsonl", help="Path to output JSONL")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of entries for tests")
    parser.add_argument("--model", default="gpt-5-mini", help="Model used in batch requests")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_path = Path(args.source)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    entries = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError("eastons.json doit être un tableau d'objets")

    if args.limit is not None:
        entries = entries[: args.limit]

    with out_path.open("w", encoding="utf-8") as f:
        for idx, item in enumerate(entries):
            if not isinstance(item, dict) or "mot" not in item or "definition" not in item:
                raise ValueError(f"Entrée invalide à l'index {idx}")
            custom_id = str(idx)
            user_prompt = {
                "id": custom_id,
                "mot_source": item["mot"],
                "definition_source": item["definition"],
                "task": "Traduire vers le français en respectant toutes les règles système et retourner uniquement le JSON demandé.",
            }
            request = {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": args.model,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                        {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
                    ],
                },
            }
            f.write(json.dumps(request, ensure_ascii=False) + "\n")

    print(f"Wrote {len(entries)} requests to {out_path}")


if __name__ == "__main__":
    main()

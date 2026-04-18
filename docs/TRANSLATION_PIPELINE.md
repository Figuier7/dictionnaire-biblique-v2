# Pipeline de traduction Easton - Mode batch/API

Ce document decrit uniquement le mode `batch/API`.

Il ne decrit pas le mode `100% Codex App local`.

Pour la separation des deux modes et la structure cible du projet :

- voir `docs/TRANSLATION_MODES.md`
- voir `docs/CODEX_APP_LOCAL_MODE.md`

Ce pipeline produit:
- `out/batch_input.jsonl`
- `out/results.jsonl`
- `out/qa_report.csv`
- `out/repair_batch.jsonl`
- `out/repair_results.jsonl`
- `eastons_fr.json`
- `proper_nouns_unknown.json`

## Prérequis

- Python 3.10+
- `curl`
- Variable d'environnement `OPENAI_API_KEY`

```bash
export OPENAI_API_KEY="sk-..."
mkdir -p out
```

## 1) Générer `batch_input.jsonl`

1 requête Batch = 1 entrée Easton (anti-troncage).

```bash
python scripts/build_batch_input.py --source eastons.json --out out/batch_input.jsonl
```

Test rapide (échantillon):

```bash
python scripts/build_batch_input.py --source eastons.json --out out/batch_input.jsonl --limit 50
```

## 2) Lancer la Batch API OpenAI

### 2.1 Uploader le fichier JSONL

```bash
curl https://api.openai.com/v1/files \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F purpose="batch" \
  -F file="@out/batch_input.jsonl"
```

Noter l'`id` du fichier, par ex. `file-abc123`.

### 2.2 Créer le job batch

```bash
curl https://api.openai.com/v1/batches \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input_file_id": "file-abc123",
    "endpoint": "/v1/chat/completions",
    "completion_window": "24h"
  }'
```

Noter le `batch_id`.

### 2.3 Suivre le statut

```bash
curl https://api.openai.com/v1/batches/$BATCH_ID \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

Quand `status=completed`, récupérer `output_file_id`.

### 2.4 Télécharger les résultats

```bash
curl https://api.openai.com/v1/files/$OUTPUT_FILE_ID/content \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -o out/results.jsonl
```

## 3) QA -> `qa_report.csv`

Vérifications par entrée:
- JSON invalide / champs manquants
- soupçon de troncage (ratio longueur FR/source)
- résidus `A.V.`, `R.V.`, `Authorized Version`, `Revised Version`
- présence interdite de `Dieu` (majuscule) ou `l’Éternel`

```bash
python scripts/qa_results.py --source eastons.json --results out/results.jsonl --out out/qa_report.csv
```

## 4) Générer `repair_batch.jsonl` (échecs uniquement)

```bash
python scripts/build_repair_batch.py --source eastons.json --qa out/qa_report.csv --out out/repair_batch.jsonl
```

## 5) Relancer la réparation (Batch API)

Même procédure que l'étape 2, avec `out/repair_batch.jsonl` en entrée.

Télécharger ensuite:

```bash
curl https://api.openai.com/v1/files/$REPAIR_OUTPUT_FILE_ID/content \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -o out/repair_results.jsonl
```

## 6) Merge final -> `eastons_fr.json`

```bash
python scripts/merge_results.py \
  --source eastons.json \
  --batch-results out/results.jsonl \
  --repair-results out/repair_results.jsonl \
  --out eastons_fr.json \
  --out-proper proper_nouns_unknown.json
```

## Troubleshooting

- **`invalid_json` dans QA**: augmenter la précision des prompts si besoin, puis passer par `build_repair_batch.py`.
- **Trop de `suspected_truncation`**: vérifier que le modèle choisi est adapté, que 1 entrée = 1 requête est conservé, et relancer en mode repair.
- **`missing_or_empty_response`**: vérifier les erreurs batch (`error_file_id`) via l'API batches.
- **Merge échoue avec `Missing valid translation`**: il manque des IDs valides dans `results.jsonl` + `repair_results.jsonl`; relancer une batch repair ciblée.
- **Caractères accentués**: tous les scripts lisent/écrivent en UTF-8.

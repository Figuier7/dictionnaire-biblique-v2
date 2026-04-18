# Pipeline Smith

Ce flux prepare la traduction francaise de `Smith.jsonl` puis son integration dans l'interface biblique V2.

## 1. Normaliser la source

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\prepare_smith_source.ps1
```

Sortie:

- `uploads/dictionnaires/smith/smith.json`

Le fichier produit est un tableau JSON UTF-8 avec BOM au format:

```json
[
  {
    "mot": "Aaron",
    "definition": "..."
  }
]
```

## 2. Generer le workspace de traduction locale

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\prepare_smith_translation_workspace.ps1
```

Sorties principales:

- `work/codex_local_smith/manifests/chunk_manifest.json`
- `work/codex_local_smith/source_chunks/*.source.json`

## 3. Traduire et fusionner

Utiliser les scripts du dossier `scripts/codex_local/` avec les chemins Smith:

- source: `uploads/dictionnaires/smith/smith.json`
- manifest: `work/codex_local_smith/manifests/chunk_manifest.json`
- translated dir: `work/codex_local_smith/translated_chunks`
- repair manifest: `work/codex_local_smith/manifests/repair_manifest.json`
- repair translated dir: `work/codex_local_smith/repair/translated_chunks`
- sortie finale: `uploads/dictionnaires/smith/smith.fr.json`

## 4. Construire les artefacts d'interface

Quand `uploads/dictionnaires/smith/smith.fr.json` existe:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_enriched_dictionary_entries.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_concepts_and_manifest.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_search_artifacts.ps1
```

Effet attendu:

- generation de `uploads/dictionnaires/smith/smith.entries.json`
- rattachement automatique de Smith aux concepts existants quand la correspondance est unique
- creation de concepts Smith autonomes sinon
- exposition de Smith dans `source-manifest.json` pour l'interface Bible V2

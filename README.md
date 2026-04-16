# dictionnaire-biblique

Dictionnaires bibliques pour le site alombredufiguier.org.

## Traduction Easton

Le depot contient une source unique `eastons.json` et des regles strictes dans `AGENTS.md`.

Deux modes doivent etre distingues explicitement :

- `Mode batch/API` : workflow base sur l'API OpenAI et des fichiers JSONL.
- `Mode Codex App local` : workflow 100% local, sans API, avec segmentation, validation et fusion locales.

Documentation :

- `docs/TRANSLATION_MODES.md` : vue d'ensemble et structure cible.
- `docs/TRANSLATION_PIPELINE.md` : mode batch/API existant.
- `docs/CODEX_APP_LOCAL_MODE.md` : mode local cible, sans API.

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

EASTON_FR_SOURCE = ROOT / "work" / "codex_local_global_batch_20260307_run01" / "eastons_fr_final.json"
EASTON_EN_SOURCE = ROOT / "uploads" / "dictionnaires" / "easton" / "eastons.json"
BYM_SOURCE = ROOT / "uploads" / "dictionnaires" / "bym" / "lexique-bym.json"
GLOSSARY_SOURCE = ROOT / "glossaire-bym-equivalences.json"

EASTON_OUT = ROOT / "uploads" / "dictionnaires" / "easton" / "easton.entries.json"
EASTON_AUDIT_OUT = ROOT / "uploads" / "dictionnaires" / "easton" / "easton.mot-restore-audit.json"
BYM_OUT = ROOT / "uploads" / "dictionnaires" / "bym" / "bym-lexicon.entries.json"
BYM_AUDIT_OUT = ROOT / "uploads" / "dictionnaires" / "bym" / "bym-lexicon.mot-restore-audit.json"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip()


def lookup_key(value: str) -> str:
    return normalize_text(value).casefold()


def split_french_names(value: str) -> list[str]:
    parts = re.split(r"[\n,]+", value)
    return [normalize_text(part) for part in parts if normalize_text(part)]


def slugify(value: str) -> str:
    folded = unicodedata.normalize("NFD", value)
    folded = "".join(ch for ch in folded if unicodedata.category(ch) != "Mn")
    lowered = folded.casefold()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return cleaned or "entry"


def first_letter(value: str) -> str:
    folded = unicodedata.normalize("NFD", value)
    folded = "".join(ch for ch in folded if unicodedata.category(ch) != "Mn")
    for char in folded:
        if char.isalnum():
            return char.upper()
    return "#"


def render_mode_from_length(length: int) -> str:
    if length <= 420:
        return "direct"
    if length <= 1800:
        return "preview_expand"
    return "deep_read"


@dataclass(frozen=True)
class GlossaryRow:
    nom_restaure: str
    noms_francais: tuple[str, ...]


class GlossaryIndex:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self.restore_by_key: dict[str, GlossaryRow] = {}
        self.french_to_rows: dict[str, list[GlossaryRow]] = {}
        for row in rows:
            restore = normalize_text(row["nom_restaure"])
            french_names = tuple(split_french_names(row["noms_francais"]))
            glossary_row = GlossaryRow(nom_restaure=restore, noms_francais=french_names)
            self.restore_by_key[lookup_key(restore)] = glossary_row
            for french_name in french_names:
                self.french_to_rows.setdefault(lookup_key(french_name), []).append(glossary_row)

    def resolve_restore(self, value: str) -> tuple[str, str, list[str]]:
        key = lookup_key(value)
        restore_row = self.restore_by_key.get(key)
        if restore_row:
            return restore_row.nom_restaure, "restore_exact", [restore_row.nom_restaure]

        french_rows = self.french_to_rows.get(key, [])
        candidates = sorted({row.nom_restaure for row in french_rows})
        if len(candidates) == 1:
            return candidates[0], "fr_exact_unique", candidates
        if len(candidates) > 1:
            return "", "none", candidates
        return "", "none", []

    def unique_french_label_for_restore(self, restore: str) -> str:
        row = self.restore_by_key.get(lookup_key(restore))
        if not row:
            return ""
        if len(row.noms_francais) == 1:
            return row.noms_francais[0]
        return ""


def build_easton_entries(glossary: GlossaryIndex) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    easton_fr = load_json(EASTON_FR_SOURCE)
    easton_en = load_json(EASTON_EN_SOURCE)
    if len(easton_fr) != len(easton_en):
        raise ValueError("Easton FR/EN counts do not align.")

    entries: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []

    for idx, (fr_entry, en_entry) in enumerate(zip(easton_fr, easton_en), start=1):
        mot = normalize_text(fr_entry["mot"])
        definition = fr_entry["definition"]
        source_title_en = normalize_text(en_entry["mot"])
        mot_restore, mot_restore_method, restore_candidates = glossary.resolve_restore(mot)

        quality_flags: list[str] = []
        status = "ready"

        if lookup_key(mot) == lookup_key(source_title_en):
            quality_flags.append("title_source_english")

        if mot_restore:
            pass
        elif restore_candidates:
            quality_flags.append("restore_ambiguous")
            status = "review"
        else:
            quality_flags.append("restore_missing_authority")

        aliases: list[str] = []
        if source_title_en and lookup_key(source_title_en) != lookup_key(mot):
            aliases.append(source_title_en)
        if mot_restore and lookup_key(mot_restore) != lookup_key(mot):
            aliases.append(mot_restore)

        entry = {
            "id": f"easton-{idx:06d}",
            "dictionary": "easton",
            "source_order": idx,
            "mot": mot,
            "source_title_en": source_title_en,
            "label_fr": mot,
            "mot_restore": mot_restore,
            "mot_restore_method": mot_restore_method,
            "aliases": aliases,
            "slug": f"easton-{slugify(mot)}",
            "letter": first_letter(mot),
            "definition": definition,
            "definition_length": len(definition),
            "display_role": "main_definition",
            "render_mode_default": render_mode_from_length(len(definition)),
            "category_hint": "",
            "concept_hint": "",
            "status": status,
            "quality_flags": quality_flags,
        }
        entries.append(entry)

        if quality_flags:
            audit.append(
                {
                    "entry_id": entry["id"],
                    "mot": mot,
                    "dictionary": "easton",
                    "reason": quality_flags[0],
                    "candidate_restores": restore_candidates,
                }
            )

    return entries, audit


def build_bym_entries(glossary: GlossaryIndex) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    bym_entries = load_json(BYM_SOURCE)

    entries: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []

    for idx, source_entry in enumerate(bym_entries, start=1):
        mot = normalize_text(source_entry["mot"])
        definition = source_entry["definition"]
        mot_restore, mot_restore_method, restore_candidates = glossary.resolve_restore(mot)

        label_fr = mot
        quality_flags: list[str] = []
        status = "ready"

        if mot_restore_method == "restore_exact":
            french_label = glossary.unique_french_label_for_restore(mot_restore)
            if french_label and lookup_key(french_label) != lookup_key(mot):
                label_fr = french_label
                quality_flags.append("label_fr_from_glossary")

        if mot_restore:
            pass
        elif restore_candidates:
            quality_flags.append("restore_ambiguous")
            status = "review"
        else:
            quality_flags.append("restore_missing_authority")

        aliases: list[str] = []
        if lookup_key(label_fr) != lookup_key(mot):
            aliases.append(label_fr)
        if mot_restore and lookup_key(mot_restore) != lookup_key(mot):
            aliases.append(mot_restore)

        entry = {
            "id": f"bym-{idx:06d}",
            "dictionary": "bym_lexicon",
            "source_order": idx,
            "mot": mot,
            "source_title_en": "",
            "label_fr": label_fr,
            "mot_restore": mot_restore,
            "mot_restore_method": mot_restore_method,
            "aliases": aliases,
            "slug": f"bym-{slugify(mot)}",
            "letter": first_letter(label_fr or mot),
            "definition": definition,
            "definition_length": len(definition),
            "display_role": "quick_gloss",
            "render_mode_default": render_mode_from_length(len(definition)),
            "category_hint": "",
            "concept_hint": "",
            "status": status,
            "quality_flags": quality_flags,
        }
        entries.append(entry)

        if quality_flags:
            audit.append(
                {
                    "entry_id": entry["id"],
                    "mot": mot,
                    "dictionary": "bym_lexicon",
                    "reason": quality_flags[0],
                    "candidate_restores": restore_candidates,
                }
            )

    return entries, audit


def main() -> None:
    glossary = GlossaryIndex(load_json(GLOSSARY_SOURCE))

    easton_entries, easton_audit = build_easton_entries(glossary)
    write_json(EASTON_OUT, easton_entries)
    write_json(EASTON_AUDIT_OUT, easton_audit)

    bym_entries, bym_audit = build_bym_entries(glossary)
    write_json(BYM_OUT, bym_entries)
    write_json(BYM_AUDIT_OUT, bym_audit)

    print(f"Easton entries written: {EASTON_OUT}")
    print(f"Easton audit written: {EASTON_AUDIT_OUT}")
    print(f"BYM entries written: {BYM_OUT}")
    print(f"BYM audit written: {BYM_AUDIT_OUT}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Shared helpers for the dedicated ISBE OpenAI batch pipeline.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ISBE_JSON = ROOT / "isbe.json"
WORK_DIR = ROOT / "work" / "codex_local_isbe"
SOURCE_DIR = WORK_DIR / "source_chunks"
TRANSLATED_DIR = WORK_DIR / "translated_chunks"
MANIFEST_PATH = WORK_DIR / "manifests" / "chunk_manifest.json"
V1_MANIFEST_PATH = WORK_DIR / "manifests" / "v1_chunks_manifest.json"
PRIORITY_CIRCLES_PATH = WORK_DIR / "isbe-priority-circles.json"
REQUESTS_DIR = WORK_DIR / "batch" / "requests"
RESULTS_DIR = WORK_DIR / "batch" / "results"
REPORTS_DIR = WORK_DIR / "batch" / "reports"
RAW_ERRORS_DIR = WORK_DIR / "batch" / "raw_errors"
UPLOADS_ISBE_DIR = ROOT / "uploads" / "dictionnaires" / "isbe"
MERGED_PATH = UPLOADS_ISBE_DIR / "isbe.fr.json"

DEFAULT_MODEL = "gpt-5-mini"
DEFAULT_BUDGET = 40_000
DEFAULT_SUBBATCH_SIZE = 50

CHUNK_ID_RE = re.compile(r"^chunk_(\d{4})$")
SOURCE_CHUNK_RE = re.compile(r"^chunk_(\d{4})\.source\.json$")
TRANSLATED_CHUNK_RE = re.compile(r"^chunk_(\d{4})\.fr\.json$")

ISBE_SYSTEM_INSTRUCTIONS = (
    "Tu traduis des chunks de l'encyclopedie biblique ISBE "
    "(International Standard Bible Encyclopedia) vers le francais "
    "pour un pipeline JSON strict.\n"
    "Retourner uniquement un objet JSON exact sous la forme "
    "{\"chunk_id\":\"...\",\"entries\":[...]}.\n"
    "Contraintes absolues:\n"
    "- chunk_id identique a la source.\n"
    "- entries doit garder exactement le meme nombre d'elements, le meme ordre et les memes ids.\n"
    "- Chaque element doit etre strictement {\"id\":0,\"mot\":\"...\",\"definition\":\"...\"}.\n"
    "- mot est un invariant absolu: ne jamais le modifier.\n"
    "- Traduire integralement definition, sans troncage, sans resume, sans ajout.\n"
    "- L'ISBE est une encyclopedie savante: conserver le ton encyclopedique, les sections numerotees, "
    "les signatures d'auteurs, les prononciations (ar'-un, a-bad'-on, etc.).\n"
    "- Conserver toutes les translitterations hebraiques et grecques entre parentheses.\n"
    "- Renvois internes: traduire le mot introducteur (See -> Voir, compare -> comparer) "
    "mais JAMAIS la cible du renvoi (ALEPH, APOLLYON, PRIEST, III, etc.) qui doit rester en forme source.\n"
    "- Conserver inchanges comme sigles savants: Heb., Gr., LXX, cf., comp., ibid., q.v.\n"
    "- Franciser: i.e. -> c.-a-d.; e.g. -> par ex.; viz. -> a savoir; No. -> no.\n"
    "- References bibliques en formes courtes francaises stables: Gen., Ex., Lev., Nomb., Deut., Jos., "
    "Jug., 1 Sam., 2 Sam., 1 Rois, 2 Rois, 1 Chr., 2 Chr., Esdr., Neh., Esth., Job, Ps., Prov., "
    "Eccl., Cant., Esa., Jer., Lam., Ez., Dan., Matt., Marc, Luc, Jean, Actes, Rom., 1 Cor., 2 Cor., "
    "Gal., Eph., Phil., Col., 1 Thess., 2 Thess., 1 Tim., 2 Tim., Tite, Philem., Heb., Jacq., "
    "1 Pi., 2 Pi., 1 Jean, 2 Jean, 3 Jean, Jude, Apoc.\n"
    "- Authorized Version -> Version autorisee; Revised Version -> Version revisee; "
    "in our version -> dans notre version; margin/in the margin -> marge/en marge.\n"
    "- American Standard Revised Version / A.S.V. -> Version Standard Americaine Revisee.\n"
    "- Si un mot ou groupe de mots anglais est conserve parce qu'il est l'objet meme d'une remarque "
    "editoriale ou textuelle, conserver uniquement cette forme anglaise citee, avec sa casse source, "
    "entre guillemets si elle est citee dans la source, et traduire entierement la phrase autour.\n"
    "- God -> Elohim; LORD/Jehovah/Yahweh/the LORD -> YHWH; the Lord -> le Seigneur; "
    "Jesus -> Yehoshoua (Jesus) si necessaire; Christ/Messiah -> Mashiah (Christ) ou Mashiah; "
    "Holy Spirit/Holy Ghost -> Saint-Esprit.\n"
    "- B.C. -> av. J.-C.; A.D. -> apr. J.-C.\n"
    "- Ne laisser aucun anglais residuel non cite, sauf sigles savants ou citation anglaise "
    "explicitement objet de la remarque.\n"
)


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any:
    raw = path.read_text(encoding="utf-8-sig")
    return json.loads(raw)


def write_json(path: Path, data: Any, *, bom: bool = True, indent: int = 2) -> None:
    ensure_parent_dir(path)
    encoding = "utf-8-sig" if bom else "utf-8"
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=indent) + "\n",
        encoding=encoding,
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]], *, bom: bool = False) -> None:
    ensure_parent_dir(path)
    encoding = "utf-8-sig" if bom else "utf-8"
    with path.open("w", encoding=encoding, newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig") as handle:
        for index, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {index} in {path}: {exc}") from exc
    return rows


def chunk_id_from_number(number: int) -> str:
    return f"chunk_{number:04d}"


def parse_chunk_number(chunk_id: str) -> int:
    match = CHUNK_ID_RE.match(chunk_id)
    if not match:
        raise ValueError(f"Invalid chunk id: {chunk_id}")
    return int(match.group(1))


def source_chunk_path(chunk_id: str, source_dir: Path = SOURCE_DIR) -> Path:
    return source_dir / f"{chunk_id}.source.json"


def translated_chunk_path(chunk_id: str, translated_dir: Path = TRANSLATED_DIR) -> Path:
    return translated_dir / f"{chunk_id}.fr.json"


def load_chunk_manifest(path: Path = MANIFEST_PATH) -> list[dict[str, Any]]:
    data = read_json(path)
    if not isinstance(data, list):
        raise ValueError(f"Expected a list in {path}")
    return data


def load_v1_chunks(path: Path = V1_MANIFEST_PATH) -> list[dict[str, Any]]:
    data = read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("chunks"), list):
        raise ValueError(f"Expected an object with chunks[] in {path}")
    return data["chunks"]


def load_source_entries(path: Path = ISBE_JSON) -> list[dict[str, Any]]:
    entries = read_json(path)
    if not isinstance(entries, list):
        raise ValueError(f"Expected a list in {path}")
    return [
        {"id": index, "mot": entry["mot"], "definition": entry["definition"]}
        for index, entry in enumerate(entries)
    ]


def build_request_payload(chunk: dict[str, Any], source_entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "task": "Traduire ce chunk ISBE en francais selon les regles du pipeline.",
        "chunk_id": chunk["chunk_id"],
        "chunk_mode": chunk["chunk_mode"],
        "entry_count": chunk["entry_count"],
        "output_contract": {
            "chunk_id": chunk["chunk_id"],
            "entries": [{"id": "int", "mot": "string (invariant)", "definition": "string (traduit)"}],
        },
        "entries": source_entries,
    }


def build_batch_request(
    chunk: dict[str, Any],
    source_entries: list[dict[str, Any]],
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    return {
        "custom_id": chunk["chunk_id"],
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": ISBE_SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": json.dumps(build_request_payload(chunk, source_entries), ensure_ascii=False)},
            ],
        },
    }


def validate_chunk_structure(
    source_entries: list[dict[str, Any]],
    translated_entries: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []

    if not isinstance(translated_entries, list):
        issues.append({"code": "translated_chunk_not_array", "message": "Translated chunk is not a JSON array."})
        return normalized, issues

    if len(translated_entries) != len(source_entries):
        issues.append(
            {
                "code": "chunk_entry_count_mismatch",
                "message": f"Expected {len(source_entries)} entries, got {len(translated_entries)}.",
            }
        )
        return normalized, issues

    for index, (source_entry, translated_entry) in enumerate(zip(source_entries, translated_entries)):
        if not isinstance(translated_entry, dict):
            issues.append(
                {
                    "code": "translated_entry_not_object",
                    "entry_id": source_entry["id"],
                    "message": f"Entry {index} is not an object.",
                }
            )
            continue

        missing_fields = [
            field
            for field in ("id", "mot", "definition")
            if field not in translated_entry
        ]
        if missing_fields:
            issues.append(
                {
                    "code": "translated_entry_missing_fields",
                    "entry_id": source_entry["id"],
                    "message": f"Entry {index} is missing fields: {', '.join(missing_fields)}.",
                }
            )
            continue

        if translated_entry["id"] != source_entry["id"]:
            issues.append(
                {
                    "code": "translated_id_mismatch",
                    "entry_id": source_entry["id"],
                    "message": f"Expected id {source_entry['id']}, got {translated_entry['id']}.",
                }
            )
            continue

        if translated_entry["mot"] != source_entry["mot"]:
            issues.append(
                {
                    "code": "translated_mot_mismatch",
                    "entry_id": source_entry["id"],
                    "message": f"Expected mot {source_entry['mot']!r}, got {translated_entry['mot']!r}.",
                }
            )
            continue

        if not isinstance(translated_entry["definition"], str):
            issues.append(
                {
                    "code": "translated_definition_not_string",
                    "entry_id": source_entry["id"],
                    "message": f"Definition for id {source_entry['id']} is not a string.",
                }
            )
            continue

        normalized.append(
            {
                "id": translated_entry["id"],
                "mot": translated_entry["mot"],
                "definition": translated_entry["definition"],
            }
        )

    return normalized, issues


def qa_chunk_translation(
    chunk_id: str,
    source_entries: list[dict[str, Any]],
    translated_entries: Any,
    *,
    min_ratio_check_chars: int = 80,
    min_ratio_hard: float = 0.35,
    min_ratio_warn: float = 0.5,
    max_ratio_warn: float = 2.2,
    max_ratio_hard: float = 3.0,
) -> dict[str, Any]:
    normalized, structural_issues = validate_chunk_structure(source_entries, translated_entries)
    entry_reports: list[dict[str, Any]] = []
    warnings = 0
    errors = len(structural_issues)

    if structural_issues:
        status = "error"
    else:
        status = "ok"
        for source_entry, translated_entry in zip(source_entries, normalized):
            source_chars = len(source_entry["definition"])
            translated_text = translated_entry["definition"]
            translated_chars = len(translated_text)
            entry_issues: list[dict[str, Any]] = []
            entry_status = "ok"

            if source_chars > 0 and not translated_text.strip():
                entry_issues.append({"code": "empty_translated_definition", "message": "Translated definition is empty."})
                entry_status = "error"
                errors += 1

            ratio: float | None
            if source_chars > 0:
                ratio = translated_chars / source_chars
                if source_chars >= min_ratio_check_chars:
                    if ratio < min_ratio_hard:
                        entry_issues.append(
                            {
                                "code": "translation_ratio_too_small",
                                "message": f"Ratio {ratio:.2f} is below hard threshold {min_ratio_hard:.2f}.",
                            }
                        )
                        entry_status = "error"
                        errors += 1
                    elif ratio < min_ratio_warn:
                        entry_issues.append(
                            {
                                "code": "translation_ratio_low_warning",
                                "message": f"Ratio {ratio:.2f} is below warning threshold {min_ratio_warn:.2f}.",
                            }
                        )
                        if entry_status == "ok":
                            entry_status = "warning"
                        warnings += 1

                    if ratio > max_ratio_hard:
                        entry_issues.append(
                            {
                                "code": "translation_ratio_too_large",
                                "message": f"Ratio {ratio:.2f} is above hard threshold {max_ratio_hard:.2f}.",
                            }
                        )
                        entry_status = "error"
                        errors += 1
                    elif ratio > max_ratio_warn:
                        entry_issues.append(
                            {
                                "code": "translation_ratio_high_warning",
                                "message": f"Ratio {ratio:.2f} is above warning threshold {max_ratio_warn:.2f}.",
                            }
                        )
                        if entry_status == "ok":
                            entry_status = "warning"
                        warnings += 1
            else:
                ratio = 1.0 if translated_chars == 0 else None
                if translated_chars > 0:
                    entry_issues.append(
                        {
                            "code": "unexpected_translation_for_empty_source",
                            "message": "Source definition is empty but translated definition is not.",
                        }
                    )
                    if entry_status == "ok":
                        entry_status = "warning"
                    warnings += 1

            entry_reports.append(
                {
                    "entry_id": source_entry["id"],
                    "mot_source": source_entry["mot"],
                    "mot_target": translated_entry["mot"],
                    "source_chars": source_chars,
                    "translated_chars": translated_chars,
                    "ratio": ratio,
                    "status": entry_status,
                    "issues": entry_issues,
                }
            )

        if errors:
            status = "error"
        elif warnings:
            status = "warning"

    return {
        "chunk_id": chunk_id,
        "status": status,
        "summary": {
            "source_entry_count": len(source_entries),
            "translated_entry_count": len(translated_entries) if isinstance(translated_entries, list) else 0,
            "error_count": errors,
            "warning_count": warnings,
        },
        "chunk_issues": structural_issues,
        "entries": entry_reports,
    }


def extract_result_text(result_line: dict[str, Any]) -> tuple[str | None, int | None, str]:
    response = result_line.get("response") if isinstance(result_line, dict) else None
    error = result_line.get("error") if isinstance(result_line, dict) else None
    status_code = response.get("status_code") if isinstance(response, dict) else None
    error_message = ""

    if isinstance(error, dict):
        error_message = str(error.get("message") or json.dumps(error, ensure_ascii=False))

    body = response.get("body") if isinstance(response, dict) else None
    if not isinstance(body, dict):
        return None, status_code, error_message

    choices = body.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content, status_code, error_message
            if isinstance(content, list):
                parts: list[str] = []
                for part in content:
                    if isinstance(part, str):
                        parts.append(part)
                    elif isinstance(part, dict) and isinstance(part.get("text"), str):
                        parts.append(part["text"])
                return "".join(parts), status_code, error_message

    output = body.get("output")
    if isinstance(output, list):
        parts = []
        for item in output:
            if not isinstance(item, dict):
                continue
            for part in item.get("content", []):
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    parts.append(part["text"])
        if parts:
            return "".join(parts), status_code, error_message

    return None, status_code, error_message


def parse_batch_envelope(raw_text: str, expected_chunk_id: str) -> tuple[list[dict[str, Any]], str]:
    parsed = json.loads(raw_text)
    wrapper_type = "unknown"

    if isinstance(parsed, list):
        wrapper_type = "direct_array"
        entries = parsed
    elif isinstance(parsed, dict):
        entries = parsed.get("entries")
        if entries is None:
            for key in ("data", "result", "translations"):
                candidate = parsed.get(key)
                if isinstance(candidate, list):
                    entries = candidate
                    wrapper_type = key
                    break
        else:
            wrapper_type = "entries"

        if not isinstance(entries, list):
            raise ValueError("Batch response does not contain an entries array.")

        response_chunk_id = parsed.get("chunk_id")
        if response_chunk_id and response_chunk_id != expected_chunk_id:
            raise ValueError(
                f"Response chunk_id {response_chunk_id!r} does not match expected {expected_chunk_id!r}."
            )
    else:
        raise ValueError("Batch response is neither an object nor an array.")

    return entries, wrapper_type


def load_priority_circle_map(path: Path = PRIORITY_CIRCLES_PATH) -> dict[int, str]:
    if not path.exists():
        return {}
    rows = read_json(path)
    if not isinstance(rows, list):
        return {}
    result: dict[int, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        entry_id = row.get("isbe_id")
        circle = row.get("circle")
        if isinstance(entry_id, int) and isinstance(circle, str):
            result[entry_id] = circle
    return result


def transpose_c4_definition(definition: str) -> str:
    text = definition.strip()
    if not text:
        return ""

    substitutions = [
        (r"^See also\b", "Voir aussi"),
        (r"^see also\b", "voir aussi"),
        (r"^See under\b", "Voir sous"),
        (r"^see under\b", "voir sous"),
        (r"^Same as\b", "Identique a"),
        (r"^compare\b", "comparer"),
        (r"^Compare\b", "Comparer"),
        (r"^See\b", "Voir"),
        (r"^see\b", "voir"),
    ]
    for pattern, replacement in substitutions:
        text = re.sub(pattern, replacement, text)
    return re.sub(r"\s{2,}", " ", text).strip()


def collect_inventory(
    manifest_chunks: list[dict[str, Any]],
    *,
    source_dir: Path = SOURCE_DIR,
    translated_dir: Path = TRANSLATED_DIR,
    v1_chunks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    valid_chunk_ids: list[str] = []
    invalid_chunks: list[dict[str, Any]] = []
    missing_chunk_ids: list[str] = []
    translated_entry_count = 0
    translated_source_chars = 0

    manifest_by_id = {chunk["chunk_id"]: chunk for chunk in manifest_chunks}

    for chunk in manifest_chunks:
        chunk_id = chunk["chunk_id"]
        source_entries = read_json(source_chunk_path(chunk_id, source_dir))
        translated_path = translated_chunk_path(chunk_id, translated_dir)

        if not translated_path.exists():
            missing_chunk_ids.append(chunk_id)
            continue

        try:
            translated_entries = read_json(translated_path)
        except Exception as exc:  # noqa: BLE001
            invalid_chunks.append(
                {"chunk_id": chunk_id, "reason": "invalid_json", "message": str(exc), "path": str(translated_path)}
            )
            continue

        _, issues = validate_chunk_structure(source_entries, translated_entries)
        if issues:
            invalid_chunks.append(
                {
                    "chunk_id": chunk_id,
                    "reason": issues[0]["code"],
                    "message": issues[0]["message"],
                    "path": str(translated_path),
                }
            )
            continue

        valid_chunk_ids.append(chunk_id)
        translated_entry_count += len(source_entries)
        translated_source_chars += sum(len(entry.get("definition", "")) for entry in source_entries)

    known_names = {translated_chunk_path(chunk["chunk_id"], translated_dir).name for chunk in manifest_chunks}
    extraneous_files = sorted(
        str(path)
        for path in translated_dir.iterdir()
        if path.is_file() and path.name not in known_names and path.name != "c4_redirections.fr.json"
    ) if translated_dir.exists() else []

    valid_set = set(valid_chunk_ids)
    invalid_set = {item["chunk_id"] for item in invalid_chunks}
    missing_set = set(missing_chunk_ids)

    summary: dict[str, Any] = {
        "source_chunk_count": len(manifest_chunks),
        "valid_translated_chunk_count": len(valid_chunk_ids),
        "invalid_translated_chunk_count": len(invalid_chunks),
        "missing_chunk_count": len(missing_chunk_ids),
        "remaining_chunk_count": len(manifest_chunks) - len(valid_chunk_ids),
        "translated_entry_count": translated_entry_count,
        "translated_source_chars": translated_source_chars,
        "translated_source_chars_mb": round(translated_source_chars / (1024 * 1024), 2),
        "first_missing_chunks": sorted(missing_chunk_ids, key=parse_chunk_number)[:20],
        "invalid_chunks": invalid_chunks,
        "extraneous_files": extraneous_files,
    }

    if v1_chunks is not None:
        v1_ids = [chunk["chunk_id"] for chunk in v1_chunks]
        v1_set = set(v1_ids)
        v1_remaining = [chunk_id for chunk_id in v1_ids if chunk_id not in valid_set]
        summary["v1_chunk_count"] = len(v1_ids)
        summary["v1_valid_chunk_count"] = len(v1_ids) - len(v1_remaining)
        summary["v1_remaining_chunk_count"] = len(v1_remaining)
        summary["v1_first_remaining_chunks"] = v1_remaining[:20]
        summary["phase2_remaining_chunk_count"] = len(
            [chunk_id for chunk_id in manifest_by_id if chunk_id not in v1_set and chunk_id not in valid_set]
        )
        summary["invalid_chunk_ids"] = sorted(invalid_set, key=parse_chunk_number)
        summary["missing_chunk_ids"] = sorted(missing_set, key=parse_chunk_number)

    return {
        "summary": summary,
        "valid_chunk_ids": sorted(valid_chunk_ids, key=parse_chunk_number),
        "invalid_chunks": invalid_chunks,
        "missing_chunk_ids": sorted(missing_chunk_ids, key=parse_chunk_number),
    }

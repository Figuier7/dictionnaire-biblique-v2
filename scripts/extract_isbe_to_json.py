#!/usr/bin/env python3
"""
Extract ISBE (International Standard Bible Encyclopedia) from Sword zLD
binary module into a JSON file matching the eastons.json format:

    [{"mot": "ENTRY_NAME", "definition": "..."}, ...]

Sword zLD format (compressed lexicon/dictionary):
  - isbe.idx : fixed 8-byte records  → (offset_into_dat:u32_le, length:u32_le)
  - isbe.dat : entry keys with block/entry indices
  - isbe.zdx : fixed 8-byte records  → (offset_into_zdt:u32_le, block_size:u32_le)
  - isbe.zdt : ZIP-compressed content blocks (one block = multiple entries)

Usage:
    python extract_isbe_to_json.py [--module-dir DIR] [--out PATH] [--strip-markup]

Requirements: Python 3.8+ (standard library only, no pip install needed).
"""

from __future__ import annotations

import argparse
import html
import json
import re
import struct
import zlib
from pathlib import Path


# ---------------------------------------------------------------------------
# 1. Low-level Sword zLD readers
# ---------------------------------------------------------------------------

def read_idx(idx_path: Path) -> list[tuple[int, int]]:
    """Return list of (offset_into_dat, length) from the .idx file."""
    data = idx_path.read_bytes()
    count = len(data) // 8
    entries = []
    for i in range(count):
        offset, length = struct.unpack_from("<II", data, i * 8)
        entries.append((offset, length))
    return entries


def read_dat_entries(dat_path: Path, idx_entries: list[tuple[int, int]]) -> list[dict]:
    """
    Parse each idx record from the .dat file.
    Each dat record contains:
      - entry name (terminated by \\r\\n)
      - 4 bytes: block number (u32 LE) — which zdx/zdt block
      - 4 bytes: entry index within block (u32 LE)
    """
    dat = dat_path.read_bytes()
    result = []
    for offset, length in idx_entries:
        if length == 0:
            continue
        chunk = dat[offset:offset + length]
        # Entry name terminated by \r\n, followed by 8 bytes of metadata
        name_end = chunk.find(b"\r\n")
        if name_end < 0:
            continue

        name = chunk[:name_end].decode("utf-8", errors="replace").strip()
        if not name:
            continue

        # After \r\n: block_num (u32 LE) + entry_idx (u32 LE)
        meta_start = name_end + 2  # skip \r\n
        if meta_start + 8 <= len(chunk):
            block_num = struct.unpack_from("<I", chunk, meta_start)[0]
            entry_idx = struct.unpack_from("<I", chunk, meta_start + 4)[0]
        else:
            block_num = 0
            entry_idx = 0

        result.append({
            "name": name,
            "block": block_num,
            "entry_idx": entry_idx,
        })
    return result


def read_zdx(zdx_path: Path) -> list[tuple[int, int]]:
    """Return list of (offset_into_zdt, compressed_size) from .zdx."""
    data = zdx_path.read_bytes()
    count = len(data) // 8
    blocks = []
    for i in range(count):
        offset, size = struct.unpack_from("<II", data, i * 8)
        blocks.append((offset, size))
    return blocks


def decompress_block(zdt_path: Path, offset: int, size: int) -> bytes:
    """Read and decompress a single block from .zdt (ZIP/zlib compressed)."""
    with open(zdt_path, "rb") as f:
        f.seek(offset)
        compressed = f.read(size)

    # Sword uses raw zlib (sometimes with a 4-byte entry-count header per block)
    # Try multiple decompression strategies
    for attempt in [
        lambda: zlib.decompress(compressed),
        lambda: zlib.decompress(compressed, -15),        # raw deflate
        lambda: zlib.decompress(compressed, 15),          # zlib header
        lambda: zlib.decompress(compressed, 15 + 32),     # auto gzip/zlib
        lambda: zlib.decompress(compressed[4:]),           # skip 4-byte header
        lambda: zlib.decompress(compressed[4:], -15),
    ]:
        try:
            return attempt()
        except zlib.error:
            continue

    raise ValueError(f"Cannot decompress block at offset {offset}, size {size}")


def split_block_entries(raw: bytes) -> list[str]:
    """
    Split a decompressed Sword zLD block into individual entry texts.

    Block format:
      - 4 bytes: entry_count (u32 LE)
      - entry_count * 8 bytes: pairs of (offset_in_block: u32, size: u32)
      - then the actual entry data at those offsets
    """
    if len(raw) < 4:
        return [raw.decode("utf-8", errors="replace")]

    entry_count = struct.unpack_from("<I", raw, 0)[0]
    if entry_count == 0 or entry_count > 500:
        # Doesn't look like a valid header, treat as single entry
        return [raw.decode("utf-8", errors="replace")]

    header_size = 4 + entry_count * 8
    if header_size > len(raw):
        return [raw.decode("utf-8", errors="replace")]

    entries = []
    for i in range(entry_count):
        eoff, esz = struct.unpack_from("<II", raw, 4 + i * 8)
        if eoff + esz <= len(raw):
            text = raw[eoff:eoff + esz].decode("utf-8", errors="replace")
        elif eoff < len(raw):
            text = raw[eoff:].decode("utf-8", errors="replace")
        else:
            text = ""
        entries.append(text)

    return entries


# ---------------------------------------------------------------------------
# 2. Markup cleaning (TEI/ThML → plain text)
# ---------------------------------------------------------------------------

def strip_tei_markup(text: str) -> str:
    """Remove TEI/ThML/HTML markup, keeping readable text."""
    # Decode HTML entities
    text = html.unescape(text)

    # Convert <br/> and <p> to newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?p[^>]*>", "\n", text, flags=re.IGNORECASE)

    # Convert <scripRef> tags — keep the text content
    text = re.sub(r"<scripRef[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</scripRef>", "", text, flags=re.IGNORECASE)

    # Convert <hi rend="bold"> or <b> → keep text
    text = re.sub(r"<hi[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</hi>", "", text, flags=re.IGNORECASE)

    # Remove all remaining XML/HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Remove null bytes and clean up whitespace
    text = text.replace("\x00", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip()

    return text


# ---------------------------------------------------------------------------
# 3. Main extraction pipeline
# ---------------------------------------------------------------------------

def extract_isbe(module_dir: Path, strip_markup: bool = True) -> list[dict]:
    """Extract all ISBE entries and return as list of {mot, definition}."""
    idx_path = module_dir / "isbe.idx"
    dat_path = module_dir / "isbe.dat"
    zdx_path = module_dir / "isbe.zdx"
    zdt_path = module_dir / "isbe.zdt"

    for p in [idx_path, dat_path, zdx_path, zdt_path]:
        if not p.exists():
            raise FileNotFoundError(f"Missing file: {p}")

    print(f"Reading index from {idx_path} ...")
    idx_entries = read_idx(idx_path)
    print(f"  -> {len(idx_entries)} idx records")

    print(f"Reading entry keys from {dat_path} ...")
    dat_entries = read_dat_entries(dat_path, idx_entries)
    print(f"  -> {len(dat_entries)} named entries")

    print(f"Reading block index from {zdx_path} ...")
    zdx_blocks = read_zdx(zdx_path)
    print(f"  -> {len(zdx_blocks)} compressed blocks")

    # Decompress all blocks and split into entries
    print(f"Decompressing content from {zdt_path} ...")
    block_entries: dict[int, list[str]] = {}
    errors = 0
    for block_num, (offset, size) in enumerate(zdx_blocks):
        if size == 0:
            continue
        try:
            raw = decompress_block(zdt_path, offset, size)
            block_entries[block_num] = split_block_entries(raw)
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  [WARN] Block {block_num}: {e}")
            block_entries[block_num] = []

    if errors:
        print(f"  -> {errors} blocks with decompression errors")

    # Match each dat entry to its content
    print("Matching entries to content ...")
    results = []
    matched = 0
    for entry in dat_entries:
        name = entry["name"]
        block_num = entry["block"]
        entry_idx = entry["entry_idx"]

        definition = ""
        if block_num in block_entries:
            block_texts = block_entries[block_num]
            if entry_idx < len(block_texts):
                definition = block_texts[entry_idx]
            elif block_texts:
                # Fallback: try first entry
                definition = block_texts[0] if len(block_texts) == 1 else ""

        if strip_markup and definition:
            definition = strip_tei_markup(definition)

        if definition:
            matched += 1

        # Title-case the name for consistency with eastons.json
        display_name = name.title() if name.isupper() else name

        results.append({
            "mot": display_name,
            "definition": definition,
        })

    print(f"  -> {matched}/{len(results)} entries with content")
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract ISBE Sword module to JSON (eastons.json format)"
    )
    parser.add_argument(
        "--module-dir",
        default="ISBE/modules/lexdict/zld/isbe",
        help="Path to the directory containing isbe.idx/dat/zdx/zdt",
    )
    parser.add_argument(
        "--out",
        default="isbe.json",
        help="Output JSON file path (default: isbe.json)",
    )
    parser.add_argument(
        "--strip-markup",
        action="store_true",
        default=True,
        help="Remove TEI/ThML markup (default: True)",
    )
    parser.add_argument(
        "--keep-markup",
        action="store_true",
        default=False,
        help="Keep raw TEI/ThML markup",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    module_dir = Path(args.module_dir)
    strip = not args.keep_markup

    entries = extract_isbe(module_dir, strip_markup=strip)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Wrote {len(entries)} entries to {out_path}")
    print(f"  File size: {out_path.stat().st_size / 1024 / 1024:.1f} MB")

    # Quick stats
    with_def = sum(1 for e in entries if e["definition"])
    empty = len(entries) - with_def
    avg_len = (
        sum(len(e["definition"]) for e in entries if e["definition"]) / max(with_def, 1)
    )
    print(f"  Entries with content: {with_def}")
    print(f"  Empty entries: {empty}")
    print(f"  Avg definition length: {avg_len:.0f} chars")


if __name__ == "__main__":
    main()

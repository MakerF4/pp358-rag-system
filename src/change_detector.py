import hashlib
import json
from datetime import datetime
from pathlib import Path

from src.config import (
    METADATA_FILENAME,
    CHANGES_FILENAME,
    VERSIONS_DIR,
)


def calculate_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_version_folders(versions_dir: Path = VERSIONS_DIR) -> list[Path]:
    if not versions_dir.exists():
        return []

    return sorted(
        [
            path
            for path in versions_dir.iterdir()
            if path.is_dir() and (path / METADATA_FILENAME).exists()
        ]
    )


def get_latest_version_path(versions_dir: Path = VERSIONS_DIR) -> Path | None:
    version_folders = get_version_folders(versions_dir)

    if not version_folders:
        return None

    return version_folders[-1]


def load_metadata(version_path: Path) -> dict:
    metadata_path = version_path / METADATA_FILENAME

    return json.loads(metadata_path.read_text(encoding="utf-8"))


def load_chunks_from_version(version_path: Path) -> dict[str, dict]:
    """
    Loads chunks from saved version folder.

    Returns:
        {
            "ru:ru_chunk_0001": chunk,
            "uz:uz_chunk_0001": chunk,
            ...
        }
    """
    metadata = load_metadata(version_path)
    chunks_by_key = {}

    for language, language_metadata in metadata.get("languages", {}).items():
        chunks_relative_path = language_metadata["files"]["chunks"]
        chunks_path = version_path / chunks_relative_path

        chunks = json.loads(chunks_path.read_text(encoding="utf-8"))

        for chunk in chunks:
            chunk_copy = chunk.copy()
            chunk_copy["language"] = chunk_copy.get("language", language)

            chunk_id = chunk_copy.get("chunk_id")

            if not chunk_id:
                continue

            key = f"{language}:{chunk_id}"
            chunks_by_key[key] = chunk_copy

    return chunks_by_key


def load_chunks_from_documents_data(documents_data: dict) -> dict[str, dict]:
    """
    Loads chunks from freshly downloaded documents_data before saving.

    documents_data structure:
        {
            "ru": {"chunks": [...]},
            "uz": {"chunks": [...]},
        }
    """
    chunks_by_key = {}

    for language, payload in documents_data.items():
        chunks = payload.get("chunks", [])

        for chunk in chunks:
            chunk_copy = chunk.copy()
            chunk_copy["language"] = chunk_copy.get("language", language)

            chunk_id = chunk_copy.get("chunk_id")

            if not chunk_id:
                continue

            key = f"{language}:{chunk_id}"
            chunks_by_key[key] = chunk_copy

    return chunks_by_key


def get_chunk_hash(chunk: dict) -> str:
    existing_hash = chunk.get("hash")

    if existing_hash:
        return existing_hash

    return calculate_hash(chunk.get("text", ""))


def preview_text(text: str, limit: int = 350) -> str:
    text = " ".join(text.split())

    if len(text) <= limit:
        return text

    return text[:limit] + "..."


def summarize_added_chunk(chunk: dict) -> dict:
    return {
        "chunk_id": chunk.get("chunk_id"),
        "language": chunk.get("language"),
        "type": chunk.get("type"),
        "section": chunk.get("section"),
        "hash": get_chunk_hash(chunk),
        "text_preview": preview_text(chunk.get("text", "")),
    }


def summarize_removed_chunk(chunk: dict) -> dict:
    return {
        "chunk_id": chunk.get("chunk_id"),
        "language": chunk.get("language"),
        "type": chunk.get("type"),
        "section": chunk.get("section"),
        "hash": get_chunk_hash(chunk),
        "text_preview": preview_text(chunk.get("text", "")),
    }


def summarize_modified_chunk(old_chunk: dict, new_chunk: dict) -> dict:
    return {
        "chunk_id": new_chunk.get("chunk_id"),
        "language": new_chunk.get("language"),
        "type": new_chunk.get("type"),
        "section": new_chunk.get("section"),
        "old_hash": get_chunk_hash(old_chunk),
        "new_hash": get_chunk_hash(new_chunk),
        "old_text_preview": preview_text(old_chunk.get("text", "")),
        "new_text_preview": preview_text(new_chunk.get("text", "")),
    }


def compare_chunks(
    old_chunks_by_key: dict[str, dict],
    new_chunks_by_key: dict[str, dict],
) -> dict:
    added = []
    removed = []
    modified = []
    unchanged = []

    old_keys = set(old_chunks_by_key.keys())
    new_keys = set(new_chunks_by_key.keys())

    added_keys = sorted(new_keys - old_keys)
    removed_keys = sorted(old_keys - new_keys)
    common_keys = sorted(old_keys & new_keys)

    for key in added_keys:
        added.append(
            summarize_added_chunk(new_chunks_by_key[key])
        )

    for key in removed_keys:
        removed.append(
            summarize_removed_chunk(old_chunks_by_key[key])
        )

    for key in common_keys:
        old_chunk = old_chunks_by_key[key]
        new_chunk = new_chunks_by_key[key]

        old_hash = get_chunk_hash(old_chunk)
        new_hash = get_chunk_hash(new_chunk)

        if old_hash == new_hash:
            unchanged.append(
                {
                    "chunk_id": new_chunk.get("chunk_id"),
                    "language": new_chunk.get("language"),
                    "type": new_chunk.get("type"),
                    "section": new_chunk.get("section"),
                    "hash": new_hash,
                }
            )
        else:
            modified.append(
                summarize_modified_chunk(
                    old_chunk=old_chunk,
                    new_chunk=new_chunk,
                )
            )

    return {
        "has_changes": bool(added or removed or modified),
        "counts": {
            "added": len(added),
            "removed": len(removed),
            "modified": len(modified),
            "unchanged": len(unchanged),
            "old_total": len(old_chunks_by_key),
            "new_total": len(new_chunks_by_key),
        },
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged": unchanged,
    }


def compare_latest_with_documents_data(
    documents_data: dict,
    versions_dir: Path = VERSIONS_DIR,
) -> dict:
    """
    Compares freshly downloaded document chunks with latest saved version.
    """
    latest_version_path = get_latest_version_path(versions_dir)

    new_chunks_by_key = load_chunks_from_documents_data(documents_data)

    if latest_version_path is None:
        return {
            "checked_at": datetime.now().isoformat(timespec="seconds"),
            "old_version_id": None,
            "new_version_id": None,
            "status": "no_previous_version",
            "has_changes": True,
            "counts": {
                "added": len(new_chunks_by_key),
                "removed": 0,
                "modified": 0,
                "unchanged": 0,
                "old_total": 0,
                "new_total": len(new_chunks_by_key),
            },
            "added": [
                summarize_added_chunk(chunk)
                for chunk in new_chunks_by_key.values()
            ],
            "removed": [],
            "modified": [],
            "unchanged": [],
        }

    old_metadata = load_metadata(latest_version_path)
    old_chunks_by_key = load_chunks_from_version(latest_version_path)

    comparison = compare_chunks(
        old_chunks_by_key=old_chunks_by_key,
        new_chunks_by_key=new_chunks_by_key,
    )

    comparison["checked_at"] = datetime.now().isoformat(timespec="seconds")
    comparison["old_version_id"] = old_metadata.get("version_id")
    comparison["new_version_id"] = None
    comparison["status"] = (
        "changed" if comparison["has_changes"] else "no_changes"
    )

    return comparison


def save_changes_file(version_path: Path, changes: dict) -> Path:
    changes_path = version_path / CHANGES_FILENAME

    changes_path.write_text(
        json.dumps(changes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return changes_path
import hashlib
import json
from datetime import datetime
from pathlib import Path

from src.config import (
    RAW_HTML_FILENAME,
    CLEAN_TEXT_FILENAME,
    CHUNKS_FILENAME,
    TABLES_FILENAME,
    METADATA_FILENAME,
)


def calculate_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_version_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _write_json(path: Path, data: dict | list) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_multilingual_document_version(
    versions_dir: Path,
    documents_data: dict,
    status: str = "initial_version",
) -> dict:
    """
    Сохраняет одну версию документа, внутри которой есть RU и UZ варианты.

    Структура:
        data/versions/<version_id>/
            metadata.json
            ru/
                raw.html
                clean_text.txt
                chunks.json
                tables.json
            uz/
                raw.html
                clean_text.txt
                chunks.json
                tables.json
    """
    versions_dir.mkdir(parents=True, exist_ok=True)

    version_id = create_version_id()
    downloaded_at = datetime.now().isoformat(timespec="seconds")

    version_path = versions_dir / version_id
    version_path.mkdir(parents=True, exist_ok=True)

    languages_metadata = {}
    combined_hash_parts = []

    total_chunks_count = 0
    total_tables_count = 0

    for language, payload in documents_data.items():
        language_path = version_path / language
        language_path.mkdir(parents=True, exist_ok=True)

        document_name = payload["document_name"]
        source_url = payload["source_url"]
        raw_html = payload["raw_html"]
        clean_text = payload["clean_text"]
        chunks = payload.get("chunks", [])
        tables = payload.get("tables", [])

        content_hash = calculate_text_hash(clean_text)

        for chunk in chunks:
            chunk["language"] = language
            chunk["document_name"] = document_name
            chunk["source_url"] = source_url

        (language_path / RAW_HTML_FILENAME).write_text(raw_html, encoding="utf-8")
        (language_path / CLEAN_TEXT_FILENAME).write_text(clean_text, encoding="utf-8")
        _write_json(language_path / CHUNKS_FILENAME, chunks)
        _write_json(language_path / TABLES_FILENAME, tables)

        languages_metadata[language] = {
            "document_name": document_name,
            "source_url": source_url,
            "content_hash": content_hash,
            "chunks_count": len(chunks),
            "tables_count": len(tables),
            "files": {
                "raw_html": f"{language}/{RAW_HTML_FILENAME}",
                "clean_text": f"{language}/{CLEAN_TEXT_FILENAME}",
                "chunks": f"{language}/{CHUNKS_FILENAME}",
                "tables": f"{language}/{TABLES_FILENAME}",
            },
        }

        combined_hash_parts.append(f"{language}:{content_hash}")
        total_chunks_count += len(chunks)
        total_tables_count += len(tables)

    overall_content_hash = calculate_text_hash("\n".join(sorted(combined_hash_parts)))

    metadata = {
        "version_id": version_id,
        "downloaded_at": downloaded_at,
        "overall_content_hash": overall_content_hash,
        "status": status,
        "languages": languages_metadata,
        "total_chunks_count": total_chunks_count,
        "total_tables_count": total_tables_count,
    }

    _write_json(version_path / METADATA_FILENAME, metadata)

    return metadata


def get_latest_version_metadata(versions_dir: Path) -> dict | None:
    if not versions_dir.exists():
        return None

    version_folders = [
        path
        for path in versions_dir.iterdir()
        if path.is_dir() and (path / METADATA_FILENAME).exists()
    ]

    if not version_folders:
        return None

    latest_version_path = sorted(version_folders)[-1]
    metadata_path = latest_version_path / METADATA_FILENAME

    return json.loads(metadata_path.read_text(encoding="utf-8"))
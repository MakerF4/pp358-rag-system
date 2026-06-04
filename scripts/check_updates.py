import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))


from src.config import (
    DOCUMENTS,
    VERSIONS_DIR,
    METADATA_FILENAME,
    CHANGES_FILENAME,
)
from src.scraper import fetch_document_html
from src.cleaner import clean_html_to_text
from src.chunker import chunk_text
from src.table_parser import parse_tables_from_html
from src.versioning import save_multilingual_document_version
from src.change_detector import (
    compare_latest_with_documents_data,
    save_changes_file,
)


def add_language_prefix(chunks: list[dict], language: str) -> list[dict]:
    updated_chunks = []

    for chunk in chunks:
        chunk_copy = chunk.copy()

        if not chunk_copy["chunk_id"].startswith(f"{language}_"):
            chunk_copy["chunk_id"] = f"{language}_{chunk_copy['chunk_id']}"

        chunk_copy["language"] = language
        updated_chunks.append(chunk_copy)

    return updated_chunks


def ingest_language(language: str, document_config: dict) -> dict:
    document_name = document_config["name"]
    document_url = document_config["url"]

    print(f"\n=== Checking language: {language.upper()} ===")
    print(f"Document: {document_name}")
    print(f"URL: {document_url}")

    print("Downloading document...")
    raw_html = fetch_document_html(document_url)

    print("Cleaning HTML...")
    clean_text = clean_html_to_text(raw_html)

    print("Extracting tables...")
    tables, table_chunks = parse_tables_from_html(raw_html)

    print("Chunking text...")
    text_chunks = chunk_text(clean_text)

    all_chunks = text_chunks + table_chunks
    all_chunks = add_language_prefix(all_chunks, language)

    print(f"Chunks: {len(all_chunks)}")
    print(f"Tables: {len(tables)}")

    return {
        "document_name": document_name,
        "source_url": document_url,
        "raw_html": raw_html,
        "clean_text": clean_text,
        "chunks": all_chunks,
        "tables": tables,
    }


def update_metadata_with_changes(
    version_path: Path,
    metadata: dict,
    changes: dict,
) -> None:
    metadata["changes"] = {
        "changes_file": CHANGES_FILENAME,
        "has_changes": changes["has_changes"],
        "counts": changes["counts"],
    }

    metadata_path = version_path / METADATA_FILENAME

    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def print_changes_summary(changes: dict) -> None:
    counts = changes["counts"]

    print("\n=== Change summary ===")
    print(f"Status: {changes['status']}")
    print(f"Old version: {changes.get('old_version_id')}")
    print(f"New version: {changes.get('new_version_id')}")
    print(f"Added: {counts['added']}")
    print(f"Removed: {counts['removed']}")
    print(f"Modified: {counts['modified']}")
    print(f"Unchanged: {counts['unchanged']}")
    print(f"Old total: {counts['old_total']}")
    print(f"New total: {counts['new_total']}")

    if changes["added"]:
        print("\nAdded examples:")
        for item in changes["added"][:5]:
            print(
                f"- {item['language']} | {item['chunk_id']} | "
                f"{item.get('section')}"
            )

    if changes["modified"]:
        print("\nModified examples:")
        for item in changes["modified"][:5]:
            print(
                f"- {item['language']} | {item['chunk_id']} | "
                f"{item.get('section')}"
            )

    if changes["removed"]:
        print("\nRemoved examples:")
        for item in changes["removed"][:5]:
            print(
                f"- {item['language']} | {item['chunk_id']} | "
                f"{item.get('section')}"
            )


def main() -> None:
    print("Checking lex.uz for PP-358 updates...")

    documents_data = {}

    for language, document_config in DOCUMENTS.items():
        documents_data[language] = ingest_language(
            language=language,
            document_config=document_config,
        )

    print("\nComparing with latest saved version...")

    changes = compare_latest_with_documents_data(
        documents_data=documents_data,
        versions_dir=VERSIONS_DIR,
    )

    if not changes["has_changes"]:
        print("\nNo changes found.")
        print_changes_summary(changes)
        return

    print("\nChanges found. Saving new version...")

    status = (
        "initial_version"
        if changes.get("old_version_id") is None
        else "updated_version"
    )

    metadata = save_multilingual_document_version(
        versions_dir=VERSIONS_DIR,
        documents_data=documents_data,
        status=status,
    )

    version_path = VERSIONS_DIR / metadata["version_id"]

    changes["new_version_id"] = metadata["version_id"]

    save_changes_file(
        version_path=version_path,
        changes=changes,
    )

    update_metadata_with_changes(
        version_path=version_path,
        metadata=metadata,
        changes=changes,
    )

    print("\nNew version saved.")
    print(f"Version ID: {metadata['version_id']}")
    print(f"Saved to: {version_path}")

    print_changes_summary(changes)

    print("\nImportant:")
    print("Document changed, so rebuild VectorDB:")
    print("python3 scripts/build_vector_store.py")


if __name__ == "__main__":
    main()
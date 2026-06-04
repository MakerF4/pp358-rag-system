import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))


from src.config import DOCUMENTS, VERSIONS_DIR
from src.scraper import fetch_document_html
from src.cleaner import clean_html_to_text
from src.chunker import chunk_text
from src.table_parser import parse_tables_from_html
from src.versioning import save_multilingual_document_version


def add_language_prefix(chunks: list[dict], language: str) -> list[dict]:
    """
    Добавляет language prefix к chunk_id, чтобы RU и UZ chunks
    не конфликтовали в одной VectorDB.
    """
    updated_chunks = []

    for chunk in chunks:
        chunk_copy = chunk.copy()
        chunk_copy["chunk_id"] = f"{language}_{chunk_copy['chunk_id']}"
        chunk_copy["language"] = language
        updated_chunks.append(chunk_copy)

    return updated_chunks


def ingest_language(language: str, document_config: dict) -> dict:
    document_name = document_config["name"]
    document_url = document_config["url"]

    print(f"\n=== Обработка языка: {language.upper()} ===")
    print(f"Документ: {document_name}")
    print(f"URL: {document_url}")

    print("Скачивание документа с lex.uz...")
    raw_html = fetch_document_html(document_url)

    print("Очистка HTML и извлечение текста документа...")
    clean_text = clean_html_to_text(raw_html)

    print("Извлечение таблиц из HTML...")
    tables, table_chunks = parse_tables_from_html(raw_html)

    print("Разделение документа на chunks...")
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


def main() -> None:
    documents_data = {}

    for language, document_config in DOCUMENTS.items():
        documents_data[language] = ingest_language(
            language=language,
            document_config=document_config,
        )

    print("\nСохранение multilingual версии документа...")

    metadata = save_multilingual_document_version(
        versions_dir=VERSIONS_DIR,
        documents_data=documents_data,
    )

    version_path = VERSIONS_DIR / metadata["version_id"]

    print("\nГотово.")
    print(f"ID версии: {metadata['version_id']}")
    print(f"Дата загрузки: {metadata['downloaded_at']}")
    print(f"Общий hash: {metadata['overall_content_hash']}")
    print(f"Всего chunks: {metadata['total_chunks_count']}")
    print(f"Всего таблиц: {metadata['total_tables_count']}")
    print(f"Сохранено в: {version_path}")

    print("\nПо языкам:")

    for language, language_metadata in metadata["languages"].items():
        print(
            f"- {language.upper()}: "
            f"{language_metadata['chunks_count']} chunks, "
            f"{language_metadata['tables_count']} tables"
        )


if __name__ == "__main__":
    main()
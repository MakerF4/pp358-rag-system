import json
from pathlib import Path
from typing import Any

import chromadb
from openai import OpenAI

from src.config import (
    VERSIONS_DIR,
    METADATA_FILENAME,
    CHUNKS_FILENAME,
    CHROMA_PATH,
    CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL,
    TOP_K,
)


openai_client = OpenAI()


def get_latest_version_path(versions_dir: Path = VERSIONS_DIR) -> Path:
    """
    Возвращает путь к последней сохранённой версии документа.
    """
    if not versions_dir.exists():
        raise FileNotFoundError(
            "Папка data/versions не найдена. Сначала запустите scripts/ingest_document.py"
        )

    version_folders = [
        path
        for path in versions_dir.iterdir()
        if path.is_dir() and (path / METADATA_FILENAME).exists()
    ]

    if not version_folders:
        raise FileNotFoundError(
            "Нет сохранённых версий документа. Сначала запустите scripts/ingest_document.py"
        )

    return sorted(version_folders)[-1]


def load_latest_chunks() -> tuple[dict, list[dict]]:
    """
    Загружает chunks из последней multilingual версии.

    Ожидаем структуру:
        data/versions/<version_id>/
            metadata.json
            ru/chunks.json
            uz/chunks.json
    """
    version_path = get_latest_version_path()

    metadata_path = version_path / METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    all_chunks = []

    languages = metadata.get("languages", {})

    for language, language_metadata in languages.items():
        chunks_file = language_metadata["files"]["chunks"]
        chunks_path = version_path / chunks_file

        chunks = json.loads(chunks_path.read_text(encoding="utf-8"))

        for chunk in chunks:
            chunk["version_id"] = metadata["version_id"]
            chunk["language"] = chunk.get("language", language)
            chunk["document_name"] = chunk.get(
                "document_name",
                language_metadata.get("document_name", ""),
            )
            chunk["source_url"] = chunk.get(
                "source_url",
                language_metadata.get("source_url", ""),
            )

        all_chunks.extend(chunks)

    return metadata, all_chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Создаёт embeddings для списка текстов через OpenAI.
    """
    if not texts:
        return []

    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )

    return [item.embedding for item in response.data]


def get_collection():
    """
    Возвращает ChromaDB collection.
    """
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    collection = chroma_client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={
            "hnsw:space": "cosine",
            "description": "PP-358 multilingual RU/UZ chunks",
        },
    )

    return collection


def _safe_metadata_value(value: Any) -> str | int | float | bool:
    """
    Chroma metadata не любит сложные типы.
    Поэтому всё сложное переводим в строку.
    """
    if value is None:
        return ""

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


def build_chunk_metadata(chunk: dict, version_id: str) -> dict:
    """
    Metadata, по которой потом будем фильтровать retrieval.
    """
    metadata = {
        "version_id": version_id,
        "chunk_id": chunk.get("chunk_id", ""),
        "section": chunk.get("section", ""),
        "type": chunk.get("type", ""),
        "language": chunk.get("language", ""),
        "document_name": chunk.get("document_name", ""),
        "source_url": chunk.get("source_url", ""),
        "table_id": chunk.get("table_id", ""),
        "row_number": chunk.get("row_number", 0),
    }

    return {
        key: _safe_metadata_value(value)
        for key, value in metadata.items()
    }


def build_vector_store(batch_size: int = 64) -> dict:
    """
    Индексирует все RU + UZ chunks из последней версии в ChromaDB.
    """
    metadata, chunks = load_latest_chunks()
    version_id = metadata["version_id"]

    collection = get_collection()

    ids = []
    documents = []
    metadatas = []

    for chunk in chunks:
        text = chunk.get("text", "").strip()

        if not text:
            continue

        chunk_id = chunk.get("chunk_id")

        if not chunk_id:
            continue

        ids.append(f"{version_id}_{chunk_id}")
        documents.append(text)
        metadatas.append(
            build_chunk_metadata(
                chunk=chunk,
                version_id=version_id,
            )
        )

    if not documents:
        raise ValueError("Нет chunks для индексации.")

    total_indexed = 0

    for start_index in range(0, len(documents), batch_size):
        end_index = start_index + batch_size

        batch_ids = ids[start_index:end_index]
        batch_documents = documents[start_index:end_index]
        batch_metadatas = metadatas[start_index:end_index]

        batch_embeddings = embed_texts(batch_documents)

        collection.upsert(
            ids=batch_ids,
            documents=batch_documents,
            metadatas=batch_metadatas,
            embeddings=batch_embeddings,
        )

        total_indexed += len(batch_documents)

        print(f"Indexed {total_indexed}/{len(documents)} chunks...")

    return {
        "version_id": version_id,
        "collection_name": CHROMA_COLLECTION_NAME,
        "chunks_indexed": total_indexed,
        "chroma_path": str(CHROMA_PATH),
    }


def _build_where_filter(
    language_filter: str | None = None,
    version_id: str | None = None,
) -> dict | None:
    conditions = []

    if language_filter:
        conditions.append({"language": language_filter})

    if version_id:
        conditions.append({"version_id": version_id})

    if not conditions:
        return None

    if len(conditions) == 1:
        return conditions[0]

    return {"$and": conditions}


def search_chunks(
    query: str,
    language_filter: str | None = None,
    top_k: int = TOP_K,
    version_id: str | None = None,
) -> list[dict]:
    """
    Ищет chunks в ChromaDB.

    language_filter:
        "ru" → искать только RU chunks
        "uz" → искать только UZ chunks
        None → искать по всем языкам
    """
    if version_id is None:
        latest_metadata, _ = load_latest_chunks()
        version_id = latest_metadata["version_id"]

    collection = get_collection()

    query_embedding = embed_texts([query])[0]

    where_filter = _build_where_filter(
        language_filter=language_filter,
        version_id=version_id,
    )

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    found_chunks = []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for document, metadata, distance in zip(documents, metadatas, distances):
        found_chunks.append(
            {
                "text": document,
                "metadata": metadata,
                "distance": distance,
            }
        )

    return found_chunks
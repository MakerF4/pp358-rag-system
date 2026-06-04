import json
import subprocess
import sys
from pathlib import Path

import streamlit as st

from src.config import (
    VERSIONS_DIR,
    METADATA_FILENAME,
    CHANGES_FILENAME,
)
from src.rag import answer_question


def get_version_folders() -> list[Path]:
    if not VERSIONS_DIR.exists():
        return []

    return sorted(
        [
            path
            for path in VERSIONS_DIR.iterdir()
            if path.is_dir() and (path / METADATA_FILENAME).exists()
        ]
    )


def get_latest_version_path() -> Path | None:
    version_folders = get_version_folders()

    if not version_folders:
        return None

    return version_folders[-1]


def load_latest_metadata() -> dict | None:
    latest_version_path = get_latest_version_path()

    if latest_version_path is None:
        return None

    metadata_path = latest_version_path / METADATA_FILENAME

    return json.loads(metadata_path.read_text(encoding="utf-8"))


def load_latest_changes() -> dict | None:
    latest_version_path = get_latest_version_path()

    if latest_version_path is None:
        return None

    changes_path = latest_version_path / CHANGES_FILENAME

    if not changes_path.exists():
        return None

    return json.loads(changes_path.read_text(encoding="utf-8"))


def run_update_check() -> str:
    process = subprocess.run(
        [sys.executable, "scripts/check_updates.py"],
        capture_output=True,
        text=True,
    )

    output = ""

    if process.stdout:
        output += process.stdout

    if process.stderr:
        output += "\n\nERROR:\n" + process.stderr

    return output


def render_status_block() -> None:
    metadata = load_latest_metadata()
    changes = load_latest_changes()

    st.subheader("Статус документа")

    if metadata is None:
        st.warning("Версии документа пока не найдены. Сначала запустите ingest_document.py.")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Текущая версия", metadata.get("version_id", "N/A"))

    with col2:
        st.metric("Всего chunks", metadata.get("total_chunks_count", 0))

    with col3:
        st.metric("Всего таблиц", metadata.get("total_tables_count", 0))

    st.write(f"**Дата загрузки:** {metadata.get('downloaded_at', 'N/A')}")
    st.write(f"**Hash документа:** `{metadata.get('overall_content_hash', 'N/A')}`")

    languages = metadata.get("languages", {})

    with st.expander("Информация по языкам"):
        for language, language_metadata in languages.items():
            st.write(f"### {language.upper()}")
            st.write(f"**Документ:** {language_metadata.get('document_name')}")
            st.write(f"**URL:** {language_metadata.get('source_url')}")
            st.write(f"**Chunks:** {language_metadata.get('chunks_count')}")
            st.write(f"**Tables:** {language_metadata.get('tables_count')}")
            st.write(f"**Content hash:** `{language_metadata.get('content_hash')}`")

    if changes:
        counts = changes.get("counts", {})

        st.write("### Изменения по сравнению с предыдущей версией")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Added", counts.get("added", 0))

        with col2:
            st.metric("Removed", counts.get("removed", 0))

        with col3:
            st.metric("Modified", counts.get("modified", 0))

        with col4:
            st.metric("Unchanged", counts.get("unchanged", 0))

        with st.expander("Детали изменений"):
            if changes.get("added"):
                st.write("#### Added chunks")
                st.json(changes["added"][:10])

            if changes.get("modified"):
                st.write("#### Modified chunks")
                st.json(changes["modified"][:10])

            if changes.get("removed"):
                st.write("#### Removed chunks")
                st.json(changes["removed"][:10])

            if not changes.get("added") and not changes.get("modified") and not changes.get("removed"):
                st.info("Для этой версии файл changes.json отсутствует или изменений не было.")


def render_sources(sources: list[dict]) -> None:
    st.subheader("Найденные chunks / контекст для ответа")

    for index, source in enumerate(sources, start=1):
        chunk_id = source.get("chunk_id")
        section = source.get("section")
        language = source.get("language")
        source_type = source.get("type")
        distance = source.get("distance")
        rerank_score = source.get("rerank_score")
        source_url = source.get("source_url")
        text = source.get("text")

        with st.expander(f"Найденный chunk {index}: {chunk_id}"):
            st.write(f"**Language:** {language}")
            st.write(f"**Type:** {source_type}")
            st.write(f"**Section:** {section}")
            st.write(f"**Distance:** {distance}")
            st.write(f"**Rerank score:** {rerank_score}")

            if source_url:
                st.write(f"**Source URL:** {source_url}")

            st.text_area(
                label="Chunk text",
                value=text or "",
                height=220,
                key=f"source_text_{index}_{chunk_id}",
            )


def main() -> None:
    st.set_page_config(
        page_title="PP-358 RAG System",
        page_icon="📄",
        layout="wide",
    )

    st.title("PP-358 RAG System")
    st.write(
        "RAG-система по Постановлению Президента Республики Узбекистан № ПП-358. "
        "Поддерживает вопросы на русском и узбекском языках."
    )

    render_status_block()

    st.divider()

    st.subheader("Проверка обновлений")

    if st.button("Проверить обновления"):
        with st.spinner("Проверяем lex.uz..."):
            output = run_update_check()

        st.code(output)

        if "Changes found" in output:
            st.warning(
                "Обнаружены изменения. После проверки нужно пересобрать VectorDB: "
                "`python3 scripts/build_vector_store.py`"
            )
        else:
            st.success("Проверка завершена.")

    st.divider()

    st.subheader("Задать вопрос")

    question = st.text_area(
        "Введите вопрос на русском или узбекском языке",
        height=120,
        placeholder="Например: Сколько научных лабораторий в сфере ИИ должно быть к 2030 году?",
    )

    top_k = st.slider(
        "Количество chunks для retrieval",
        min_value=3,
        max_value=10,
        value=5,
    )

    if st.button("Получить ответ"):
        if not question.strip():
            st.warning("Введите вопрос.")
            return

        with st.spinner("Ищем релевантные chunks и генерируем ответ..."):
            result = answer_question(
                question=question,
                top_k=top_k,
            )

        st.subheader("Ответ")
        st.write(result["answer"])

        st.write(f"**Detected language:** `{result['language']}`")

        render_sources(result["sources"])


if __name__ == "__main__":
    main()
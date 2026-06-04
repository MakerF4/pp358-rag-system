import hashlib
import re


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_section_start(line: str) -> bool:
    """
    Определяет начало нового смыслового блока в правовом документе.
    """
    patterns = [
        r"^\d+\.",                    # 1. 2. 3.
        r"^\d+\)$",                   # 1)
        r"^[а-я]\)",                  # а) б) в)
        r"^Глава\s+\d+\.",            # Глава 1.
        r"^§\d+\.",                   # §1.
        r"^ПРИЛОЖЕНИЕ",               # ПРИЛОЖЕНИЕ
        r"^Приложение №",             # Приложение № 1
        r"^СТРАТЕГИЯ",                # СТРАТЕГИЯ
        r"^ПЛАН МЕРОПРИЯТИЙ",         # ПЛАН МЕРОПРИЯТИЙ
        r"^ПЕРЕЧЕНЬ",                 # ПЕРЕЧЕНЬ
        r"^ЦЕЛЕВЫЕ ПОКАЗАТЕЛИ",       # ЦЕЛЕВЫЕ ПОКАЗАТЕЛИ
    ]

    return any(re.match(pattern, line) for pattern in patterns)


def _detect_chunk_type(section_title: str) -> str:
    lowered = section_title.lower()

    if "приложение" in lowered:
        return "appendix"

    if "глава" in lowered:
        return "chapter"

    if "план мероприятий" in lowered:
        return "action_plan"

    if "перечень" in lowered:
        return "data_list"

    if "целевые показатели" in lowered:
        return "targets"

    return "legal_section"


def chunk_text(clean_text: str) -> list[dict]:
    """
    Делит очищенный текст ПП-358 на смысловые правовые chunks.

    Подход:
    - не режем просто каждые 500 токенов;
    - стараемся делить по пунктам, главам, приложениям и подпунктам;
    - каждый chunk получает section, type и hash.

    Args:
        clean_text: Очищенный текст документа.

    Returns:
        Список chunks для дальнейшего RAG.
    """
    lines = [line.strip() for line in clean_text.splitlines() if line.strip()]

    chunks = []
    current_lines = []
    current_section = "Введение"
    chunk_number = 1

    for line in lines:
        starts_new_section = _is_section_start(line)

        if starts_new_section and current_lines:
            chunk_text_value = "\n".join(current_lines).strip()

            chunk = {
                "chunk_id": f"chunk_{chunk_number:04d}",
                "section": current_section,
                "type": _detect_chunk_type(current_section),
                "text": chunk_text_value,
                "hash": _hash_text(chunk_text_value),
            }

            chunks.append(chunk)

            chunk_number += 1
            current_lines = []

        if starts_new_section:
            current_section = line

        current_lines.append(line)

    if current_lines:
        chunk_text_value = "\n".join(current_lines).strip()

        chunk = {
            "chunk_id": f"chunk_{chunk_number:04d}",
            "section": current_section,
            "type": _detect_chunk_type(current_section),
            "text": chunk_text_value,
            "hash": _hash_text(chunk_text_value),
        }

        chunks.append(chunk)

    return chunks
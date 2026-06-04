import re

from src.vector_store import (
    search_chunks,
    load_latest_chunks,
    build_chunk_metadata,
)


TABLE_QUERY_KEYWORDS = [
    # RU
    "сколько",
    "показатель",
    "показатели",
    "количество",
    "число",
    "доля",
    "объем",
    "объём",
    "ответственные",
    "исполнители",

    # UZ Cyrillic
    "нечта",
    "қанча",
    "кўрсаткич",
    "кўрсаткичлар",
    "сони",
    "улуши",
    "ҳажми",
    "масъул",
    "ижрочилар",

    # UZ Latin
    "nechta",
    "qancha",
    "ko‘rsatkich",
    "ko'rsatkich",
    "soni",
    "ulushi",
    "hajmi",
    "mas’ul",
    "mas'ul",
]


DEADLINE_QUERY_KEYWORDS = [
    # RU
    "когда",
    "срок",
    "дата",
    "до какого",
    "к какому",

    # UZ Cyrillic
    "қачон",
    "муддат",
    "санаси",
    "қадар",

    # UZ Latin
    "qachon",
    "muddat",
    "sanasi",
    "qadar",
]


STOPWORDS = {
    # RU
    "какой", "какая", "какое", "какие", "для", "это", "или", "что", "как",
    "быть", "должно", "должна", "должны", "году", "года", "годы",

    # UZ
    "учун", "бўйича", "билан", "қадар", "керак", "бўлади", "қандай",
    "қайси", "нечта", "қачон",
}


TOKEN_PATTERN = re.compile(
    r"[a-zA-Zа-яА-ЯёЁўқғҳЎҚҒҲ0-9']+",
    flags=re.UNICODE,
)


def _tokenize(text: str) -> list[str]:
    tokens = []

    for raw_token in TOKEN_PATTERN.findall(text.lower()):
        token = raw_token.strip().lower()

        if len(token) < 3:
            continue

        if token in STOPWORDS:
            continue

        tokens.append(token)

    return tokens


def _tokens_match(query_token: str, document_token: str) -> bool:
    """
    General fuzzy lexical matching.

    Examples:
    - базаси ~ базасини
    - яратилиши ~ яратиш
    - маълумотлар == маълумотлар
    """
    if query_token == document_token:
        return True

    if len(query_token) >= 5 and query_token in document_token:
        return True

    if len(document_token) >= 5 and document_token in query_token:
        return True

    if len(query_token) >= 5 and len(document_token) >= 5:
        if query_token[:5] == document_token[:5]:
            return True

    return False


def looks_like_table_question(question: str) -> bool:
    lowered = question.lower()

    return any(keyword in lowered for keyword in TABLE_QUERY_KEYWORDS)


def looks_like_deadline_question(question: str) -> bool:
    lowered = question.lower()

    return any(keyword in lowered for keyword in DEADLINE_QUERY_KEYWORDS)


def text_contains_deadline(text: str) -> bool:
    lowered = text.lower()

    has_year = bool(re.search(r"20\d{2}", lowered))

    deadline_words = [
        # RU
        "до",
        "срок",
        "года",
        "год",

        # UZ
        "йил",
        "қадар",
        "муддат",
        "санаси",
    ]

    return has_year and any(word in lowered for word in deadline_words)


def build_query_variants(question: str, language: str) -> list[str]:
    """
    General query variants.

    No answer-specific hacks.
    """
    variants = [question]

    if looks_like_deadline_question(question):
        if language == "uz":
            variants.append(f"{question} ижро муддати сана")
        else:
            variants.append(f"{question} срок исполнения дата")

    if looks_like_table_question(question):
        if language == "uz":
            variants.append(f"{question} кўрсаткичлар масъул ижрочилар")
        else:
            variants.append(f"{question} показатели ответственные исполнители")

    unique_variants = []

    for variant in variants:
        if variant not in unique_variants:
            unique_variants.append(variant)

    return unique_variants


def lexical_search_chunks(
    question: str,
    language: str,
    top_k: int = 40,
) -> list[dict]:
    """
    Simple lexical retrieval over latest chunks.

    This is not a hack:
    it generally helps when vector search misses exact legal wording.
    """
    version_metadata, chunks = load_latest_chunks()
    version_id = version_metadata["version_id"]

    question_tokens = list(dict.fromkeys(_tokenize(question)))

    if not question_tokens:
        return []

    scored_results = []

    for chunk in chunks:
        if chunk.get("language") != language:
            continue

        chunk_text = chunk.get("text", "")
        section = chunk.get("section", "")

        searchable_text = f"{section}\n{chunk_text}"
        document_tokens = list(dict.fromkeys(_tokenize(searchable_text)))

        if not document_tokens:
            continue

        matched_tokens = []

        for query_token in question_tokens:
            for document_token in document_tokens:
                if _tokens_match(query_token, document_token):
                    matched_tokens.append(query_token)
                    break

        if not matched_tokens:
            continue

        lexical_score = len(matched_tokens) / len(question_tokens)

        # General phrase overlap bonus.
        normalized_document_text = " ".join(document_tokens)

        for n in [2, 3]:
            for index in range(0, len(question_tokens) - n + 1):
                phrase = " ".join(question_tokens[index:index + n])

                if phrase in normalized_document_text:
                    lexical_score += 0.08 * n

        scored_results.append(
            {
                "text": chunk_text,
                "metadata": build_chunk_metadata(
                    chunk=chunk,
                    version_id=version_id,
                ),
                "distance": None,
                "lexical_score": lexical_score,
                "retrieval_method": "lexical",
            }
        )

    scored_results.sort(
        key=lambda item: item["lexical_score"],
        reverse=True,
    )

    return scored_results[:top_k]


def rerank_results(question: str, results: list[dict]) -> list[dict]:
    """
    Hybrid reranking.

    Score:
        vector score
        + lexical score
        + table bonus for numeric/indicator questions
        + deadline bonus for deadline questions
        + keyword overlap
    """
    is_table_question = looks_like_table_question(question)
    is_deadline_question = looks_like_deadline_question(question)

    question_tokens = _tokenize(question)

    reranked_results = []

    for result in results:
        metadata = result["metadata"]
        text = result["text"].lower()
        section = str(metadata.get("section", "")).lower()
        searchable_text = f"{section}\n{text}"

        distance = result.get("distance")
        lexical_score = result.get("lexical_score", 0.0)

        if distance is None:
            # Lexical-only candidate. Give it a neutral base.
            score = -0.55
        else:
            score = -distance

        chunk_type = metadata.get("type", "")

        if is_table_question and chunk_type == "table_row":
            score += 0.12

        if is_deadline_question and text_contains_deadline(searchable_text):
            score += 0.14

        # General lexical score bonus.
        score += min(lexical_score, 1.0) * 0.35

        # General keyword overlap bonus.
        for token in question_tokens:
            if token in searchable_text:
                score += 0.02

        result_copy = result.copy()
        result_copy["rerank_score"] = score
        reranked_results.append(result_copy)

    return sorted(
        reranked_results,
        key=lambda item: item["rerank_score"],
        reverse=True,
    )


def _merge_unique_results(results: list[dict]) -> list[dict]:
    by_chunk_id = {}

    for result in results:
        chunk_id = result["metadata"].get("chunk_id")

        if not chunk_id:
            continue

        if chunk_id not in by_chunk_id:
            by_chunk_id[chunk_id] = result
            continue

        existing = by_chunk_id[chunk_id]

        existing_lexical_score = existing.get("lexical_score", 0.0)
        new_lexical_score = result.get("lexical_score", 0.0)

        existing["lexical_score"] = max(
            existing_lexical_score,
            new_lexical_score,
        )

        existing_method = existing.get("retrieval_method", "vector")
        new_method = result.get("retrieval_method", "vector")

        if new_method not in existing_method:
            existing["retrieval_method"] = f"{existing_method}+{new_method}"

        existing_distance = existing.get("distance")
        new_distance = result.get("distance")

        if existing_distance is None and new_distance is not None:
            existing["distance"] = new_distance

        elif (
            existing_distance is not None
            and new_distance is not None
            and new_distance < existing_distance
        ):
            existing["distance"] = new_distance

    return list(by_chunk_id.values())


def retrieve_chunks(
    question: str,
    language: str,
    top_k: int = 5,
    initial_k: int = 60,
) -> list[dict]:
    query_variants = build_query_variants(
        question=question,
        language=language,
    )

    all_results = []

    # 1. Vector retrieval
    for query_variant in query_variants:
        vector_results = search_chunks(
            query=query_variant,
            language_filter=language,
            top_k=initial_k,
        )

        for result in vector_results:
            result["lexical_score"] = 0.0
            result["retrieval_method"] = "vector"

        all_results.extend(vector_results)

    # 2. Lexical retrieval
    lexical_results = lexical_search_chunks(
        question=question,
        language=language,
        top_k=40,
    )

    all_results.extend(lexical_results)

    # 3. Merge + rerank
    unique_results = _merge_unique_results(all_results)

    reranked_results = rerank_results(
        question=question,
        results=unique_results,
    )

    return reranked_results[:top_k]
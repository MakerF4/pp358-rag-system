from openai import OpenAI

from src.config import LLM_MODEL
from src.language import detect_question_language
from src.retriever import retrieve_chunks


openai_client = OpenAI()


def format_context(chunks: list[dict]) -> str:
    """
    Converts retrieved chunks into numbered context blocks.
    """
    context_blocks = []

    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk["metadata"]

        block = f"""
[Источник {index}]
Chunk ID: {metadata.get("chunk_id")}
Language: {metadata.get("language")}
Type: {metadata.get("type")}
Section: {metadata.get("section")}
Source URL: {metadata.get("source_url")}
Text:
{chunk["text"]}
""".strip()

        context_blocks.append(block)

    return "\n\n".join(context_blocks)


def build_system_prompt(language: str) -> str:
    if language == "uz":
        return """
Сен ҳуқуқий ҳужжат бўйича RAG ёрдамчисисан.

Қоидалар:
1. Фақат берилган манбаларга таяниб жавоб бер.
2. Агар манбаларда жавоб бўлмаса, "Берилган манбаларда бу ҳақда маълумот топилмади" деб айт.
3. Жавобни ўзбек тилида бер.
4. Жавоб охирида қайси chunk/source ишлатилганини кўрсат.
5. Рақамлар, муддатлар ва ташкилот номларини аниқ сақла.
""".strip()

    return """
Ты RAG-ассистент по правовому документу.

Правила:
1. Отвечай только на основе предоставленных источников.
2. Если ответа в источниках нет, скажи: "В предоставленных источниках эта информация не найдена".
3. Отвечай на русском языке.
4. В конце ответа укажи, какие chunk/source были использованы.
5. Числа, сроки и названия организаций сохраняй точно.
""".strip()


def generate_answer(question: str, chunks: list[dict], language: str) -> str:
    context = format_context(chunks)
    system_prompt = build_system_prompt(language)

    user_prompt = f"""
Вопрос:
{question}

Источники:
{context}

Сформируй ответ только на основе источников.
""".strip()

    response = openai_client.responses.create(
        model=LLM_MODEL,
        input=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    )

    return response.output_text


def answer_question(question: str, top_k: int = 5) -> dict:
    """
    Full RAG pipeline:
    1. Detect language
    2. Retrieve chunks with language filter
    3. Generate grounded answer
    4. Return answer + sources
    """
    language = detect_question_language(question)

    chunks = retrieve_chunks(
    question=question,
    language=language,
    top_k=top_k,
    initial_k=60,
)

    answer = generate_answer(
        question=question,
        chunks=chunks,
        language=language,
    )

    sources = []

    for chunk in chunks:
        metadata = chunk["metadata"]

        sources.append(
            {
                "chunk_id": metadata.get("chunk_id"),
                "language": metadata.get("language"),
                "type": metadata.get("type"),
                "section": metadata.get("section"),
                "source_url": metadata.get("source_url"),
                "distance": chunk.get("distance"),
                "rerank_score": chunk.get("rerank_score"),
                "text": chunk.get("text"),
            }
        )

    return {
        "question": question,
        "language": language,
        "answer": answer,
        "sources": sources,
    }
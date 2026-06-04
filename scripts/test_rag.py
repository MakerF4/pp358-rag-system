import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))


from src.rag import answer_question


def print_rag_result(result: dict) -> None:
    print("\n" + "=" * 80)
    print("QUESTION")
    print("=" * 80)
    print(result["question"])

    print("\n" + "=" * 80)
    print("DETECTED LANGUAGE")
    print("=" * 80)
    print(result["language"])

    print("\n" + "=" * 80)
    print("ANSWER")
    print("=" * 80)
    print(result["answer"])

    print("\n" + "=" * 80)
    print("SOURCES")
    print("=" * 80)

    for index, source in enumerate(result["sources"], start=1):
        print(f"\nSource {index}")
        print(f"Chunk ID: {source['chunk_id']}")
        print(f"Language: {source['language']}")
        print(f"Type: {source['type']}")
        print(f"Section: {source['section']}")
        print(f"Distance: {source['distance']}")
        print(f"Rerank score: {source['rerank_score']}")
        print("-" * 40)
        print(source["text"][:700])


def main() -> None:
    questions = [
        "Сколько научных лабораторий в сфере искусственного интеллекта должно быть к 2030 году?",
        "2030 йилга қадар сунъий интеллект йўналишидаги илмий лабораториялар сони нечта бўлади?",
        "Какой кредит выделяется Министерству цифровых технологий для развития искусственного интеллекта?",
        "Сунъий интеллект учун катта маълумотлар базаси қачон яратилиши керак?",
    ]

    for question in questions:
        result = answer_question(question)
        print_rag_result(result)


if __name__ == "__main__":
    main()
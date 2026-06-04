import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))


from src.retriever import retrieve_chunks


def print_results(title: str, results: list[dict]) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    for index, result in enumerate(results, start=1):
        metadata = result["metadata"]

        print(f"\nResult {index}")
        print(f"Distance: {result['distance']}")
        print(f"Rerank score: {result.get('rerank_score')}")
        print(f"Chunk ID: {metadata.get('chunk_id')}")
        print(f"Language: {metadata.get('language')}")
        print(f"Type: {metadata.get('type')}")
        print(f"Section: {metadata.get('section')}")
        print("-" * 40)
        print(result["text"][:1000])


def main() -> None:
    ru_query = "Сколько научных лабораторий в сфере искусственного интеллекта должно быть к 2030 году?"

    uz_query = "2030 йилга қадар сунъий интеллект йўналишидаги илмий лабораториялар сони нечта бўлади?"

    ru_results = retrieve_chunks(
    question=ru_query,
    language="ru",
    top_k=5,
)

    uz_results = retrieve_chunks(
    question=uz_query,
    language="uz",
    top_k=5,
)



    print_results("RU query → RU chunks only", ru_results)
    print_results("UZ query → UZ chunks only", uz_results)


if __name__ == "__main__":
    main()
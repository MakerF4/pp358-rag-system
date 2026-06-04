import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))


from src.vector_store import build_vector_store


def main() -> None:
    print("Building VectorDB from latest RU + UZ document version...")

    result = build_vector_store()

    print("\nГотово.")
    print(f"Version ID: {result['version_id']}")
    print(f"Collection: {result['collection_name']}")
    print(f"Chunks indexed: {result['chunks_indexed']}")
    print(f"Chroma path: {result['chroma_path']}")


if __name__ == "__main__":
    main()
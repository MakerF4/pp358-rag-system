import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DOCUMENTS = {
    "ru": {
        "name": "PP-358-RU",
        "url": "https://lex.uz/ru/docs/7158606?ONDATE=22.11.2025%2000",
    },
    "uz": {
        "name": "PQ-358-UZ",
        "url": "https://lex.uz/uz/docs/7158604?ONDATE=22.11.2025%2000",
    },
}

VERSIONS_DIR = PROJECT_ROOT / os.getenv("VERSIONS_DIR", "data/versions")

RAW_HTML_FILENAME = "raw.html"
CLEAN_TEXT_FILENAME = "clean_text.txt"
CHUNKS_FILENAME = "chunks.json"
TABLES_FILENAME = "tables.json"
METADATA_FILENAME = "metadata.json"
CHANGES_FILENAME = "changes.json"

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

CHROMA_PATH = PROJECT_ROOT / os.getenv("CHROMA_PATH", "data/chroma_db")

CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "pp358_chunks")

TOP_K = int(os.getenv("TOP_K", "5"))

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5.5")
# PP-358 RAG System

Многоязычная RAG-система по Постановлению Президента Республики Узбекистан № ПП-358 о развитии технологий искусственного интеллекта.

Проект автоматически скачивает официальные русскую и узбекскую версии документа с lex.uz, очищает HTML, извлекает юридический текст и таблицы, создаёт смысловые chunks, сохраняет версии документа с hash-значениями, строит VectorDB, выполняет hybrid retrieval и генерирует grounded answers с указанием source chunks через Streamlit UI.

> Примечание: в тексте тестового задания в одном месте указано «№458», однако название задания и ссылка lex.uz относятся к ПП-358. Поэтому в проекте используется документ ПП-358.

---

## Основные возможности

- Загрузка официального документа с lex.uz.
- Поддержка русского и узбекского языков.
- Очистка HTML от служебных элементов сайта.
- Извлечение основного юридического текста.
- Извлечение таблиц из HTML.
- Преобразование строк таблиц в отдельные RAG chunks.
- Разбиение документа по правовой структуре, а не по фиксированному размеру.
- Сохранение версий документа с timestamp и content hash.
- Проверка изменений между версиями документа.
- Индексация chunks в ChromaDB.
- Использование OpenAI embeddings.
- Hybrid retrieval:
  - semantic vector search;
  - lexical search;
  - reranking.
- Генерация ответов только на основе найденных источников.
- Отображение retrieved source chunks в UI.
- Streamlit web interface.
- Кнопка проверки обновлений документа.

---

## Структура проекта

```text
pp358-rag-system/
│
├── app.py
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── scripts/
│   ├── ingest_document.py
│   ├── build_vector_store.py
│   ├── check_updates.py
│   ├── test_retrieval.py
│   └── test_rag.py
│
├── src/
│   ├── config.py
│   ├── scraper.py
│   ├── cleaner.py
│   ├── table_parser.py
│   ├── chunker.py
│   ├── versioning.py
│   ├── change_detector.py
│   ├── vector_store.py
│   ├── retriever.py
│   ├── language.py
│   └── rag.py
│
└── data/
    ├── versions/
    └── chroma_db/
```

---

## Установка

### 1. Создать virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Установить зависимости

```bash
python3 -m pip install -r requirements.txt
```

### 3. Настроить `.env`

Создайте `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

Пример `.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
EMBEDDING_MODEL=text-embedding-3-large
LLM_MODEL=gpt-5.5
CHROMA_PATH=data/chroma_db
CHROMA_COLLECTION_NAME=pp358_chunks
TOP_K=5
```

---

## Используемые модели

В проекте embeddings и LLM разделены.

```text
EMBEDDING_MODEL -> используется для создания векторов chunks
LLM_MODEL       -> используется для генерации финального ответа
```

В локальной версии проекта использовалась LLM:

```env
LLM_MODEL=gpt-5.5
```

Модель не fine-tune-ится. Она используется только на этапе answer generation после retrieval. Архитектура проекта позволяет заменить LLM без изменения кода: достаточно изменить значение `LLM_MODEL` в `.env`.

Например:

```env
LLM_MODEL=your_available_model_name
```

---

## Запуск проекта

### 1. Скачать и обработать документ

```bash
python3 scripts/ingest_document.py
```

Команда скачивает русскую и узбекскую версии документа, очищает HTML, извлекает текст и таблицы, создаёт chunks и сохраняет версию в `data/versions/`.

Пример структуры сохранённой версии:

```text
data/versions/<version_id>/
├── metadata.json
├── ru/
│   ├── raw.html
│   ├── clean_text.txt
│   ├── chunks.json
│   └── tables.json
└── uz/
    ├── raw.html
    ├── clean_text.txt
    ├── chunks.json
    └── tables.json
```

---

### 2. Построить VectorDB

```bash
python3 scripts/build_vector_store.py
```

VectorDB создаётся в:

```text
data/chroma_db/
```

Эта папка не коммитится, потому что её можно пересобрать.

---

### 3. Проверить retrieval

```bash
python3 scripts/test_retrieval.py
```

Скрипт проверяет, какие chunks находятся по русским и узбекским вопросам.

Пример ожидаемого результата:

```text
RU question -> ru_table_0002_row_009
UZ question -> uz_table_0002_row_009
```

---

### 4. Проверить полный RAG pipeline

```bash
python3 scripts/test_rag.py
```

Скрипт проверяет полный процесс:

```text
question
↓
language detection
↓
hybrid retrieval
↓
reranking
↓
LLM answer generation
↓
answer with sources
```

Примеры тестовых вопросов:

```text
Сколько научных лабораторий в сфере искусственного интеллекта должно быть к 2030 году?
```

```text
2030 йилга қадар сунъий интеллект йўналишидаги илмий лабораториялар сони нечта бўлади?
```

```text
Какой кредит выделяется Министерству цифровых технологий для развития искусственного интеллекта?
```

```text
Сунъий интеллект учун катта маълумотлар базаси қачон яратилиши керак?
```

---

### 5. Запустить Streamlit UI

```bash
python3 -m streamlit run app.py
```

После запуска откройте:

```text
http://localhost:8501
```

В UI доступны:

- статус документа;
- текущая версия;
- количество chunks;
- количество таблиц;
- кнопка проверки обновлений;
- поле для вопроса;
- ответ;
- retrieved source chunks.

---

## Архитектура RAG pipeline

```text
lex.uz RU/UZ pages
        ↓
scraper
        ↓
HTML cleaner
        ↓
table parser
        ↓
legal chunker
        ↓
version saving + hashes
        ↓
ChromaDB vector store
        ↓
hybrid retrieval
        ↓
reranking
        ↓
LLM answer generation
        ↓
Streamlit UI
```

---

## Chunking strategy

Документ разбивается не по фиксированному количеству токенов, а по структуре правового документа.

Chunker определяет такие элементы:

```text
1.
2.
а)
б)
Глава
§
Приложение
ИЛОВА
```

Это позволяет сохранять пункты, подпункты, сроки, обязанности и ответственные организации внутри одного смыслового блока.

Таблицы обрабатываются отдельно. Каждая строка таблицы превращается в отдельный `table_row` chunk, потому что строка таблицы обычно содержит завершённую смысловую единицу:

- показатель;
- срок;
- год;
- механизм реализации;
- ответственных исполнителей.

Пример table chunk:

```text
Таблица: Целевые показатели по развитию технологий искусственного интеллекта до 2030 года.
Строка таблицы №9.
Показатели: Научные лаборатории, работающие в сфере искусственного интеллекта.
Единица измерения: кол-во.
2026 год: 6.
2028 год: 8.
2030 год: 10.
Ответственные исполнители: Министерство цифровых технологий, Министерство высшего образования, науки и инноваций.
```

---

## Поддержка русского и узбекского языков

Русская и узбекская версии документа скачиваются и обрабатываются отдельно.

Количество chunks может отличаться между языками. Это нормально, потому что официальные страницы lex.uz могут иметь разную структуру абзацев, разную HTML-разметку и разные языковые формулировки.

Пример:

```text
RU chunks: 206
UZ chunks: 187
Total: 393
```

Это не влияет на retrieval:

```text
русский вопрос -> поиск по RU chunks
узбекский вопрос -> поиск по UZ chunks
```

---

## Table parser

Парсер таблиц является document-aware, но не answer-specific.

Он не содержит готовых ответов на тестовые вопросы. Вместо этого он:

- определяет тип таблицы по официальным заголовкам;
- извлекает строки таблиц;
- нормализует broken HTML rows lex.uz;
- сохраняет разделы action plan;
- превращает каждую строку таблицы в отдельный RAG chunk.

Поддерживаемые типы таблиц:

- целевые показатели до 2030 года;
- план мероприятий на 2024–2026 годы;
- перечень больших данных.

Код не содержит правил типа:

```text
лаборатории = 10
кредит = 50 миллионов
катта маълумотлар = 2025 йил 1 сентябрь
```

Он извлекает структуру документа и делает её удобной для retrieval.

---

## Retrieval strategy

В проекте используется hybrid retrieval:

```text
semantic vector search
+
lexical search
+
reranking
```

### Vector search

Chunks индексируются в ChromaDB с помощью OpenAI embeddings. Для collection используется cosine distance.

### Lexical search

Lexical search помогает находить chunks, где формулировка вопроса близка к юридическому тексту, но vector search может поставить нужный chunk ниже.

### Reranking

Reranker использует общие признаки:

- preference для `table_row` при вопросах про числа и показатели;
- preference для chunks с датами при вопросах про сроки;
- keyword overlap;
- lexical score;
- vector distance.

Reranker не содержит hardcoded answers.

---

## Генерация ответа

LLM получает только retrieved chunks и должен отвечать строго на основе этих источников.

Если ответа в источниках нет, модель должна сообщить, что информация не найдена.

Ответ содержит chunk IDs источников.

Пример:

```text
К 2030 году должно быть 10 научных лабораторий, работающих в сфере искусственного интеллекта.

Использованные источники: ru_table_0002_row_009.
```

---

## Versioning и проверка обновлений

Каждая загруженная версия документа сохраняется отдельно и не перезаписывает предыдущую.

Для каждой версии сохраняются:

- timestamp;
- общий content hash;
- language-specific hashes;
- raw HTML;
- clean text;
- chunks;
- tables;
- metadata.

Проверить обновления можно командой:

```bash
python3 scripts/check_updates.py
```

Update checker:

1. скачивает свежие RU и UZ страницы с lex.uz;
2. очищает документ;
3. создаёт chunks;
4. сравнивает результат с последней сохранённой версией;
5. показывает added, removed, modified и unchanged chunks;
6. сохраняет новую версию только если изменения найдены.

Пример результата:

```text
No changes found.

Added: 0
Removed: 0
Modified: 0
Unchanged: 393
Old total: 393
New total: 393
```

Если изменения найдены, нужно пересобрать VectorDB:

```bash
python3 scripts/build_vector_store.py
```

---

## Почему GitHub показывает HTML 92%

GitHub может показывать проект как преимущественно HTML, потому что в репозитории сохранены файлы `raw.html` внутри папки `data/versions/`.

Эти HTML-файлы являются частью versioning logic. Они сохраняют оригинальный HTML, скачанный с lex.uz, чтобы:

- иметь локальную копию официального источника;
- сравнивать версии документа;
- сохранять историю изменений;
- иметь возможность повторно проверить процесс очистки и парсинга;
- запускать проект даже если lex.uz временно недоступен.

Основная логика проекта написана на Python. Высокий процент HTML в GitHub language statistics связан не с тем, что проект является HTML-приложением, а с тем, что сохранённые версии документа содержат оригинальные HTML-страницы lex.uz.

При необходимости можно исключить `data/versions/` из GitHub language statistics через `.gitattributes`, но в рамках этого проекта папка оставлена в репозитории осознанно, чтобы показать работу versioning и update tracking.

---

## Основные команды

```bash
# Скачать и обработать документы
python3 scripts/ingest_document.py

# Построить VectorDB
python3 scripts/build_vector_store.py

# Проверить retrieval
python3 scripts/test_retrieval.py

# Проверить полный RAG
python3 scripts/test_rag.py

# Проверить обновления lex.uz
python3 scripts/check_updates.py

# Запустить UI
python3 -m streamlit run app.py
```

---

## Git notes

Не нужно коммитить:

```text
.env
.venv/
__pycache__/
*.pyc
data/chroma_db/
```

Папку `data/versions/` можно коммитить, потому что она содержит сохранённую обработанную версию официального документа. Это позволяет проверяющему запустить проект даже если lex.uz временно недоступен.

---

## Ограничения

- Parser адаптирован под структуру lex.uz и документ ПП-358.
- Это document-aware система, а не универсальный parser для всех юридических сайтов.
- После сохранения новой версии документа нужно пересобрать VectorDB.
- Качество ответа зависит от retrieved chunks и выбранной LLM model.
- Модель не fine-tune-ится; используется retrieval-time grounding only.

    В ходе локального тестирования было замечено, что semantic vector search для узбекских вопросов может показывать более слабую точность по сравнению с русскими вопросами. В отдельных тестах качество retrieval для узбекского языка было около 54%.

    Это связано не с логикой RAG pipeline, а с ограничениями multilingual embeddings для низкоресурсных языков и юридических текстов на узбекском языке. Узбекский язык представлен в обучающих данных embedding-моделей слабее, чем русский или английский, поэтому semantic similarity может хуже ранжировать релевантные chunks.

    Чтобы снизить влияние этого ограничения, в проекте используется hybrid retrieval:

    ```text
    semantic vector search
    +
    lexical search
    +
    reranking

---

## Итог

Проект реализует полноценную multilingual RAG-систему для ПП-358. Система поддерживает вопросы на русском и узбекском языках, использует официальные источники lex.uz, извлекает текст и таблицы, сохраняет версии документа, проверяет обновления, выполняет hybrid retrieval с reranking и генерирует grounded answers с указанием source chunks через Streamlit UI.
EOF
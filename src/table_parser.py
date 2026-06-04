import hashlib
import re

from bs4 import BeautifulSoup


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_text(text: str) -> str:
    return " ".join(text.split()).strip()


def _make_unique_headers(headers: list[str]) -> list[str]:
    result = []
    seen = {}

    for index, header in enumerate(headers, start=1):
        if not header:
            header = f"Колонка {index}"

        if header not in seen:
            seen[header] = 1
            result.append(header)
        else:
            seen[header] += 1
            result.append(f"{header}_{seen[header]}")

    return result


def _extract_row_cells(row) -> list[str]:
    cells = row.find_all(["th", "td"])

    return [
        _normalize_text(cell.get_text(" ", strip=True))
        for cell in cells
    ]


def _looks_like_header_row(cells: list[str]) -> bool:
    joined = " ".join(cells).lower()

    header_keywords = [
        # RU
        "№",
        "показатели",
        "наименование",
        "единица",
        "измерения",
        "текущее состояние",
        "ответственные",
        "исполнители",
        "механизм",
        "срок",
        "тип данных",
        "объем данных",
        "периодичность",

        # UZ Cyrillic
        "т/р",
        "кўрсаткичлар",
        "ўлчов бирлиги",
        "амалдаги ҳолат",
        "масъул ижрочилар",
        "чора-тадбирлар номи",
        "амалга ошириш механизми",
        "ижро муддати",
        "маълумотлар тури",
        "маълумотлар ҳажми",
        "янгилаш даврийлиги",
        "рақамли маълумотлар",

        # Common years
        "2026",
        "2028",
        "2030",
    ]

    return any(keyword in joined for keyword in header_keywords)


def _is_noise_title(text: str) -> bool:
    lowered = text.lower()

    noise_phrases = [
        # Latin lex.uz UI
        "hujjatga taklif yuborish",
        "audioni tinglash",
        "hujjat elementidan havola olish",

        # RU lex.uz UI
        "предложения по документу",
        "прослушать аудио",
        "получить ссылку из элемента документа",

        # UZ Cyrillic lex.uz UI
        "ҳужжатга таклиф юбориш",
        "аудиони тинглаш",
        "ҳужжат элементидан ҳавола олиш",
    ]

    return any(phrase in lowered for phrase in noise_phrases)


def _get_table_title(table, table_number: int) -> str:
    title_candidates = []

    previous_elements = table.find_all_previous(
        ["h1", "h2", "h3", "h4", "p", "div"],
        limit=12,
    )

    for element in previous_elements:
        text = _normalize_text(element.get_text(" ", strip=True))

        if not text:
            continue

        if len(text) > 250:
            continue

        if _is_noise_title(text):
            continue

        title_candidates.append(text)

    if title_candidates:
        return title_candidates[0]

    return f"Таблица {table_number}"


def _detect_table_title_from_headers(headers: list[str], fallback_title: str) -> str:
    headers_text = " ".join(headers).lower()

    # RU target indicators
    if (
        "показатели" in headers_text
        and "2026 год" in headers_text
        and "2030 год" in headers_text
    ):
        return "Целевые показатели по развитию технологий искусственного интеллекта до 2030 года"

    # UZ target indicators
    if (
        "кўрсаткичлар" in headers_text
        and "2026 йил" in headers_text
        and "2030 йил" in headers_text
    ):
        return "Сунъий интеллект технологияларини 2030 йилга қадар ривожлантириш бўйича мақсадли кўрсаткичлар"

    # RU action plan
    if (
        "наименование мероприятий" in headers_text
        and "механизм реализации" in headers_text
        and "срок исполнения" in headers_text
    ):
        return (
            "План мероприятий по реализации Стратегии развития технологий "
            "искусственного интеллекта на 2024 — 2026 годы"
        )

    # UZ action plan
    if (
        "чора-тадбирлар номи" in headers_text
        and "амалга ошириш механизми" in headers_text
        and "ижро муддати" in headers_text
    ):
        return (
            "Сунъий интеллект технологияларини ривожлантириш стратегиясини "
            "2024 — 2026 йилларда амалга ошириш бўйича чора-тадбирлар режаси"
        )

    # RU big data list
    if (
        "наименование цифровых данных" in headers_text
        and "тип данных" in headers_text
        and "периодичность обновления" in headers_text
    ):
        return "Перечень больших данных, формируемых в социальной сфере и секторах экономики"

    # UZ big data list
    if (
        "рақамли маълумотлар" in headers_text
        and "маълумотлар тури" in headers_text
        and "янгилаш даврийлиги" in headers_text
    ):
        return "Ижтимоий соҳа ва иқтисодиёт тармоқларида шакллантириладиган «катта маълумотлар» рўйхати"

    return fallback_title


def _find_key(row_data: dict, possible_names: list[str]) -> str | None:
    """
    Finds a column key by partial matching.

    Example:
    possible_names=["№", "т/р"]
    """
    for key in row_data.keys():
        lowered_key = key.lower().strip()

        for possible_name in possible_names:
            lowered_possible = possible_name.lower().strip()

            if lowered_key == lowered_possible:
                return key

            if lowered_possible in lowered_key:
                return key

    return None


def _is_action_plan_table(headers: list[str]) -> bool:
    headers_text = " ".join(headers).lower()

    is_ru_action_plan = (
        "наименование мероприятий" in headers_text
        and "механизм реализации" in headers_text
        and "срок исполнения" in headers_text
        and "ответственные исполнители" in headers_text
    )

    is_uz_action_plan = (
        "чора-тадбирлар номи" in headers_text
        and "амалга ошириш механизми" in headers_text
        and "ижро муддати" in headers_text
        and "масъул ижрочилар" in headers_text
    )

    return is_ru_action_plan or is_uz_action_plan


def _is_uz_action_plan_table(headers: list[str]) -> bool:
    headers_text = " ".join(headers).lower()

    return (
        "чора-тадбирлар номи" in headers_text
        and "амалга ошириш механизми" in headers_text
        and "ижро муддати" in headers_text
    )


def _get_action_plan_keys(row_data: dict) -> dict:
    number_key = _find_key(row_data, ["№", "т/р"])
    event_key = _find_key(row_data, ["наименование мероприятий", "чора-тадбирлар номи"])
    mechanism_key = _find_key(row_data, ["механизм реализации", "амалга ошириш механизми"])
    deadline_key = _find_key(row_data, ["срок исполнения", "ижро муддати"])
    responsible_key = _find_key(row_data, ["ответственные исполнители", "масъул ижрочилар"])

    return {
        "number": number_key,
        "event": event_key,
        "mechanism": mechanism_key,
        "deadline": deadline_key,
        "responsible": responsible_key,
    }


def _is_action_plan_section_row(row_data: dict) -> bool:
    """
    Detects section rows like:

    RU:
    I. Формирование нормативно-правовой базы...

    UZ:
    I. Сунъий интеллект технологияларини ривожлантиришга қаратилган...
    """
    keys = _get_action_plan_keys(row_data)
    number_key = keys["number"]

    if number_key is None:
        return False

    number_value = row_data.get(number_key, "").strip()

    other_values = [
        value.strip()
        for key, value in row_data.items()
        if key != number_key
    ]

    return (
        bool(re.match(r"^[IVX]+\.\s+", number_value))
        and not any(other_values)
    )


def _looks_like_deadline(text: str) -> bool:
    lowered = text.lower().strip()

    deadline_keywords = [
        # RU months
        "январь",
        "февраль",
        "март",
        "апрель",
        "май",
        "июнь",
        "июль",
        "август",
        "сентябрь",
        "октябрь",
        "ноябрь",
        "декабрь",

        # UZ months
        "январь",
        "февраль",
        "март",
        "апрель",
        "май",
        "июнь",
        "июль",
        "август",
        "сентябрь",
        "октябрь",
        "ноябрь",
        "декабрь",

        # Common years/periods
        "2024",
        "2025",
        "2026",
        "2027",
        "2028",
        "ежегодно",
        "начиная",
        "постоянной основе",
        "гг.",
        "год",
        "годы",
        "йил",
        "йиллар",
        "йилдан",
        "доимий",
        "бошлаб",
    ]

    return any(keyword in lowered for keyword in deadline_keywords)


def _is_action_plan_continuation_row(row_data: dict) -> bool:
    """
    Detects broken continuation rows.

    RU example:
    {
        "№": "2. Разработка проекта ...",
        "Наименование мероприятий": "июнь 2025 года",
        "Механизм реализации": "",
        "Срок исполнения": "",
        "Ответственные исполнители": ""
    }

    UZ example:
    {
        "Т/р": "2. Хатлов якуни бўйича ...",
        "Чора-тадбирлар номи": "2025 йил июнь",
        "Амалга ошириш механизми": "",
        "Ижро муддати": "",
        "Масъул ижрочилар": ""
    }
    """
    keys = _get_action_plan_keys(row_data)

    number_key = keys["number"]
    event_key = keys["event"]
    mechanism_key = keys["mechanism"]
    deadline_key = keys["deadline"]
    responsible_key = keys["responsible"]

    if not number_key or not event_key:
        return False

    number_value = row_data.get(number_key, "").strip()
    event_value = row_data.get(event_key, "").strip()
    mechanism_value = row_data.get(mechanism_key, "").strip() if mechanism_key else ""
    deadline_value = row_data.get(deadline_key, "").strip() if deadline_key else ""
    responsible_value = row_data.get(responsible_key, "").strip() if responsible_key else ""

    starts_with_step_text = bool(re.match(r"^\d+\.\s+\S+", number_value))

    return (
        starts_with_step_text
        and event_value
        and _looks_like_deadline(event_value)
        and not mechanism_value
        and not deadline_value
        and not responsible_value
    )


def _normalize_action_plan_rows(rows: list[dict], headers: list[str]) -> tuple[list[dict], list[str]]:
    """
    Cleans the action plan table.

    What it does:
    1. Saves I/II/III/IV rows as section metadata.
    2. Merges broken continuation rows into the previous real event.
    3. Adds section column to every event.
    """
    normalized_rows = []
    current_section = ""

    is_uz_table = _is_uz_action_plan_table(headers)
    section_column = "Бўлим" if is_uz_table else "Раздел"
    deadline_label = "Ижро муддати" if is_uz_table else "Срок исполнения"

    for row_data in rows:
        keys = _get_action_plan_keys(row_data)

        number_key = keys["number"]
        event_key = keys["event"]
        mechanism_key = keys["mechanism"]

        if _is_action_plan_section_row(row_data):
            current_section = row_data.get(number_key, "").strip()
            continue

        if _is_action_plan_continuation_row(row_data):
            if normalized_rows and number_key and event_key and mechanism_key:
                step_text = row_data.get(number_key, "").strip()
                step_deadline = row_data.get(event_key, "").strip()

                if step_deadline.endswith("."):
                    addition = f"{step_text} {deadline_label}: {step_deadline}"
                else:
                    addition = f"{step_text} {deadline_label}: {step_deadline}."

                previous_mechanism = normalized_rows[-1].get(mechanism_key, "").strip()

                if previous_mechanism:
                    normalized_rows[-1][mechanism_key] = previous_mechanism + "\n" + addition
                else:
                    normalized_rows[-1][mechanism_key] = addition

            continue

        row_with_section = {
            section_column: current_section,
            **row_data,
        }

        normalized_rows.append(row_with_section)

    if section_column not in headers:
        headers = [section_column] + headers

    return normalized_rows, headers


def _row_to_rag_text(
    table_title: str,
    row_number: int,
    row_data: dict,
) -> str:
    parts = [
        f"Таблица: {table_title}.",
        f"Строка таблицы №{row_number}.",
    ]

    for column_name, value in row_data.items():
        if value:
            parts.append(f"{column_name}: {value}.")

    return "\n".join(parts)


def parse_tables_from_html(html: str) -> tuple[list[dict], list[dict]]:
    soup = BeautifulSoup(html, "lxml")
    html_tables = soup.find_all("table")

    tables = []
    table_chunks = []

    for table_index, html_table in enumerate(html_tables, start=1):
        rows = html_table.find_all("tr")

        if not rows:
            continue

        extracted_rows = []

        for row in rows:
            cells = _extract_row_cells(row)

            if cells:
                extracted_rows.append(cells)

        if len(extracted_rows) < 2:
            continue

        first_row = extracted_rows[0]

        if _looks_like_header_row(first_row):
            headers = _make_unique_headers(first_row)
            data_rows = extracted_rows[1:]
        else:
            max_columns = max(len(row) for row in extracted_rows)
            headers = [f"Колонка {i}" for i in range(1, max_columns + 1)]
            data_rows = extracted_rows

        fallback_title = _get_table_title(html_table, table_index)
        table_title = _detect_table_title_from_headers(headers, fallback_title)

        table_id = f"table_{table_index:04d}"

        structured_rows = []

        for row_cells in data_rows:
            row_data = {}

            for column_index, header in enumerate(headers):
                value = row_cells[column_index] if column_index < len(row_cells) else ""
                row_data[header] = value

            if not any(row_data.values()):
                continue

            structured_rows.append(row_data)

        if not structured_rows:
            continue

        if _is_action_plan_table(headers):
            structured_rows, headers = _normalize_action_plan_rows(
                rows=structured_rows,
                headers=headers,
            )

        for row_index, row_data in enumerate(structured_rows, start=1):
            rag_text = _row_to_rag_text(
                table_title=table_title,
                row_number=row_index,
                row_data=row_data,
            )

            table_chunk = {
                "chunk_id": f"{table_id}_row_{row_index:03d}",
                "section": f"{table_title} — строка {row_index}",
                "type": "table_row",
                "text": rag_text,
                "hash": _hash_text(rag_text),
                "table_id": table_id,
                "row_number": row_index,
            }

            table_chunks.append(table_chunk)

        table_data = {
            "table_id": table_id,
            "title": table_title,
            "headers": headers,
            "rows": structured_rows,
            "rows_count": len(structured_rows),
        }

        tables.append(table_data)

    return tables, table_chunks
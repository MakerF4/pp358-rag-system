import re

from bs4 import BeautifulSoup


NOISE_LINES = {
    # RU lex.uz UI
    "Все",
    "Ссылка на последующую редакцию",
    "Ссылка на предыдущую редакцию",
    "Индексация по ОКОЗ",
    "Индексация по ТСЗ",
    "Источники изменений",
    "Источники опубликования",
    "Текущая версия",
    "Вид",
    "Предложения по документу",
    "Прослушать аудио",
    "Получить ссылку из элемента документа",
    "Перейти на действующую версию",
    "См.",
    "предыдущую",
    "редакцию.",

    # UZ Cyrillic lex.uz UI
    "Ўзб|Рус",
    "Рус|Ўзб",
    "Ҳаммаси",
    "Амалдаги версияга ўтиш",
    "Кейинги таҳрирга ҳавола",
    "Олдинги таҳрирга ҳавола",
    "Олдинги",
    "Кейинги",
    "таҳрирга қаранг.",
    "Ҳужжатга таклиф юбориш",
    "Аудиони тинглаш",
    "Ҳужжат элементидан ҳавола олиш",

    # UZ Latin lex.uz UI
    "Hammasi",
    "Keyingi tahrirga havola",
    "Oldingi tahrirga havola",
    "QTUK bo‘yicha indekslash",
    "QMQ bo‘yicha indekslash",
    "O‘zgartirishlar manbasi",
    "Rasmiy nashr manbasi",
    "Joriy versiya",
    "Ko‘rinish",
    "Hujjatga taklif yuborish",
    "Audioni tinglash",
    "Hujjat elementidan havola olish",

    # Language buttons
    "A",
    "Рус",
    "Eng",
    "Ўзб",
    "O’zb",
    "O'z",
    "O‘z",
    "Рус|O‘zb",
}


NOISE_PREFIXES = (
    "Акт на состоянии",
    "Ҳужжат ",
)


def _normalize_line(line: str) -> str:
    return " ".join(line.split()).strip()


def _is_standalone_date(line: str) -> bool:
    return bool(re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", line))


def _is_noise_line(line: str) -> bool:
    if not line:
        return True

    if line in NOISE_LINES:
        return True

    if _is_standalone_date(line):
        return True

    # Russian lex.uz status line
    if line.startswith("Акт на состоянии"):
        return True

    # Uzbek lex.uz status line
    if line.startswith("Ҳужжат ") and "санаси ҳолатига" in line:
        return True

    return False


def _remove_classifier_blocks(lines: list[str]) -> list[str]:
    """
    Removes technical classifier blocks like ОКОЗ/ТСЗ.
    """
    cleaned_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        is_classifier_start = (
            line == "["
            and i + 1 < len(lines)
            and lines[i + 1] in {"ОКОЗ:", "ТСЗ:"}
        )

        if is_classifier_start:
            i += 1

            while i < len(lines):
                if lines[i].endswith("]"):
                    i += 1
                    break

                i += 1

            continue

        cleaned_lines.append(line)
        i += 1

    return cleaned_lines


def clean_html_to_text(html: str) -> str:
    """
    Extracts clean legal text from lex.uz HTML.

    Works for both:
    - Russian PP-358 page
    - Uzbek PQ-358 page
    """
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()

    candidates = soup.find_all(
        ["main", "article", "section", "div"],
        class_=lambda class_name: class_name
        and any(
            keyword in str(class_name).lower()
            for keyword in [
                "doc",
                "document",
                "content",
                "article",
                "text",
                "law",
                "lex",
            ]
        ),
    )

    if candidates:
        main_content = max(
            candidates,
            key=lambda element: len(element.get_text(" ", strip=True)),
        )
    else:
        main_content = soup.body or soup

    raw_text = main_content.get_text("\n", strip=True)

    normalized_lines = []

    for raw_line in raw_text.splitlines():
        line = _normalize_line(raw_line)

        if _is_noise_line(line):
            continue

        normalized_lines.append(line)

    cleaned_lines = _remove_classifier_blocks(normalized_lines)

    clean_text = "\n".join(cleaned_lines)

    if not clean_text.strip():
        raise ValueError("После очистки HTML текст документа оказался пустым.")

    return clean_text
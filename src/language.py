def detect_question_language(question: str) -> str:
    """
    Very simple RU / UZ detector.

    Returns:
        "uz" or "ru"
    """
    lowered = question.lower()

    uz_markers = [
        "ў",
        "қ",
        "ғ",
        "ҳ",
        "нинг",
        "учун",
        "қанча",
        "нечта",
        "йил",
        "кўрсаткич",
        "масъул",
    ]

    for marker in uz_markers:
        if marker in lowered:
            return "uz"

    return "ru"
import requests


def fetch_document_html(url: str) -> str:
    """
    Скачивает HTML-страницу документа с lex.uz.

    Args:
        url: Ссылка на документ lex.uz.

    Returns:
        HTML страницы в виде строки.

    Raises:
        requests.HTTPError: Если сервер вернул ошибку.
        requests.RequestException: Если произошла ошибка сети.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9,uz;q=0.8,en;q=0.7",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(f"Не удалось скачать документ с lex.uz: {error}") from error

    return response.text
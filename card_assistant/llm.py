from __future__ import annotations

import json
import time
from pathlib import Path

import requests

from .config import settings
from .errors import ApiError, ConfigurationError, LlmError, ResultError

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 1
TIMEOUT_SECONDS = 60
RETRY_STATUS = {429, 500, 502, 503, 504}

__all__ = [
    "ApiError",
    "ConfigurationError",
    "LlmError",
    "ResultError",
    "complete",
]


with (Path(__file__).parents[1] / "prompts" / "system_ru.md").open(encoding="utf8") as stream:
    SYSTEM = stream.read()


def _parse_response(response: requests.Response) -> dict:
    """Validate the API envelope and the JSON card returned by the model."""
    try:
        payload = response.json()
    except ValueError as exc:
        raise ResultError("API вернул не-JSON ответ") from exc
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ResultError("API вернул ответ без choices[0].message.content") from exc
    if not isinstance(content, str):
        raise ResultError("Модель вернула не текст")
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ResultError(f"Модель вернула невалидный JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ResultError("Модель вернула JSON, который не является объектом")
    return data


def _raise_status_error(status: int, response: requests.Response) -> None:
    """Map non-retryable HTTP statuses to distinct, actionable messages."""
    if status == 401:
        raise ApiError("Неверный API-ключ: проверьте OPENAI_API_KEY")
    if status == 400:
        raise ApiError("Неверная модель или endpoint: проверьте OPENAI_MODEL и OPENAI_BASE_URL")
    if status == 403:
        raise ApiError("Нет доступа к API (403): проверьте права ключа, модель и прокси")
    if status == 404:
        raise ApiError("Endpoint не найден: проверьте OPENAI_BASE_URL")
    if 400 <= status < 500:
        raise ApiError(f"Ошибка API: HTTP {status}")
    raise ApiError(f"Неожиданный ответ API: HTTP {status}: {response.text[:200]}")


def complete(payload: dict, feedback: list[str] | None = None) -> dict:
    """Call the chat-completions endpoint with bounded retries.

    Only rate limits, 5xx responses and network timeouts are retried. Auth,
    model/endpoint and access errors fail immediately with a distinct message;
    malformed model output is a result-validation error (exit code 5).
    """
    cfg = settings()
    if not cfg.api_key or not cfg.model:
        raise ConfigurationError(
            "Не задан OPENAI_API_KEY или OPENAI_MODEL. Заполните .env по примеру .env.example"
        )
    body = {
        "model": cfg.model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": "Данные товара (недоверенный JSON):\n"
                + json.dumps(payload, ensure_ascii=False)
                + ("\nИсправь: " + "; ".join(feedback) if feedback else ""),
            },
        ],
    }
    if "deepseek" in cfg.base_url.lower():
        body["thinking"] = {"type": "disabled"}
    last_attempt = MAX_ATTEMPTS - 1
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.post(
                cfg.base_url + "/chat/completions",
                headers={
                    "Authorization": f"Bearer {cfg.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=TIMEOUT_SECONDS,
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            if attempt == last_attempt:
                raise ApiError(f"Нет доступа к сети или прокси: {exc}") from exc
            time.sleep(BACKOFF_SECONDS * 2**attempt)
            continue
        except requests.RequestException as exc:
            raise ApiError(f"Ошибка сети или прокси: {exc}") from exc

        status = response.status_code
        if status in RETRY_STATUS:
            if attempt == last_attempt:
                raise ApiError(
                    f"API временно недоступен (HTTP {status}) после {MAX_ATTEMPTS} попыток"
                )
            time.sleep(BACKOFF_SECONDS * 2**attempt)
            continue
        if not 200 <= status < 300:
            _raise_status_error(status, response)
        return _parse_response(response)
    raise AssertionError("unreachable")

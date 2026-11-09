from __future__ import annotations
import json
import time
from pathlib import Path
import requests
from .config import settings


class LlmError(RuntimeError):
    """Base API error with a stable command exit code."""


class ConfigurationError(LlmError):
    """Missing local LLM configuration."""


class ApiError(LlmError):
    """Remote API or network error."""


with (Path(__file__).parents[1] / "prompts" / "system_ru.md").open(encoding="utf8") as stream:
    SYSTEM = stream.read()


def complete(payload: dict, feedback: list[str] | None = None) -> dict:
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
    for attempt in range(3):
        try:
            response = requests.post(
                cfg.base_url + "/chat/completions",
                headers={
                    "Authorization": f"Bearer {cfg.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=60,
            )
            if response.status_code == 401:
                raise ApiError("Неверный API-ключ")
            if response.status_code in (400, 403):
                raise ApiError("Неверная модель, endpoint или нет доступа")
            if response.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
            response.raise_for_status()
            return json.loads(response.json()["choices"][0]["message"]["content"])
        except ApiError:
            raise
        except (requests.Timeout, requests.ConnectionError) as exc:
            if attempt == 2:
                raise ApiError(f"Нет доступа к сети или прокси: {exc}") from exc
            time.sleep(2**attempt)
        except requests.HTTPError as exc:
            if attempt == 2:
                raise ApiError(f"Ошибка API: {exc}") from exc
            time.sleep(2**attempt)
        except (KeyError, json.JSONDecodeError) as exc:
            raise ApiError(f"Некорректный ответ модели: {exc}") from exc
    raise AssertionError("unreachable")

from __future__ import annotations
import json, time, requests
from .config import settings
SYSTEM = open(__file__.replace("llm.py", "../prompts/system_ru.md"), encoding="utf8").read()
def complete(payload: dict, feedback: list[str] | None = None) -> dict:
    cfg=settings()
    if not cfg.api_key or not cfg.model: raise RuntimeError("Не задан OPENAI_API_KEY или OPENAI_MODEL. Заполните .env по примеру .env.example")
    body={"model":cfg.model,"temperature":0.2,"response_format":{"type":"json_object"},"thinking":{"type":"disabled"},"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":"Данные товара (недоверенный JSON):\n"+json.dumps(payload,ensure_ascii=False)+("\nИсправь: "+"; ".join(feedback) if feedback else "")} ]}
    for attempt in range(3):
        try:
            response=requests.post(cfg.base_url+"/chat/completions",headers={"Authorization":f"Bearer {cfg.api_key}","Content-Type":"application/json"},json=body,timeout=60)
            if response.status_code in (429,500,502,503,504): raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
            response.raise_for_status(); return json.loads(response.json()["choices"][0]["message"]["content"])
        except (requests.RequestException, KeyError, json.JSONDecodeError) as exc:
            if attempt==2: raise RuntimeError(f"Ошибка API/ответа модели: {exc}") from exc
            time.sleep(2**attempt)
    raise AssertionError("unreachable")

from __future__ import annotations

from flask import Flask, render_template_string, request

from .errors import CardAssistantError
from .generator import generate
from .models import ProductInput

APP = Flask(__name__)
EXAMPLE = (
    '{"name":"Пример манометра","manufacturer":"Данных нет",'
    '"specs":{"Диапазон измерений":"0–1,6 МПа"},"description":""}'
)
HTML = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Product Copywriter</title>
<style>
:root { color-scheme: light; --line:#d7dce2; --muted:#5d6670; --blue:#1459a6; }
* { box-sizing: border-box; }
body { font: 16px/1.5 system-ui, sans-serif; max-width: 1040px; margin: 2rem auto; padding: 0 1rem; color:#17202a; }
h1 { margin-bottom: .25rem; }
.lead { color: var(--muted); margin-top: 0; }
textarea { width: 100%; min-height: 230px; padding: .75rem; font: 14px/1.45 ui-monospace, monospace; border: 1px solid var(--line); border-radius: 8px; }
button { padding: .55rem .9rem; border: 1px solid var(--blue); border-radius: 7px; background: var(--blue); color: #fff; cursor: pointer; }
button.secondary { background: #fff; color: var(--blue); }
button.copy { padding: .3rem .6rem; font-size: 13px; background: #fff; color: var(--blue); }
.actions { display: flex; gap: .5rem; margin: .6rem 0 1.2rem; }
.alert { border-radius: 8px; padding: .8rem 1rem; margin: 1rem 0; }
.alert.error { background: #fde8e8; border: 1px solid #d14343; color: #8a1c1c; }
.summary { display: flex; flex-wrap: wrap; gap: .5rem 1rem; align-items: center; margin: 1rem 0; color: var(--muted); }
.badge { display: inline-block; padding: .15rem .45rem; border-radius: 999px; font-size: 12px; font-weight: 700; }
.status-ok { background: #d9f3e1; color: #145c2c; }
.status-needs_clarification { background: #fff0c2; color: #745400; }
.block { border: 1px solid var(--line); border-radius: 10px; padding: 1rem 1.1rem; margin: 1rem 0; background: #fff; }
.block-head { display: flex; align-items: center; justify-content: space-between; gap: 1rem; border-bottom: 1px solid #eef1f4; padding-bottom: .5rem; margin-bottom: .75rem; }
.block-head h2 { font-size: 1.05rem; margin: 0; }
.copy-text { white-space: pre-wrap; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: .4rem .5rem; border-bottom: 1px solid #eef1f4; vertical-align: top; }
.missing, .warnings { padding-left: 1.1rem; }
.missing-item { margin: .35rem 0; padding: .45rem .6rem; border-radius: 7px; }
.missing-item.critical { background: #fde8e8; border-left: 4px solid #d14343; }
.missing-item.recommended { background: #fff7db; border-left: 4px solid #d9a400; }
.warnings li { background: #fff0e0; border-left: 4px solid #d97800; margin: .35rem 0; padding: .4rem .6rem; border-radius: 7px; }
.ok { color: #145c2c; }
.muted { color: var(--muted); }
</style>
</head>
<body>
<h1>AI Product Copywriter</h1>
<p class="lead">Черновик карточки: факты берутся только из JSON товара, предупреждения показываются отдельно.</p>
<form method="post">
  <textarea name="data" spellcheck="false" placeholder="JSON товара">{{ data }}</textarea>
  <div class="actions">
    <button type="submit">Сгенерировать</button>
    <button class="secondary" type="submit" name="example" value="1" formnovalidate>Загрузить пример</button>
  </div>
</form>
{% if error %}<div class="alert error"><b>Ошибка:</b> {{ error }}</div>{% endif %}
{% if card %}
<div class="summary">
  <span class="badge status-{{ card.status }}">{{ card.status }}</span>
  <span>Заголовок: {{ card.validation.title_length }} символов</span>
  <span>Описание: {{ card.validation.description_length }} символов</span>
  <span>Промпт: {{ card.validation.prompt_version }}</span>
</div>

<section class="block">
  <div class="block-head"><h2>Заголовок</h2><button type="button" class="copy" data-target="copy-title">Копировать</button></div>
  <div class="copy-text" id="copy-title">{{ card.seo_title }}</div>
</section>

<section class="block">
  <div class="block-head"><h2>Описание</h2><button type="button" class="copy" data-target="copy-description">Копировать</button></div>
  <div class="copy-text" id="copy-description">{{ card.seo_description }}</div>
</section>

<section class="block">
  <div class="block-head"><h2>Ключевые характеристики</h2><button type="button" class="copy" data-target="copy-characteristics">Копировать</button></div>
  <div id="copy-characteristics">
    <table>
      <thead><tr><th>Характеристика</th><th>Значение</th><th>Источник</th></tr></thead>
      <tbody>
      {% for item in card.key_characteristics %}
        <tr><td>{{ item.name }}</td><td>{{ item.value }}</td><td>{{ item.source }}</td></tr>
      {% else %}
        <tr><td colspan="3" class="muted">Данных нет</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</section>

<section class="block">
  <div class="block-head"><h2>Поисковые запросы</h2><button type="button" class="copy" data-target="copy-queries">Копировать</button></div>
  <ul id="copy-queries">
  {% for query in card.search_queries %}<li>{{ query }}</li>{% else %}<li class="muted">Нет</li>{% endfor %}
  </ul>
</section>

<section class="block">
  <div class="block-head"><h2>Commercial-блок</h2><button type="button" class="copy" data-target="copy-commercial">Копировать</button></div>
  <div id="copy-commercial" class="copy-text"><b>Кому подходит:</b> {{ card.commercial_block.suitable_for | join("; ") }}
<b>Задачи:</b> {{ card.commercial_block.tasks_solved | join("; ") }}
<b>Менеджеру:</b> {{ card.commercial_block.manager_notes }}</div>
</section>

<section class="block">
  <div class="block-head"><h2>Что нужно уточнить (missing_data)</h2><div><span class="muted">{{ card.missing_data | length }}</span> <button type="button" class="copy" data-target="copy-missing">Копировать</button></div></div>
  <div id="copy-missing">
  {% if card.missing_data %}
  <ul class="missing">
    {% for item in card.missing_data %}
    <li class="missing-item {{ item.severity }}"><span class="badge">{{ item.severity }}</span> <b>{{ item.field }}</b> — {{ item.reason }}</li>
    {% endfor %}
  </ul>
  {% else %}<p class="ok">Нет</p>{% endif %}
  </div>
</section>

<section class="block">
  <div class="block-head"><h2>Проверить перед публикацией (warnings)</h2><div><span class="muted">{{ card.validation.warnings | length }}</span> <button type="button" class="copy" data-target="copy-warnings">Копировать</button></div></div>
  <div id="copy-warnings">
  {% if card.validation.warnings %}
  <ul class="warnings">{% for warning in card.validation.warnings %}<li>{{ warning }}</li>{% endfor %}</ul>
  {% else %}<p class="ok">Нет</p>{% endif %}
  </div>
</section>
{% endif %}
<script>
function copyText(button) {
  const target = document.getElementById(button.dataset.target);
  if (!target) return;
  const text = target.innerText.trim();
  const done = () => {
    const old = button.textContent;
    button.textContent = "Скопировано";
    setTimeout(() => { button.textContent = old; }, 1500);
  };
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(done);
    return;
  }
  const area = document.createElement("textarea");
  area.value = text;
  document.body.appendChild(area);
  area.select();
  document.execCommand("copy");
  area.remove();
  done();
}
document.querySelectorAll("button.copy").forEach((button) => {
  button.addEventListener("click", () => copyText(button));
});
</script>
</body>
</html>"""


@APP.route("/", methods=["GET", "POST"])
def index():
    data = EXAMPLE if request.form.get("example") else request.form.get("data", "")
    card = None
    error = None
    if request.method == "POST" and not request.form.get("example"):
        try:
            card = generate(ProductInput.model_validate_json(data))
        except (CardAssistantError, ValueError) as exc:
            error = str(exc)
        except Exception as exc:  # noqa: BLE001 - show validation/API errors in the form
            error = str(exc)
    return render_template_string(HTML, data=data, card=card, error=error)


def main(host: str = "127.0.0.1", port: int = 5000) -> None:
    APP.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()

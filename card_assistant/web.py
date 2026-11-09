from flask import Flask, request, render_template_string
from .models import ProductInput
from .generator import generate
from .render import markdown

APP = Flask(__name__)
HTML = """<!doctype html><meta charset="utf-8"><title>AI Product Copywriter</title><style>body{font:16px system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem}textarea{width:100%;height:280px}button{padding:.7rem;margin:.5rem 0}.warn{background:#fff3cd;padding:1rem;white-space:pre-wrap}</style><h1>AI Product Copywriter</h1><form method=post><textarea name=data placeholder='JSON товара'>{{ data }}</textarea><br><button>Сгенерировать</button> <button name=example value=1>Загрузить пример</button></form>{% if error %}<div class=warn>{{error}}</div>{% endif %}{% if result %}<pre>{{result}}</pre>{% endif %}"""
EXAMPLE = '{"name":"Пример манометра","manufacturer":"Данных нет","specs":{"Диапазон измерений":"0–1,6 МПа"},"description":""}'


@APP.route("/", methods=["GET", "POST"])
def index():
    data = EXAMPLE if request.form.get("example") else request.form.get("data", "")
    if request.method == "POST" and not request.form.get("example"):
        try:
            return render_template_string(
                HTML, data=data, result=markdown(generate(ProductInput.model_validate_json(data)))
            )
        except Exception as exc:
            return render_template_string(HTML, data=data, error=str(exc))
    return render_template_string(HTML, data=data)


def main():
    APP.run(host="127.0.0.1", port=5000, debug=False)

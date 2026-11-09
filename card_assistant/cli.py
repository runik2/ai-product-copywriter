from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from pydantic import ValidationError

from .checks import blocking_warnings, check
from .errors import CardAssistantError, InputError
from .feed import enrich_from_page, fetch, fetch_page_jsonld, parse, pick
from .generator import generate
from .models import Card, ProductInput
from .render import save


def product_file(path: Path) -> ProductInput:
    try:
        return ProductInput.model_validate_json(path.read_text(encoding="utf8"))
    except (OSError, ValidationError, ValueError) as exc:
        raise InputError(f"Некорректный входной JSON {path}: {exc}") from exc


def cmd_feed(args) -> int:
    if args.action == "fetch":
        fetch(args.url, Path(args.out))
        print(f"Фид сохранён: {args.out}")
        return 0
    chosen = pick(parse(Path(args.feed)), args.ids.split(",") if args.ids else None)
    out = Path(args.out)
    raw_dir = out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    xml = Path(args.feed).read_text(encoding="utf8", errors="ignore")
    for index, product in enumerate(chosen, 1):
        if args.enrich:
            data = fetch_page_jsonld(product.url)
            if data:
                (raw_dir / f"product_{index}.page.json").write_text(
                    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf8"
                )
                product = enrich_from_page(product, data)
        (out / f"product_{index}.json").write_text(
            product.model_dump_json(indent=2), encoding="utf8"
        )
        raw = re.search(
            rf'<offer\b[^>]*\bid="{re.escape(product.offer_id)}"[^>]*>[\s\S]*?</offer>', xml
        )
        if raw:
            (raw_dir / f"product_{index}.xml").write_text(raw.group(0), encoding="utf8")
    print("Выбраны: " + ", ".join(p.name for p in chosen))
    return 0


def cmd_generate(args) -> int:
    cards: list[Card] = []
    codes: list[int] = []
    for item in args.inputs:
        label = Path(item).name
        try:
            product = product_file(Path(item))
            card = generate(product, args.dry_run)
        except CardAssistantError as exc:
            print(f"{label}: ошибка: {exc}", file=sys.stderr)
            codes.append(exc.exit_code)
            continue
        blocking = [] if args.dry_run else blocking_warnings(card.validation.warnings)
        codes.append(5 if blocking else 0)
        cards.append(card)
        print(
            f"{label}: {card.status}; предупреждений: {len(card.validation.warnings)}; "
            f"код: {codes[-1]}"
        )
        for warning in card.validation.warnings:
            print(f"  - {warning}")
    if cards:
        save(cards, Path(args.out), args.format)
    return max(codes) if codes else 0


def _load_sources(folder: Path = Path("examples/inputs")) -> list[ProductInput]:
    sources: list[ProductInput] = []
    for path in sorted(folder.glob("product_*.json")):
        try:
            sources.append(product_file(path))
        except CardAssistantError:
            continue
    return sources


def cmd_check(args) -> int:
    code = 0
    sources = _load_sources()
    for path in sorted(Path(args.out).glob("*.json")):
        try:
            card = Card.model_validate_json(path.read_text(encoding="utf8"))
        except (OSError, ValidationError, ValueError) as exc:
            print(f"{path.name}: ошибка: {exc}")
            code = max(code, 2)
            continue
        source = next(
            (item for item in sources if item.offer_id == card.source.get("offer_id")),
            None,
        )
        if source is None:
            print(f"{path.name}: ошибка: не найден исходный товар")
            code = max(code, 2)
            continue
        warnings = check(card, source)
        blocking = blocking_warnings(warnings)
        state = "OK" if not blocking else "; ".join(blocking)
        print(f"{path.name}: {state}")
        if blocking:
            code = max(code, 5)
    return code


def cmd_serve(args) -> int:
    from .web import main as web_main

    web_main(host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m card_assistant", description="Черновики товарных карточек КИП"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    feed = sub.add_parser("feed")
    fsub = feed.add_subparsers(dest="action", required=True)
    ff = fsub.add_parser("fetch")
    ff.add_argument("--url", default="https://www.souz-pribor.ru/yml/any/feed.xml")
    ff.add_argument("--out", default="data/feed.xml")
    fp = fsub.add_parser("pick")
    fp.add_argument("--feed", default="data/feed.xml")
    fp.add_argument("--ids")
    fp.add_argument("--enrich", action="store_true")
    fp.add_argument("--out", default="examples/inputs")
    gen = sub.add_parser("generate")
    gen.add_argument("inputs", nargs="+")
    gen.add_argument("--out", default="examples/outputs")
    gen.add_argument("--format", choices=("md", "json", "both"), default="both")
    gen.add_argument("--dry-run", action="store_true")
    gen.add_argument("--debug", action="store_true")
    checkp = sub.add_parser("check")
    checkp.add_argument("out", nargs="?", default="examples/outputs")
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=5000)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "feed":
            return cmd_feed(args)
        if args.command == "generate":
            return cmd_generate(args)
        if args.command == "check":
            return cmd_check(args)
        return cmd_serve(args)
    except CardAssistantError as exc:
        if getattr(args, "debug", False):
            raise
        print(f"Ошибка: {exc}", file=sys.stderr)
        return exc.exit_code
    except (OSError, ValidationError, ValueError) as exc:
        if getattr(args, "debug", False):
            raise
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

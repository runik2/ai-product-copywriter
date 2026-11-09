from __future__ import annotations
import argparse
import sys
import re
from pathlib import Path
from pydantic import ValidationError
from .feed import enrich_from_page, fetch, parse, pick
from .models import ProductInput, Card
from .generator import generate
from .checks import check
from .render import save


def product_file(path: Path) -> ProductInput:
    try:
        return ProductInput.model_validate_json(path.read_text(encoding="utf8"))
    except (OSError, ValidationError, ValueError) as exc:
        raise RuntimeError(f"Некорректный входной JSON {path}: {exc}") from exc


def cmd_feed(args):
    if args.action == "fetch":
        fetch(args.url, Path(args.out))
        print(f"Фид сохранён: {args.out}")
        return 0
    chosen = pick(parse(Path(args.feed)), args.ids.split(",") if args.ids else None)
    chosen[0] = enrich_from_page(chosen[0])
    out = Path(args.out)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    xml = Path(args.feed).read_text(encoding="utf8", errors="ignore")
    for i, p in enumerate(chosen, 1):
        (out / f"product_{i}.json").write_text(p.model_dump_json(indent=2), encoding="utf8")
        raw = re.search(rf'<offer\b[^>]*\bid="{re.escape(p.offer_id)}"[^>]*>[\s\S]*?</offer>', xml)
        if raw:
            (out / "raw" / f"product_{i}.xml").write_text(raw.group(0), encoding="utf8")
    print("Выбраны: " + ", ".join(p.name for p in chosen))
    return 0


def cmd_generate(args):
    cards = [generate(product_file(Path(item)), args.dry_run) for item in args.inputs]
    save(cards, Path(args.out), args.format)
    for card in cards:
        print(
            f"{card.product_name}: {card.status}; предупреждений: {len(card.validation.warnings)}"
        )
    return 0


def cmd_check(args):
    code = 0
    sources = [product_file(path) for path in Path("examples/inputs").glob("product_*.json")]
    for path in Path(args.out).glob("*.json"):
        try:
            card = Card.model_validate_json(path.read_text(encoding="utf8"))
            source = next(p for p in sources if p.offer_id == card.source.get("offer_id"))
            warnings = check(card, source)
            print(f"{path.name}: {'OK' if not warnings else '; '.join(warnings)}")
            code |= bool(warnings)
        except (ValidationError, RuntimeError) as exc:
            print(f"{path.name}: ошибка: {exc}")
            code = 1
    return int(code)


def main(argv=None):
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
    fp.add_argument("--out", default="examples/inputs")
    gen = sub.add_parser("generate")
    gen.add_argument("inputs", nargs="+")
    gen.add_argument("--out", default="examples/outputs")
    gen.add_argument("--format", choices=("md", "json", "both"), default="both")
    gen.add_argument("--dry-run", action="store_true")
    gen.add_argument("--debug", action="store_true")
    checkp = sub.add_parser("check")
    checkp.add_argument("out", nargs="?", default="examples/outputs")
    args = parser.parse_args(argv)
    try:
        return (
            cmd_feed(args)
            if args.command == "feed"
            else cmd_generate(args)
            if args.command == "generate"
            else cmd_check(args)
        )
    except Exception as exc:
        if getattr(args, "debug", False):
            raise
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

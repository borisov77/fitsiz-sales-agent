"""Быстрый sanity-test парсера входящих писем.

Запуск (без pytest):
    python -m scripts.test_email_parser
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.email_parser import clean_reply_text, parse  # noqa: E402


RAW_RU = b"""\
Return-Path: <sergey@svarmontazh-ufa.ru>
From: "\xd0\x98\xd0\xb2\xd0\xb0\xd0\xbd\xd0\xbe\xd0\xb2 \xd0\xa1\xd0\xb5\xd1\x80\xd0\xb3\xd0\xb5\xd0\xb9" <sergey@svarmontazh-ufa.ru>
To: sales@fitsiz.ru
Subject: =?UTF-8?B?UmU6INCf0YDQvtC00YPQutGG0LjRjyBGSVRTSVo=?=
Message-ID: <reply-12345@svarmontazh-ufa.ru>
In-Reply-To: <abc-initial@fitsiz.ru>
References: <abc-initial@fitsiz.ru>
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: 8bit

\xd0\x94\xd0\xbe\xd0\xb1\xd1\x80\xd1\x8b\xd0\xb9 \xd0\xb4\xd0\xb5\xd0\xbd\xd1\x8c!

\xd0\x9f\xd1\x80\xd0\xb8\xd1\x88\xd0\xbb\xd0\xb8\xd1\x82\xd0\xb5 \xd0\xbf\xd1\x80\xd0\xb0\xd0\xb9\xd1\x81, \xd0\xb8\xd0\xbd\xd1\x82\xd0\xb5\xd1\x80\xd0\xb5\xd1\x81\xd1\x83\xd0\xb5\xd1\x82 FSC-\xd0\xa1777.

--
\xd0\x98\xd0\xb2\xd0\xb0\xd0\xbd\xd0\xbe\xd0\xb2 \xd0\xa1\xd0\xb5\xd1\x80\xd0\xb3\xd0\xb5\xd0\xb9
\xd0\xa1\xd0\xb2\xd0\xb0\xd1\x80\xd0\x9c\xd0\xbe\xd0\xbd\xd1\x82\xd0\xb0\xd0\xb6

15.04.2026 10:30, \xd0\x92\xd0\xbb\xd0\xb0\xd0\xb4\xd0\xb8\xd0\xbc\xd0\xb8\xd1\x80 FITSIZ \xd0\xbf\xd0\xb8\xd1\x81\xd0\xb0\xd0\xbb:
> \xd0\x94\xd0\xbe\xd0\xb1\xd1\x80\xd1\x8b\xd0\xb9 \xd0\xb4\xd0\xb5\xd0\xbd\xd1\x8c!
> \xd0\x9d\xd0\xb0\xd0\xbf\xd0\xb8\xd1\x88\xd0\xb8\xd1\x82\xd0\xb5 \xd0\xbd\xd0\xb0\xd1\x81...
"""


def test_parse_ru_reply() -> None:
    parsed = parse(RAW_RU)
    assert parsed.from_address == "sergey@svarmontazh-ufa.ru", parsed.from_address
    assert parsed.in_reply_to == "<abc-initial@fitsiz.ru>", parsed.in_reply_to
    assert parsed.subject.startswith("Re:"), parsed.subject
    assert "FSC-С777" in parsed.body_text, parsed.body_text
    # Подпись и цитата должны быть срезаны
    assert "СварМонтаж" not in parsed.body_text_clean, parsed.body_text_clean
    assert "писал" not in parsed.body_text_clean.lower(), parsed.body_text_clean
    assert "Добрый день" in parsed.body_text_clean, parsed.body_text_clean
    assert "Пришлите прайс" in parsed.body_text_clean, parsed.body_text_clean
    print("[OK] parse RU reply → clean body:")
    print(parsed.body_text_clean)


def test_clean_inline_quotes() -> None:
    text = (
        "Ок, берём 10 штук.\n"
        "\n"
        "> мы работаем с FUBAG\n"
        "> и не хотим менять\n"
        "\n"
        "Спасибо!\n"
    )
    cleaned = clean_reply_text(text)
    assert ">" not in cleaned, cleaned
    assert "Ок, берём 10 штук." in cleaned
    # После блока цитат парсер останавливается — это ожидаемо
    print("[OK] inline quotes stripped →", repr(cleaned))


def test_clean_english_reply() -> None:
    text = (
        "Sounds good, let's talk next week.\n"
        "\n"
        "On Wed, Apr 15, 2026 at 11:04 AM Vladimir <v@fitsiz.ru> wrote:\n"
        "> Hi, here is the pricelist.\n"
    )
    cleaned = clean_reply_text(text)
    assert "Sounds good" in cleaned, cleaned
    assert "wrote" not in cleaned.lower(), cleaned
    print("[OK] english reply cleaned →", repr(cleaned))


def main() -> int:
    test_parse_ru_reply()
    test_clean_inline_quotes()
    test_clean_english_reply()
    print("\nВсе проверки парсера прошли.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

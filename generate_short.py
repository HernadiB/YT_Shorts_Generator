import argparse
import json
import re
import random
import shutil
import subprocess
import textwrap
import os
import ctypes
import uuid
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import requests
import whisperx
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
PROMPTS = ROOT / "prompts"
CHANNEL_PROFILE_FILE = ROOT / "channel_profile.json"
DEFAULT_TAGS = [
    "personal finance",
    "finance",
    "money",
    "financial education",
]
DEFAULT_HASHTAGS = ["#Shorts", "#PersonalFinance", "#FinanceTips"]
MAX_YOUTUBE_TAG_CHARS = 480
METADATA_SCHEMA_FIELDS = [
    "title",
    "description",
    "tags",
    "hashtags",
    "search_keywords",
    "playlist",
    "script",
    "sections",
]
METADATA_SCHEMA_KEYS = set(METADATA_SCHEMA_FIELDS)
NUMBER_WORDS_ONES = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen",
]
NUMBER_WORDS_TENS = [
    "", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
    "eighty", "ninety",
]
CURRENCY_SYMBOLS = {
    "$": ("dollar", "dollars"),
    "€": ("euro", "euros"),
    "£": ("pound", "pounds"),
}
CURRENCY_CODES = {
    "USD": ("dollar", "dollars"),
    "EUR": ("euro", "euros"),
    "GBP": ("pound", "pounds"),
}
CURRENCY_WORDS = {
    "dollar": ("dollar", "dollars"),
    "dollars": ("dollar", "dollars"),
    "euro": ("euro", "euros"),
    "euros": ("euro", "euros"),
    "pound": ("pound", "pounds"),
    "pounds": ("pound", "pounds"),
}
NUMBER_SUFFIXES = {
    "k": "thousand",
    "m": "million",
    "b": "billion",
    "t": "trillion",
}
NUMBER_WORD_VALUES = {
    word: value for value, word in enumerate(NUMBER_WORDS_ONES)
}
NUMBER_WORD_VALUES.update({
    word: value * 10
    for value, word in enumerate(NUMBER_WORDS_TENS)
    if word
})
NUMBER_SCALE_WORDS = {
    "hundred": 100,
    "thousand": 1000,
    "million": 1_000_000,
    "billion": 1_000_000_000,
    "trillion": 1_000_000_000_000,
}
NUMBER_LARGE_SCALE_WORDS = {
    key: value for key, value in NUMBER_SCALE_WORDS.items()
    if key != "hundred"
}
NUMBER_PARSE_IGNORED_WORDS = {"and"}
QUALITY_GATE_DEFAULTS = {
    "enabled": True,
    "max_revision_attempts": 3,
    "min_script_words": 105,
    "hard_min_script_words": 95,
    "max_script_words": 145,
    "hard_max_script_words": 165,
    "min_complete_sentences": 4,
    "fail_on_unresolved_issues": True,
}
RENDER_DEFAULTS = {
    "tail_padding_seconds": 0.6,
}
GENERIC_INTRO_PATTERNS = [
    r"\btoday we (?:will|are going to)\b",
    r"\bin this video\b",
    r"\blet'?s talk about\b",
]
RISKY_FINANCE_PATTERNS = [
    r"\bguaranteed returns?\b",
    r"\brisk[- ]free returns?\b",
    r"\bcan'?t lose\b",
    r"\bwill make you rich\b",
    r"\bshould buy\b",
    r"\bmust buy\b",
]
CURRENT_DATA_FINANCE_PATTERNS = [
    r"\baverage\s+(?:credit card|mortgage|loan|savings|market)\s+rate\b",
    r"\bcurrent\s+(?:credit card|mortgage|loan|savings|market)\s+rate\b",
    r"\btoday'?s\s+(?:credit card|mortgage|loan|savings|market)\s+rate\b",
    r"\btriple\s+the\s+average\b",
]
PLACEHOLDER_PATTERN = r"\b(?:todo|placeholder|insert here|n/a|tbd)\b"
SPOKEN_FINANCE_ACRONYM_PATTERN = r"\b(?:ETF|ETFs|APR|CPI|IRA|IRAs|ROI|FDIC)\b"
APR_PATTERN = r"(?:apr|a\s+p\s+r)"
TEXT_ARTIFACT_REPLACEMENTS = {
    "â€“": "-",
    "â€”": "-",
    "â€˜": "'",
    "â€™": "'",
    "â€œ": '"',
    "â€": '"',
    "â€¦": "...",
    "–": "-",
    "—": "-",
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "…": "...",
    "\u00a0": " ",
}
AMOUNT_WORD_PATTERN = (
    "zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|"
    "twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
    "nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|"
    "ninety|hundred|thousand|million|billion|trillion"
)
SPOKEN_NUMBER_WORD_PATTERN = f"{AMOUNT_WORD_PATTERN}|and|point"
SPOKEN_NUMBER_PHRASE_PATTERN = (
    rf"(?:{SPOKEN_NUMBER_WORD_PATTERN})"
    rf"(?:[\s-]+(?:{SPOKEN_NUMBER_WORD_PATTERN}))*"
)
SCRIPT_EXPANSION_SENTENCES = [
    "The real lesson is simple.",
    "Understand the mechanism before copying the rule.",
    "Small timing details can change what the decision actually costs.",
    "That is what turns a finance term into a wallet-level decision.",
    "Follow for clearer money mechanics.",
]


def resolve_path(p):
    p = Path(p)
    if p.is_absolute():
        return p
    return ROOT / p

def short_path(path: Path) -> str:
    path = Path(path).resolve()

    if os.name != "nt":
        return str(path)

    buffer = ctypes.create_unicode_buffer(4096)
    result = ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, len(buffer))

    if result == 0:
        return str(path)

    return buffer.value


def short_output_path(path: Path) -> str:
    path = Path(path).resolve()

    if os.name != "nt":
        return str(path)

    parent_short = short_path(path.parent)
    return str(Path(parent_short) / path.name)


def piper_relative_path(path: Path, workdir: Path):
    path = Path(path).resolve()
    workdir = Path(workdir).resolve()

    try:
        return str(path.relative_to(workdir))
    except ValueError:
        return short_path(path)


@dataclass
class Chunk:
    text: str
    start: float
    end: float
    background_group: int = 0


def load_config():
    load_dotenv(ROOT / ".env")
    with open(ROOT / "config.json", "r", encoding="utf-8-sig") as f:
        return json.load(f)


def quality_gate_config(config: dict | None):
    configured = {}
    if config:
        configured = config.get("quality_gate", {}) or {}

    settings = dict(QUALITY_GATE_DEFAULTS)
    settings.update(configured)
    settings["max_revision_attempts"] = max(0, int(settings["max_revision_attempts"]))
    settings["min_script_words"] = max(1, int(settings["min_script_words"]))
    settings["hard_min_script_words"] = max(
        1,
        int(settings["hard_min_script_words"]),
    )
    settings["hard_min_script_words"] = min(
        settings["hard_min_script_words"],
        settings["min_script_words"],
    )
    settings["max_script_words"] = max(
        settings["min_script_words"],
        int(settings["max_script_words"]),
    )
    settings["hard_max_script_words"] = max(
        settings["max_script_words"],
        int(settings["hard_max_script_words"]),
    )
    settings["min_complete_sentences"] = max(
        1,
        int(settings["min_complete_sentences"]),
    )
    settings["enabled"] = bool(settings["enabled"])
    settings["fail_on_unresolved_issues"] = bool(
        settings["fail_on_unresolved_issues"]
    )
    return settings


def render_config(config: dict | None):
    configured = {}
    if config:
        configured = config.get("render", {}) or {}

    settings = dict(RENDER_DEFAULTS)
    settings.update(configured)
    settings["tail_padding_seconds"] = max(
        0.0,
        float(settings["tail_padding_seconds"]),
    )
    return settings


def load_channel_profile():
    if not CHANNEL_PROFILE_FILE.exists():
        return {}

    try:
        return json.loads(CHANNEL_PROFILE_FILE.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def safe_slug(text: str):
    return re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")[:80]


def clean_json_response(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()

    start = text.find("{")
    end = text.rfind("}")
    return text[start:end + 1]


def normalize(value: Any):
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        return " ".join(str(v).strip() for v in value if str(v).strip())

    if isinstance(value, dict):
        for k in ["text", "content", "script", "value", "message", "body"]:
            if k in value:
                return normalize(value[k])
        return json.dumps(value, ensure_ascii=False)

    return str(value).strip()


def clean_text_artifacts(text: str):
    text = normalize(text)
    for bad, replacement in TEXT_ARTIFACT_REPLACEMENTS.items():
        text = text.replace(bad, replacement)

    text = re.sub(r"\s+-\s+it(?:'| i)s\b", ". It is", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+-\s+", ". ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tag_candidates(value: Any):
    if isinstance(value, list):
        return [normalize(v) for v in value]

    if isinstance(value, str):
        return [t.strip() for t in re.split(r",|\|", value) if t.strip()]

    return []


def clean_tag(tag: str):
    tag = clean_text_artifacts(tag).replace("#", "")
    tag = re.sub(r"\s+", " ", tag).strip(" ,|#")
    return tag[:60].strip()


def keyword_fallbacks(topic: str, title: str = ""):
    candidates = []

    for value in [topic, title]:
        value = normalize(value)
        if not value:
            continue
        candidates.extend([
            value,
            f"{value} explained",
            f"{value} for beginners",
        ])

    candidates.extend(DEFAULT_TAGS)
    return candidates


def normalize_tags(value: Any, fallback=None, max_tags=12):
    tags = tag_candidates(value)
    if fallback:
        tags.extend(fallback)

    if not tags:
        tags = DEFAULT_TAGS

    total_chars = 0
    cleaned = []
    seen = set()

    for tag in tags:
        tag = clean_tag(tag)
        key = tag.casefold()
        if not tag or key in seen:
            continue

        next_total = total_chars + len(tag) + (1 if cleaned else 0)
        if next_total > MAX_YOUTUBE_TAG_CHARS:
            continue

        cleaned.append(tag)
        seen.add(key)
        total_chars = next_total

        if len(cleaned) >= max_tags:
            break

    return cleaned or DEFAULT_TAGS[:max_tags]


def hashtag_from_text(text: str):
    text = normalize(text)
    if re.fullmatch(r"#[A-Za-z0-9_]+", text):
        return text[:51]

    parts = re.findall(r"[A-Za-z0-9]+", text)
    if not parts:
        return ""

    pieces = [part if part.isupper() else part.capitalize() for part in parts]
    return f"#{''.join(pieces)[:50]}"


def normalize_hashtags(value: Any, fallback_tags=None):
    candidates = tag_candidates(value)
    hashtags = ["#Shorts"]
    seen = {"#shorts"}

    for candidate in candidates:
        hashtag = hashtag_from_text(candidate)
        key = hashtag.casefold()
        if hashtag and key not in seen:
            hashtags.append(hashtag)
            seen.add(key)

    for fallback in DEFAULT_HASHTAGS:
        key = fallback.casefold()
        if key not in seen:
            hashtags.append(fallback)
            seen.add(key)

    if fallback_tags:
        for tag in fallback_tags:
            hashtag = hashtag_from_text(tag)
            key = hashtag.casefold()
            if hashtag and key not in seen:
                hashtags.append(hashtag)
                seen.add(key)

    return hashtags[:3]


def append_hashtags_to_description(description: str, hashtags):
    description = normalize(description)
    if not description:
        description = (
            "Simple personal finance education for beginners.\n\n"
            "Education only. Not financial advice."
        )

    missing = [
        hashtag for hashtag in hashtags
        if hashtag.casefold() not in description.casefold()
    ]
    if missing:
        description = f"{description.rstrip()}\n\n{' '.join(missing)}"

    return description


def integer_to_words(value: int):
    value = int(value)

    if value < 0:
        return f"minus {integer_to_words(abs(value))}"

    if value < 20:
        return NUMBER_WORDS_ONES[value]

    if value < 100:
        tens, ones = divmod(value, 10)
        if ones:
            return f"{NUMBER_WORDS_TENS[tens]} {NUMBER_WORDS_ONES[ones]}"
        return NUMBER_WORDS_TENS[tens]

    if value < 1000:
        hundreds, rest = divmod(value, 100)
        words = f"{NUMBER_WORDS_ONES[hundreds]} hundred"
        if rest:
            words = f"{words} {integer_to_words(rest)}"
        return words

    for size, label in [
        (1_000_000_000_000, "trillion"),
        (1_000_000_000, "billion"),
        (1_000_000, "million"),
        (1000, "thousand"),
    ]:
        if value >= size:
            major, rest = divmod(value, size)
            words = f"{integer_to_words(major)} {label}"
            if rest:
                words = f"{words} {integer_to_words(rest)}"
            return words

    return str(value)


def decimal_to_words(value: str):
    whole, fraction = value.split(".", 1)
    whole_words = integer_to_words(int(whole or "0"))
    fraction_words = " ".join(NUMBER_WORDS_ONES[int(digit)] for digit in fraction)
    return f"{whole_words} point {fraction_words}"


def amount_to_words(value: str, suffix: str = ""):
    value = value.replace(",", "")

    if "." in value:
        words = decimal_to_words(value)
    else:
        words = integer_to_words(int(value))

    if suffix:
        words = f"{words} {NUMBER_SUFFIXES[suffix.lower()]}"

    return words


def currency_amount_to_words(value: str, currency_names, suffix: str = ""):
    singular, plural = currency_names
    clean_value = value.replace(",", "")

    if suffix:
        return f"{amount_to_words(clean_value, suffix)} {plural}"

    if "." in clean_value:
        whole, cents = clean_value.split(".", 1)
        cents = cents[:2].ljust(2, "0")
        whole_amount = int(whole or "0")
        cent_amount = int(cents)

        if cent_amount and whole_amount:
            unit = singular if whole_amount == 1 else plural
            cent_unit = "cent" if cent_amount == 1 else "cents"
            return (
                f"{integer_to_words(whole_amount)} {unit} and "
                f"{integer_to_words(cent_amount)} {cent_unit}"
            )

        if cent_amount:
            cent_unit = "cent" if cent_amount == 1 else "cents"
            return f"{integer_to_words(cent_amount)} {cent_unit}"

        unit = singular if whole_amount == 1 else plural
        return f"{integer_to_words(whole_amount)} {unit}"

    whole_amount = int(clean_value)
    unit = singular if whole_amount == 1 else plural
    return f"{integer_to_words(whole_amount)} {unit}"


def normalize_spoken_numbers(text: str):
    text = normalize(text)

    if not text:
        return ""

    number = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
    compact_number = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"

    def replace_symbol_currency(match):
        symbol = match.group("symbol")
        amount = match.group("amount")
        suffix = match.group("suffix") or ""
        return currency_amount_to_words(amount, CURRENCY_SYMBOLS[symbol], suffix)

    text = re.sub(
        rf"(?P<symbol>[$€£])\s*(?P<amount>{compact_number})(?:\s*(?P<suffix>[kKmMbBtT]))?\b",
        replace_symbol_currency,
        text,
    )

    def replace_prefix_currency(match):
        code = match.group("code").upper()
        amount = match.group("amount")
        suffix = match.group("suffix") or ""
        return currency_amount_to_words(amount, CURRENCY_CODES[code], suffix)

    text = re.sub(
        rf"\b(?P<code>USD|EUR|GBP)\s+(?P<amount>{number})(?:\s*(?P<suffix>[kKmMbBtT]))?\b",
        replace_prefix_currency,
        text,
        flags=re.IGNORECASE,
    )

    def replace_suffix_currency(match):
        amount = match.group("amount")
        suffix = match.group("suffix") or ""
        code = match.group("code").upper()
        return currency_amount_to_words(amount, CURRENCY_CODES[code], suffix)

    text = re.sub(
        rf"\b(?P<amount>{number})\s*(?P<suffix>[kKmMbBtT])?\s+(?P<code>USD|EUR|GBP)\b",
        replace_suffix_currency,
        text,
        flags=re.IGNORECASE,
    )

    def replace_misordered_currency_words(match):
        currency = match.group("currency").lower()
        amount = match.group("amount")
        suffix = match.group("suffix") or ""
        return currency_amount_to_words(amount, CURRENCY_WORDS[currency], suffix)

    text = re.sub(
        rf"\b(?P<currency>dollars?|euros?|pounds?)\s+(?P<amount>{number})(?:\s*(?P<suffix>[kKmMbBtT]))?\b",
        replace_misordered_currency_words,
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"(?i)\b401\s*\(\s*k\s*\)", "four oh one k", text)

    def replace_percent(match):
        return f"{amount_to_words(match.group('amount'))} percent"

    text = re.sub(
        rf"\b(?P<amount>{number})\s*%",
        replace_percent,
        text,
    )
    text = re.sub(
        rf"\b(?P<amount>{number})\s+percent\b",
        replace_percent,
        text,
        flags=re.IGNORECASE,
    )

    def replace_misordered_percent(match):
        return f"{amount_to_words(match.group('amount'))} percent"

    text = re.sub(
        rf"\bpercent\s+(?P<amount>{number})\b",
        replace_misordered_percent,
        text,
        flags=re.IGNORECASE,
    )

    def replace_compact_suffix(match):
        return amount_to_words(match.group("amount"), match.group("suffix"))

    text = re.sub(
        rf"\b(?P<amount>{number})(?P<suffix>[kKmMbBtT])\b",
        replace_compact_suffix,
        text,
    )

    def replace_plain_number(match):
        value = match.group("amount")
        if "." in value:
            return decimal_to_words(value.replace(",", ""))
        return integer_to_words(int(value.replace(",", "")))

    text = re.sub(rf"\b(?P<amount>{number})\b", replace_plain_number, text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def repair_currency_adjective_phrases(text: str):
    text = normalize(text)

    def replace_currency_adjective(match):
        amount = re.sub(r"\s+", " ", match.group("amount")).strip()
        currency = match.group("currency").lower()
        noun = re.sub(r"\s+", " ", match.group("noun")).strip()
        article = "an" if noun[:1].casefold() in {"a", "e", "i", "o", "u"} else "a"
        if match.group("article")[0].isupper():
            article = article.capitalize()
        return f"{article} {noun} of {amount} {currency}"

    noun_pattern = (
        "emergency fund|savings account|credit card balance|loan payment|"
        "monthly payment|investment account|cash reserve|budget gap|"
        "repair bill|medical bill|expense|fee|cost|payment|balance|loan|"
        "debt|principal|fund"
    )
    return re.sub(
        rf"\b(?P<article>[Aa]n?)\s+"
        rf"(?P<amount>(?:(?:{AMOUNT_WORD_PATTERN})\s+)+)"
        rf"(?P<currency>dollars?|euros?|pounds?)\s+"
        rf"(?P<noun>{noun_pattern})\b",
        replace_currency_adjective,
        text,
        flags=re.IGNORECASE,
    )


def repair_currency_unit_pluralization(text: str):
    text = normalize(text)

    def replace_currency_unit(match):
        amount = re.sub(r"\s+", " ", match.group("amount")).strip()
        currency = match.group("currency").lower()
        if amount.casefold() == "one":
            return f"{amount} {currency}"
        return f"{amount} {currency}s"

    return re.sub(
        rf"\b(?P<amount>(?:(?:{AMOUNT_WORD_PATTERN})\s+)+)"
        r"(?P<currency>dollar|euro|pound)\b",
        replace_currency_unit,
        text,
        flags=re.IGNORECASE,
    )


def normalize_sections(value: Any):
    if isinstance(value, list):
        sections = [normalize(v) for v in value]
    elif isinstance(value, str):
        sections = [s.strip() for s in re.split(r",|\|", value) if s.strip()]
    else:
        sections = []

    sections = [s for s in sections if s]

    if not sections:
        sections = ["Hook", "Explanation", "Example", "Why it matters", "CTA"]

    return sections


def channel_playlist_titles(profile):
    titles = []

    for playlist in profile.get("playlists", []):
        title = normalize(playlist.get("title"))
        if title:
            titles.append(title)

    return titles


def normalize_playlist(value: Any, allowed_titles):
    playlist = normalize(value)
    if not playlist:
        return ""

    if not allowed_titles:
        return playlist

    normalized = {" ".join(title.split()).casefold(): title for title in allowed_titles}
    return normalized.get(" ".join(playlist.split()).casefold(), "")


def request_ollama_json(model, url, prompt):
    response = requests.post(
        url,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        },
        timeout=300,
    )
    response.raise_for_status()

    raw = response.json()["response"]
    return json.loads(clean_json_response(raw))


def script_word_count(script: str):
    return len(re.findall(r"\b[A-Za-z]+(?:'[A-Za-z]+)?\b", script))


def sentence_list(script: str):
    return [
        sentence.strip()
        for sentence in re.findall(r"[^.!?]+[.!?]", script)
        if sentence.strip()
    ]


def dedupe_issues(issues):
    if isinstance(issues, str):
        issues = [issues]

    cleaned = []
    seen = set()

    for issue in issues:
        issue = normalize(issue)
        key = issue.casefold()
        if not issue or key in {"none", "no issues", "no issue"} or key in seen:
            continue
        cleaned.append(issue)
        seen.add(key)

    return cleaned


def unexpected_metadata_fragments(parsed):
    fragments = []
    if not isinstance(parsed, dict):
        return fragments

    for key, value in parsed.items():
        if key in METADATA_SCHEMA_KEYS:
            continue

        for candidate in [key, normalize(value)]:
            candidate = clean_text_artifacts(candidate)
            if script_word_count(candidate) >= 8 or re.search(r"[.!?]", candidate):
                fragments.append(candidate)

    return dedupe_issues(fragments)


def keep_metadata_schema(parsed):
    return {
        key: parsed[key]
        for key in METADATA_SCHEMA_FIELDS
        if key in parsed
    }


def parse_integer_words(tokens):
    total = 0
    current = 0
    seen_number = False

    for token in tokens:
        token = token.casefold()
        if token in NUMBER_PARSE_IGNORED_WORDS:
            continue

        if re.fullmatch(r"\d+", token):
            current += int(token)
            seen_number = True
            continue

        if token in NUMBER_WORD_VALUES:
            current += NUMBER_WORD_VALUES[token]
            seen_number = True
            continue

        if token == "hundred":
            current = max(1, current) * NUMBER_SCALE_WORDS[token]
            seen_number = True
            continue

        if token in NUMBER_LARGE_SCALE_WORDS:
            current = max(1, current)
            total += current * NUMBER_LARGE_SCALE_WORDS[token]
            current = 0
            seen_number = True
            continue

        return None

    if not seen_number:
        return None

    return total + current


def parse_spoken_number(text: str):
    text = normalize(text).casefold()
    tokens = re.findall(r"[a-z]+|\d+(?:\.\d+)?", text)
    tokens = [token for token in tokens if token not in NUMBER_PARSE_IGNORED_WORDS]

    if not tokens:
        return None

    if len(tokens) == 1 and re.fullmatch(r"\d+(?:\.\d+)?", tokens[0]):
        return float(tokens[0])

    if "point" not in tokens:
        return parse_integer_words(tokens)

    point_index = tokens.index("point")
    whole_tokens = tokens[:point_index]
    decimal_tokens = tokens[point_index + 1:]
    scale = 1

    if decimal_tokens and decimal_tokens[-1] in NUMBER_LARGE_SCALE_WORDS:
        scale = NUMBER_LARGE_SCALE_WORDS[decimal_tokens[-1]]
        decimal_tokens = decimal_tokens[:-1]

    whole = parse_integer_words(whole_tokens)
    if whole is None or not decimal_tokens:
        return None

    decimal_digits = []
    for token in decimal_tokens:
        if re.fullmatch(r"\d+", token):
            decimal_digits.extend(token)
            continue
        if token in NUMBER_WORD_VALUES and NUMBER_WORD_VALUES[token] < 10:
            decimal_digits.append(str(NUMBER_WORD_VALUES[token]))
            continue
        return None

    return (whole + float(f"0.{''.join(decimal_digits)}")) * scale


def number_group(name):
    return rf"(?<![A-Za-z-])(?P<{name}>{SPOKEN_NUMBER_PHRASE_PATTERN})"


def money_group(name):
    return rf"{number_group(name)}\s+(?:dollars?|euros?|pounds?)"


def extract_first_number(text, patterns, group_name="amount"):
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue

        value = parse_spoken_number(match.group(group_name))
        if value is not None:
            return value

    return None


def extract_loan_term_months(text):
    patterns = [
        rf"\b(?:over|for)\s+{number_group('term')}[\s-]+(?P<unit>years?|months?)\b",
        rf"\b{number_group('term')}[\s-]+(?P<unit>years?|months?)[\s-]+(?:loan|debt|term|schedule)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue

        value = parse_spoken_number(match.group("term"))
        if value is None or value <= 0:
            continue

        unit = match.group("unit").casefold()
        if unit.startswith("year"):
            return int(round(value * 12))
        return int(round(value))

    return None


def amortized_loan_payment(principal, apr_percent, months):
    if principal <= 0 or months <= 0 or apr_percent < 0:
        return None

    monthly_rate = apr_percent / 100 / 12
    if monthly_rate == 0:
        return principal / months

    return principal * monthly_rate / (1 - (1 + monthly_rate) ** -months)


def format_money_value(value):
    if abs(value) >= 100:
        return f"${value:,.0f}"
    return f"${value:,.2f}"


def loan_math_issues(script: str):
    text = clean_text_artifacts(script).casefold()
    if not re.search(
        rf"\b(?:loan|debt|principal|{APR_PATTERN}|interest rate|monthly payment)\b",
        text,
    ):
        return []

    principal = extract_first_number(text, [
        rf"\b(?:loan|balance|debt|principal)\s+of\s+{money_group('amount')}",
        rf"\b{money_group('amount')}\s+(?:loan|balance|debt|principal)\b",
        rf"\bborrow(?:ed|ing)?\s+{money_group('amount')}\b",
    ])
    apr = extract_first_number(text, [
        rf"\bannual\s+percentage\s+rate\b[^.!?]{{0,90}}\b{number_group('amount')}\s+percent\b",
        rf"\b{APR_PATTERN}\s+of\s+{number_group('amount')}\s+percent\b",
        rf"\b{number_group('amount')}\s+percent\s+{APR_PATTERN}\b",
        rf"\binterest\s+rate\s+of\s+{number_group('amount')}\s+percent\b",
        rf"\bat\s+{number_group('amount')}\s+percent\s+(?:{APR_PATTERN}|interest)\b",
        rf"\b{number_group('amount')}\s+percent\s+interest\b",
    ])
    monthly_payment = extract_first_number(text, [
        rf"\bmonthly\s+payment\s+of\s+(?:only\s+)?{money_group('amount')}",
        rf"\bpayment\s+of\s+(?:only\s+)?{money_group('amount')}\s+(?:a\s+month|per\s+month|monthly)\b",
        rf"\b{money_group('amount')}\s+(?:a\s+month|per\s+month|monthly)\b",
    ])
    stated_interest = extract_first_number(text, [
        rf"\b{money_group('amount')}\s+in\s+interest\b",
        rf"\binterest\s+of\s+{money_group('amount')}\b",
        rf"\bpay(?:ing)?\s+{money_group('amount')}\s+interest\b",
        rf"\bpay\s+(?:over\s+|about\s+)?{money_group('amount')}\s+more\s+than\s+the\s+principal(?:\s+amount)?\b",
        rf"\b(?:over\s+|about\s+)?{money_group('amount')}\s+more\s+than\s+the\s+principal(?:\s+amount)?\b",
    ])
    term_months = extract_loan_term_months(text)

    if (
        principal is not None
        and apr is not None
        and term_months is None
        and (monthly_payment is not None or stated_interest is not None)
    ):
        return [
            "Loan math incomplete: APR, payment, or total-interest examples "
            "need a loan term, or the example should stay qualitative."
        ]

    if principal is None or apr is None or term_months is None:
        return []

    expected_payment = amortized_loan_payment(principal, apr, term_months)
    if expected_payment is None:
        return []

    expected_interest = expected_payment * term_months - principal
    details = []

    if monthly_payment is not None:
        total_stated_payments = monthly_payment * term_months
        if total_stated_payments < principal:
            details.append(
                "stated payments total "
                f"{format_money_value(total_stated_payments)}, below the "
                f"{format_money_value(principal)} principal"
            )

        tolerance = max(5, expected_payment * 0.05)
        if abs(monthly_payment - expected_payment) > tolerance:
            details.append(
                "monthly payment should be about "
                f"{format_money_value(expected_payment)}, not "
                f"{format_money_value(monthly_payment)}"
            )

    if stated_interest is not None:
        tolerance = max(75, abs(expected_interest) * 0.10)
        if abs(stated_interest - expected_interest) > tolerance:
            details.append(
                "total interest should be about "
                f"{format_money_value(expected_interest)}, not "
                f"{format_money_value(stated_interest)}"
            )

    if not details:
        return []

    return [f"Loan math inconsistent: {'; '.join(details)}."]


def normalize_metadata(parsed, topic, playlist_titles):
    if not isinstance(parsed, dict):
        raise ValueError("Ollama did not return a JSON object.")

    extra_script_fragments = unexpected_metadata_fragments(parsed)
    parsed = dict(parsed)
    if extra_script_fragments:
        parsed["script"] = " ".join([
            normalize(parsed.get("script")),
            *extra_script_fragments,
        ]).strip()

    parsed = keep_metadata_schema(parsed)
    parsed["script"] = clean_text_artifacts(parsed.get("script"))
    parsed["script"] = normalize_spoken_numbers(parsed["script"])
    parsed["script"] = repair_currency_adjective_phrases(parsed["script"])
    parsed["script"] = repair_currency_unit_pluralization(parsed["script"])
    parsed["script"] = clean_text_artifacts(parsed["script"])
    parsed["title"] = clean_text_artifacts(parsed.get("title"))
    parsed["description"] = clean_text_artifacts(parsed.get("description"))
    parsed["playlist"] = normalize_playlist(parsed.get("playlist"), playlist_titles)
    parsed["sections"] = normalize_sections(parsed.get("sections"))

    if not parsed["title"]:
        parsed["title"] = topic

    fallback_keywords = keyword_fallbacks(topic, parsed["title"])
    parsed["search_keywords"] = normalize_tags(
        parsed.get("search_keywords"),
        fallback=fallback_keywords,
        max_tags=8,
    )
    parsed["tags"] = normalize_tags(
        tag_candidates(parsed.get("tags")) + parsed["search_keywords"],
        fallback=fallback_keywords,
        max_tags=12,
    )
    parsed["hashtags"] = normalize_hashtags(
        parsed.get("hashtags"),
        fallback_tags=parsed["tags"],
    )

    if not parsed["description"]:
        parsed["description"] = (
            "Simple personal finance education for beginners.\n\n"
            "Education only. Not financial advice."
        )
    parsed["description"] = append_hashtags_to_description(
        parsed["description"],
        parsed["hashtags"],
    )

    if not parsed["script"]:
        raise ValueError("No usable script returned by Ollama.")

    return parsed


def heuristic_quality_issues(meta, settings):
    script = normalize(meta.get("script"))
    title = normalize(meta.get("title"))
    description = normalize(meta.get("description"))
    issues = []

    if not script:
        return ["Script is empty."]

    word_count = script_word_count(script)
    if word_count < settings["hard_min_script_words"]:
        issues.append(
            f"Script is far too short: {word_count} words; "
            f"hard minimum is {settings['hard_min_script_words']}."
        )
    elif word_count < settings["min_script_words"]:
        issues.append(
            f"Script is too short: {word_count} words; "
            f"target minimum is {settings['min_script_words']}."
        )

    if word_count > settings["hard_max_script_words"]:
        issues.append(
            f"Script is far too long: {word_count} words; "
            f"hard maximum is {settings['hard_max_script_words']}."
        )
    elif word_count > settings["max_script_words"]:
        issues.append(
            f"Script is too long: {word_count} words; "
            f"target maximum is {settings['max_script_words']}."
        )

    sentences = sentence_list(script)
    if len(sentences) < settings["min_complete_sentences"]:
        issues.append("Script has too few complete sentences.")
    if len(sentences) > 12:
        issues.append("Script has too many sentences for the target pacing.")

    for sentence in sentences:
        sentence_words = script_word_count(sentence)
        if sentence_words > 22:
            issues.append(
                "Script has an overloaded sentence above 22 words; "
                "split it for clearer narration."
            )
            break

    if not re.search(r"[.!?]$", script):
        issues.append("Script must end with sentence punctuation.")

    if re.search(r"\b([A-Za-z]+)\s+\1\b", script, flags=re.IGNORECASE):
        issues.append("Script contains an accidental repeated word.")

    searchable_text = f"{title}\n{description}\n{script}"
    if any(bad in searchable_text for bad in TEXT_ARTIFACT_REPLACEMENTS):
        issues.append("Script or metadata contains text encoding artifacts.")

    if re.search(PLACEHOLDER_PATTERN, searchable_text, flags=re.IGNORECASE):
        issues.append("Metadata or script contains placeholder text.")

    for pattern in GENERIC_INTRO_PATTERNS:
        if re.search(pattern, script, flags=re.IGNORECASE):
            issues.append("Script starts or reads like a generic video intro.")
            break

    for pattern in RISKY_FINANCE_PATTERNS:
        if re.search(pattern, searchable_text, flags=re.IGNORECASE):
            issues.append("Script or metadata contains a risky finance claim.")
            break

    for pattern in CURRENT_DATA_FINANCE_PATTERNS:
        if re.search(pattern, searchable_text, flags=re.IGNORECASE):
            issues.append(
                "Script or metadata contains a finance claim that needs "
                "current market data."
            )
            break

    issues.extend(loan_math_issues(script))

    if re.search(r"[$€£%]|\b(?:USD|EUR|GBP)\b", script, flags=re.IGNORECASE):
        issues.append("Spoken script still contains numeric finance symbols.")

    if re.search(SPOKEN_FINANCE_ACRONYM_PATTERN, script, flags=re.IGNORECASE):
        issues.append("Spoken script contains unspaced finance acronyms.")

    if re.search(
        rf"\b(?:dollars?|euros?|pounds?)\s+(?:{AMOUNT_WORD_PATTERN})\b",
        script,
        flags=re.IGNORECASE,
    ):
        issues.append("Script contains a misordered currency phrase.")

    if re.search(
        rf"\bpercent\s+(?:{AMOUNT_WORD_PATTERN})\b",
        script,
        flags=re.IGNORECASE,
    ):
        issues.append("Script contains a misordered percentage phrase.")

    if re.search(
        rf"\b[Aa]n?\s+(?:(?:{AMOUNT_WORD_PATTERN})\s+)+"
        r"(?:dollars?|euros?|pounds?)\s+"
        r"(?:fund|payment|account|balance|loan|debt|principal|expense|fee|cost|bill)\b",
        script,
        flags=re.IGNORECASE,
    ):
        issues.append("Script contains an ungrammatical currency adjective phrase.")

    for match in re.finditer(
        rf"\b(?P<amount>(?:(?:{AMOUNT_WORD_PATTERN})\s+)+)"
        r"(?P<currency>dollar|euro|pound)\b",
        script,
        flags=re.IGNORECASE,
    ):
        amount = re.sub(r"\s+", " ", match.group("amount")).strip()
        if amount.casefold() != "one":
            issues.append(
                "Script contains a singular currency unit after a plural amount."
            )
            break

    return dedupe_issues(issues)


def sentence_already_present(script, sentence):
    return sentence.casefold() in script.casefold()


def repair_short_script(meta, settings):
    script = normalize(meta.get("script"))
    if script_word_count(script) >= settings["hard_min_script_words"]:
        return meta

    additions = []
    for sentence in SCRIPT_EXPANSION_SENTENCES:
        if "follow" in sentence.casefold() and re.search(r"\bfollow\b", script, re.I):
            continue
        if sentence_already_present(script, sentence):
            continue

        additions.append(sentence)
        candidate = " ".join([script] + additions)
        if script_word_count(candidate) >= settings["min_script_words"]:
            break

    if not additions:
        return meta

    repaired = dict(meta)
    repaired["script"] = normalize_spoken_numbers(" ".join([script] + additions))
    repaired["script"] = repair_currency_adjective_phrases(repaired["script"])
    repaired["script"] = repair_currency_unit_pluralization(repaired["script"])
    repaired["script"] = clean_text_artifacts(repaired["script"])
    return repaired


def blocking_quality_issues(issues):
    blocking = []
    soft_prefixes = (
        "Script is too short:",
        "Script is too long:",
        "Script has too few complete sentences.",
        "Script has too many sentences for the target pacing.",
        "Script has an overloaded sentence above 22 words",
        "Overloaded sentence:",
        "Spoken script exceeds word limit.",
        "Technical term ",
        "LLM quality review did not approve the script.",
    )

    for issue in dedupe_issues(issues):
        if issue.startswith(soft_prefixes):
            continue
        blocking.append(issue)

    return blocking


def build_quality_review_prompt(topic, meta, playlist_titles, issues):
    playlist_guidance = "[]"
    if playlist_titles:
        playlist_guidance = json.dumps(playlist_titles, ensure_ascii=False)

    return f"""You are a strict English copy editor and personal finance fact-checker.

Review and rewrite the YouTube Shorts metadata below before it is sent to TTS.
The final result must be clean, natural English with no grammar, sentence
structure, terminology, or finance-mechanism mistakes.

Topic:
{topic}

Allowed playlist titles:
{playlist_guidance}

Known issues to fix:
{json.dumps(issues, ensure_ascii=False)}

Current metadata:
{json.dumps(meta, indent=2, ensure_ascii=False)}

Quality requirements:
- Fix grammar, word order, punctuation, agreement, awkward phrasing, and
  sentence fragments.
- Make every sentence complete, natural, and easy to read aloud.
- Use precise grammar with clear subjects and verbs. Replace vague "this",
  "that", or "it" when the reference could be unclear.
- Prefer active voice and direct sentence structure. Do not bury the main idea
  in long dependent clauses.
- Keep the script professionally simple: precise, but understandable.
- Do not introduce technical claims that need current market data, tax/legal
  advice, guarantees, stock picks, or investment recommendations.
- Every economic claim must be logically true, mathematically consistent, and
  financially coherent in the context given.
- Do not invent background facts, market averages, typical rates, hidden fees,
  or historical performance. Use them only when the original metadata already
  provided them.
- If a claim needs missing background information, either include the needed
  assumption in plain English or make the example qualitative.
- Use causality carefully. Do not say one finance variable causes another unless
  that mechanism is actually explained in the script.
- Correct finance terminology. If a technical term appears, explain it in plain
  English immediately.
- Technical finance terms must be both correct and pronounceable. Introduce the
  full term first, then a simple translation.
- For acronyms that should be read letter by letter, write spaced letters in
  the spoken script: "E T F", "A P R", "C P I", "I R A", "R O I", and
  "F D I C". Do not write "ETF", "APR", "CPI", "IRA", "ROI", or "FDIC" in the
  spoken script.
- Avoid plural acronym forms in the spoken script, such as "ETFs". Use "E T F"
  as an adjective or rewrite the phrase, for example "funds like this".
- Avoid parentheses, slashes, dense hyphenated terms, and ticker-like notation
  in the spoken script. Write the phrase the way a human should say it.
- Keep one financial mechanism only. Remove side topics that muddy the logic.
- Keep the hook sharp, but do not use clickbait, fake urgency, or vague hype.
- Keep the spoken script between 105 and 145 words when possible.
- A clean script between 95 and 155 words may still be approved. Do not reject
  a publication-ready script only because it is slightly outside the target.
- Use spoken numbers only in the script, such as "one thousand dollars" and
  "four percent". Do not write "$1,000", "4%", "USD", or "dollar one thousand"
  in the script.
- If you use a loan, APR, monthly payment, term, or total-interest example,
  make the amortization math internally consistent. If you cannot verify the
  math, use a qualitative wallet-level example instead.
- If you state a total interest amount for a loan, include the loan term.
- Do not combine principal, APR, term, monthly payment, and total interest
  unless all figures can be true at the same time.
- Do not use broken currency adjectives. Write "an emergency fund of one
  thousand dollars", not "a one thousand dollars emergency fund".
- Use plural currency units after any amount other than exactly "one": "one
  thousand dollars", not "one thousand dollar".
- Preserve the topic and useful SEO metadata.
- Use one exact playlist title from the allowed list if the list is not empty.
- Return only the keys in the JSON schema below. Do not add extra keys.
- Put every word that should be narrated inside the script field. Do not place
  spoken narration in any other field.
- The script must end with this exact final sentence: "Follow for more
  practical money tips."
- Do not use the word "advice" in the CTA.

Return valid JSON only in this exact schema:
{{
  "approved": true,
  "issues": ["string"],
  "title": "string",
  "description": "string",
  "tags": ["string", "string"],
  "hashtags": ["#Shorts", "#PersonalFinance", "#FinanceTips"],
  "search_keywords": ["string", "string"],
  "playlist": "string",
  "script": "string",
  "sections": ["Hook", "Explanation", "Example", "Why it matters", "CTA"]
}}

Set approved to true only if your returned version is ready for publication.
Set issues to an empty array when the returned version has no remaining issue.
"""


def merge_review_metadata(meta, review):
    merged = dict(meta)
    for key in [
        "title",
        "description",
        "tags",
        "hashtags",
        "search_keywords",
        "playlist",
        "script",
        "sections",
    ]:
        if key in review:
            merged[key] = review[key]

    return merged


def apply_quality_gate(meta, topic, model, url, playlist_titles, settings):
    if not settings["enabled"]:
        meta["quality_checks"] = {
            "enabled": False,
            "passed": True,
            "issues": [],
        }
        return meta

    approved = False
    review_issues = []
    attempts = 0

    for attempt in range(settings["max_revision_attempts"]):
        attempts = attempt + 1
        issues = heuristic_quality_issues(meta, settings)
        review_prompt = build_quality_review_prompt(
            topic,
            meta,
            playlist_titles,
            issues,
        )
        review = request_ollama_json(model, url, review_prompt)
        approved = bool(review.get("approved", False))
        review_issues = dedupe_issues(review.get("issues", []))
        meta = normalize_metadata(
            merge_review_metadata(meta, review),
            topic,
            playlist_titles,
        )
        meta = repair_short_script(meta, settings)

        if approved and not review_issues:
            post_review_issues = heuristic_quality_issues(meta, settings)
            blocking_issues = blocking_quality_issues(post_review_issues)
            if not blocking_issues:
                meta["quality_checks"] = {
                    "enabled": True,
                    "passed": True,
                    "review_attempts": attempts,
                    "issues": blocking_issues,
                    "warnings": post_review_issues,
                }
                return meta

    meta = repair_short_script(meta, settings)
    final_issues = heuristic_quality_issues(meta, settings)
    review_warnings = []
    if attempts and not approved:
        review_warnings.append("LLM quality review did not approve the script.")
    review_warnings.extend(review_issues)
    final_issues = dedupe_issues(final_issues)
    blocking_issues = blocking_quality_issues(final_issues)
    warnings = dedupe_issues([
        issue for issue in final_issues
        if issue not in blocking_issues
    ] + review_warnings)
    meta["quality_checks"] = {
        "enabled": True,
        "passed": not blocking_issues,
        "review_attempts": attempts,
        "issues": blocking_issues,
        "warnings": warnings,
    }

    if blocking_issues and settings["fail_on_unresolved_issues"]:
        formatted = "\n- ".join(blocking_issues)
        raise ValueError(f"Generated script failed the quality gate:\n- {formatted}")

    return meta


def ask_ollama(topic, model, url, config=None):
    system_prompt = (PROMPTS / "system_prompt.txt").read_text(encoding="utf-8")
    quality_settings = quality_gate_config(config)
    profile = load_channel_profile()
    playlist_titles = channel_playlist_titles(profile)
    playlist_guidance = ""
    if playlist_titles:
        playlist_guidance = (
            "\nChoose the single best playlist for this Short. "
            "Use one exact title from this list:\n"
            f"{json.dumps(playlist_titles, ensure_ascii=False)}\n"
        )

    prompt = f"""{system_prompt}

Topic: {topic}

Create a faceless English YouTube Short about this topic for beginners in personal finance.
{playlist_guidance}

The script must:
- feel human
- sound confident and professional
- be easy to understand
- sound "professionally simple": credible, but easy for a normal adult to follow
- use 105 to 145 spoken words
- keep the first second sharp, then slow the explanation down for comprehension
- make the main takeaway clear on first watch, but reward a replay with the
  example, contrast, or final line
- end by looping back to the opening hook naturally
- avoid textbook phrasing
- avoid robotic filler
- keep attention in the first 2 seconds
- explain one concept clearly
- explain one finance mechanism, not a list of generic tips
- use precise grammar with clear subjects, active voice, and no vague pronouns
- make professional finance terms pronounceable in TTS and readable in captions
- include one tiny number example or concrete wallet-level scenario
- make every economic claim logically true and financially coherent
- avoid invented background facts, market averages, typical rates, and
  historical performance unless they are included in the topic
- name one precise finance term only if it is translated into plain English
- write numbers, percentages, and currencies exactly as they should be spoken
- keep any loan, APR, payment, term, and interest figures internally consistent
- write letter-by-letter acronyms as spaced letters in the spoken script, such
  as "E T F" and "A P R", not "ETF" or "APR"
- end with the exact sentence: "Follow for more practical money tips."
- put every narrated word inside the script field
- return only the JSON keys requested below

Return valid JSON only in this format:
{{
  "title": "string",
  "description": "string",
  "tags": ["string", "string"],
  "hashtags": ["#Shorts", "#PersonalFinance", "#FinanceTips"],
  "search_keywords": ["string", "string"],
  "playlist": "string",
  "script": "string",
  "sections": ["Hook", "Explanation", "Example", "Why it matters", "CTA"]
}}
"""

    parsed = request_ollama_json(model, url, prompt)
    parsed = normalize_metadata(parsed, topic, playlist_titles)
    parsed = apply_quality_gate(
        parsed,
        topic,
        model,
        url,
        playlist_titles,
        quality_settings,
    )

    return parsed


# ---------------------------
# 🎙 TTS (Piper)
# ---------------------------
def run_piper(script_text: str, config: dict, out_wav: Path):
    piper_exe_path = resolve_path(config["paths"]["piper_exe"])
    voice_model_path = resolve_path(config["paths"]["voice_model"])
    voice_config_path = resolve_path(config["paths"]["voice_config"])
    tts_config = config.get("tts", {})
    piper_workdir = piper_exe_path.resolve().parent
    espeak_data_path = piper_workdir / "espeak-ng-data"
    temp_wav = piper_workdir / f"piper-output-{uuid.uuid4().hex}.wav"

    if temp_wav.exists():
        temp_wav.unlink()

    cmd = [
        str(piper_exe_path.resolve()),
        "--model",
        piper_relative_path(voice_model_path, piper_workdir),
        "--config",
        piper_relative_path(voice_config_path, piper_workdir),
    ]

    if espeak_data_path.exists():
        cmd.extend([
            "--espeak_data",
            piper_relative_path(espeak_data_path, piper_workdir),
        ])

    for option in ["length_scale", "sentence_silence", "noise_scale", "noise_w"]:
        value = tts_config.get(option)
        if value is not None:
            cmd.extend([f"--{option}", str(value)])

    cmd.extend([
        "--output_file",
        temp_wav.name,
    ])

    result = subprocess.run(
        cmd,
        input=script_text,
        text=True,
        capture_output=True,
        check=False,
        cwd=str(piper_workdir),
    )

    if result.returncode != 0:
        if temp_wav.exists():
            temp_wav.unlink()
        raise RuntimeError(
            f"Piper crashed.\n"
            f"Return code: {result.returncode}\n\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(temp_wav), str(out_wav))


# ---------------------------
# 🧠 WhisperX timing
# ---------------------------
def round_to_frame(t, fps):
    return round(t * fps) / fps


def script_caption_tokens(script_text: str):
    return re.findall(
        r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?[.,!?;:]?",
        normalize(script_text),
    )


def caption_token_key(token: str):
    return re.sub(r"[^a-z0-9]+", "", normalize(token).casefold())


def align_transcript_words_to_script(words, script_text: str):
    script_tokens = [
        token for token in script_caption_tokens(script_text)
        if caption_token_key(token)
    ]
    transcript_keys = [
        caption_token_key(word.get("word", ""))
        for word in words
    ]
    script_keys = [caption_token_key(token) for token in script_tokens]

    if not words or not script_tokens:
        return words

    matcher = SequenceMatcher(
        None,
        transcript_keys,
        script_keys,
        autojunk=False,
    )

    if matcher.ratio() < 0.62 and abs(len(transcript_keys) - len(script_keys)) > 6:
        return words

    aligned_words = [dict(word) for word in words]

    for tag, word_start, word_end, script_start, script_end in matcher.get_opcodes():
        if tag == "delete":
            continue

        if tag == "insert":
            inserted_tokens = script_tokens[script_start:script_end]
            if word_start > 0 and 0 < len(inserted_tokens) <= 2:
                target = aligned_words[word_start - 1]
                inserted = " ".join(inserted_tokens)
                target["word"] = f"{target['word']} {inserted}".strip()
            continue

        replace_count = min(word_end - word_start, script_end - script_start)
        for offset in range(replace_count):
            target = aligned_words[word_start + offset]
            replacement = script_tokens[script_start + offset]
            if caption_token_key(target.get("word", "")) != caption_token_key(replacement):
                target["transcribed_word"] = target.get("word", "")
            target["word"] = replacement

        if tag == "replace" and script_end - script_start > replace_count:
            extras = script_tokens[script_start + replace_count:script_end]
            if 0 < len(extras) <= 2 and word_start + replace_count - 1 >= 0:
                target = aligned_words[word_start + replace_count - 1]
                target["word"] = f"{target['word']} {' '.join(extras)}".strip()

    return aligned_words


def transcribe_words(audio_path: Path, script_text: str = ""):
    device = "cpu"
    audio = whisperx.load_audio(str(audio_path))

    model = whisperx.load_model("small", device=device, compute_type="int8")
    result = model.transcribe(audio)

    align_model, metadata = whisperx.load_align_model(
        language_code=result["language"],
        device=device
    )

    aligned = whisperx.align(
        result["segments"],
        align_model,
        metadata,
        audio,
        device
    )

    words = []
    for seg in aligned["segments"]:
        for w in seg.get("words", []):
            start = w.get("start")
            end = w.get("end")
            word = w.get("word", "")

            if start is not None and end is not None and str(word).strip():
                words.append({
                    "word": str(word).strip(),
                    "start": float(start),
                    "end": float(end)
                })

    if not words:
        raise ValueError("WhisperX returned no word timings.")

    if script_text:
        words = align_transcript_words_to_script(words, script_text)

    return words


def build_chunks(words, fps, words_per_chunk=1):
    words_per_chunk = max(1, int(words_per_chunk))
    chunks = []
    i = 0

    while i < len(words):
        group = words[i:i + words_per_chunk]

        text = " ".join(w["word"] for w in group).upper()
        start = round_to_frame(group[0]["start"], fps)
        end = round_to_frame(group[-1]["end"], fps)

        if end <= start:
            end = start + (1 / fps)

        chunks.append(Chunk(text, start, end, len(chunks)))
        i += words_per_chunk

    return chunks


def group_semantic_words(words, min_words=3, max_words=8, max_seconds=3.4):
    min_words = max(1, int(min_words))
    max_words = max(min_words, int(max_words))
    max_seconds = max(1.0, float(max_seconds))

    groups = []
    group = []

    for word in words:
        group.append(word)
        duration = group[-1]["end"] - group[0]["start"]
        ends_phrase = re.search(r"[.!?,;:]$", str(word["word"])) is not None
        is_long_enough = len(group) >= min_words
        is_full = len(group) >= max_words or duration >= max_seconds

        if (is_long_enough and ends_phrase) or is_full:
            groups.append(group)
            group = []

    if group:
        groups.append(group)

    return groups


def chunk_from_word_group(group, fps, background_group=0):
    start = round_to_frame(group[0]["start"], fps)
    end = round_to_frame(group[-1]["end"], fps)

    if end <= start:
        end = start + (1 / fps)

    text = " ".join(w["word"] for w in group)
    return Chunk(text.upper(), start, end, background_group)


def build_semantic_chunks(words, fps, min_words=3, max_words=8, max_seconds=3.4):
    chunks = []

    for background_group, group in enumerate(group_semantic_words(words, min_words, max_words, max_seconds)):
        chunks.append(chunk_from_word_group(group, fps, background_group))

    return chunks


def build_progressive_semantic_chunks(words, fps, min_words=3, max_words=8, max_seconds=3.4):
    chunks = []

    for background_group, group in enumerate(group_semantic_words(words, min_words, max_words, max_seconds)):
        for i in range(len(group)):
            visible_words = group[:i + 1]
            text = " ".join(w["word"] for w in visible_words)
            word = group[i]
            start = round_to_frame(word["start"], fps)
            end = round_to_frame(word["end"], fps)

            if end <= start:
                end = start + (1 / fps)

            chunks.append(Chunk(text.upper(), start, end, background_group))

    return chunks


def write_caption_timing(words, chunks, timeline, out):
    payload = {
        "words": words,
        "caption_chunks": [chunk.__dict__ for chunk in chunks],
        "visual_timeline": [chunk.__dict__ for chunk in timeline],
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_caption_chunks(words, fps, config):
    caption_config = config["video"].get("captions", {})
    mode = caption_config.get("mode", "progressive")

    if mode == "fixed":
        words_per_chunk = caption_config.get(
            "words_per_chunk",
            config["video"].get("caption_words_per_scene", 4),
        )
        return build_chunks(words, fps, words_per_chunk)

    if mode == "phrase":
        return build_semantic_chunks(
            words,
            fps,
            min_words=caption_config.get("min_words", 3),
            max_words=caption_config.get("max_words", 8),
            max_seconds=caption_config.get("max_seconds", 3.4),
        )

    return build_progressive_semantic_chunks(
        words,
        fps,
        min_words=caption_config.get("min_words", 3),
        max_words=caption_config.get("max_words", 8),
        max_seconds=caption_config.get("max_seconds", 3.4),
    )


# ---------------------------
# 🎨 Scene rendering
# ---------------------------
def get_audio_duration(audio_path: Path, config: dict) -> float:
    ffprobe = config["paths"].get("ffprobe", "ffprobe")
    result = subprocess.run(
        [
            ffprobe,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"ffprobe could not read audio duration.\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )

    return float(result.stdout.strip())


def validate_audio_duration(audio_duration: float, config: dict):
    video_config = config.get("video", {})
    min_seconds = video_config.get("min_seconds")
    max_seconds = video_config.get("max_seconds")

    if min_seconds:
        min_seconds = float(min_seconds)
        if audio_duration < min_seconds:
            raise ValueError(
                f"Generated voice is {audio_duration:.1f}s, below the configured "
                f"{min_seconds:.1f}s finance pacing floor. Regenerate with a "
                "longer script, increase tts.length_scale, or lower "
                "video.min_seconds in config.json."
            )

    if not max_seconds:
        return

    max_seconds = float(max_seconds)
    if audio_duration <= max_seconds:
        return

    raise ValueError(
        f"Generated voice is {audio_duration:.1f}s, above the configured "
        f"{max_seconds:.1f}s Shorts target. Regenerate with a shorter script "
        "or raise video.max_seconds in config.json."
    )


def build_visual_timeline(chunks, audio_duration, fps):
    if not chunks:
        raise ValueError("Cannot build visual timeline without chunks.")

    frame_duration = 1 / fps
    timeline = []

    for i, chunk in enumerate(chunks):
        start = 0 if i == 0 else chunk.start
        next_start = chunks[i + 1].start if i + 1 < len(chunks) else audio_duration
        end = max(next_start, start + frame_duration)

        if end > audio_duration:
            end = audio_duration

        if end <= start:
            end = start + frame_duration

        timeline.append(Chunk(chunk.text, start, end, chunk.background_group))

    return timeline


def pick_font(size):
    return ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", size)


def list_background_images(config, slug):
    background_config = config.get("backgrounds", {})
    base_dir = resolve_path(background_config.get("image_dir", "assets/backgrounds"))
    extensions = {".jpg", ".jpeg", ".png", ".webp"}

    candidate_dirs = [
        base_dir / slug,
        base_dir / "default",
        base_dir,
    ]

    seen = set()
    images = []
    for candidate_dir in candidate_dirs:
        if not candidate_dir.exists():
            continue

        for path in sorted(candidate_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in extensions and path not in seen:
                images.append(path)
                seen.add(path)

        if images:
            break

    return images


def cover_image(image, w, h):
    image = image.convert("RGB")
    scale = max(w / image.width, h / image.height)
    resized = image.resize(
        (int(image.width * scale) + 1, int(image.height * scale) + 1),
        Image.Resampling.LANCZOS,
    )
    x = (resized.width - w) // 2
    y = (resized.height - h) // 2
    return resized.crop((x, y, x + w, y + h))


def make_procedural_finance_background(w, h, variant=0):
    rng = random.Random(variant)
    palettes = [
        ((12, 20, 24), (28, 97, 85), (232, 218, 148), (238, 244, 241)),
        ((17, 18, 26), (67, 112, 163), (238, 183, 74), (239, 242, 246)),
        ((15, 25, 22), (93, 139, 94), (231, 199, 94), (244, 246, 238)),
    ]
    bg, accent, gold, line = palettes[variant % len(palettes)]
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img, "RGBA")

    for x in range(0, w, 90):
        draw.line((x, 0, x, h), fill=(*line, 22), width=1)
    for y in range(0, h, 90):
        draw.line((0, y, w, y), fill=(*line, 18), width=1)

    chart_area_top = int(h * 0.18)
    chart_area_bottom = int(h * 0.72)
    points = []
    for i in range(9):
        x = int(w * 0.08 + i * (w * 0.84 / 8))
        trend = chart_area_bottom - int(i * (h * 0.035))
        y = trend + rng.randint(-90, 90)
        points.append((x, max(chart_area_top, min(chart_area_bottom, y))))

    draw.line(points, fill=(*gold, 185), width=14, joint="curve")
    draw.line(points, fill=(*line, 210), width=5, joint="curve")
    for point in points:
        r = 16
        draw.ellipse((point[0] - r, point[1] - r, point[0] + r, point[1] + r), fill=(*gold, 210))

    bar_base = int(h * 0.82)
    for i in range(7):
        x0 = int(w * 0.08 + i * w * 0.13)
        bar_h = rng.randint(int(h * 0.08), int(h * 0.24))
        draw.rounded_rectangle(
            (x0, bar_base - bar_h, x0 + int(w * 0.07), bar_base),
            radius=8,
            fill=(*accent, 155),
        )

    for _ in range(5):
        cx = rng.randint(int(w * 0.08), int(w * 0.92))
        cy = rng.randint(int(h * 0.08), int(h * 0.88))
        r = rng.randint(34, 62)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(*gold, 95), width=5)

    return img


def make_background(w, h, background_path=None, variant=0):
    if background_path:
        img = cover_image(Image.open(background_path), w, h)
    else:
        img = make_procedural_finance_background(w, h, variant)

    overlay = Image.new("RGB", (w, h), (0, 0, 0))
    return Image.blend(img, overlay, 0.46)


def make_scene(w, h, text, out, background_path=None, variant=0):
    img = make_background(w, h, background_path, variant)
    draw = ImageDraw.Draw(img)

    if not text.strip():
        img.save(out)
        return

    font = pick_font(110)

    wrapped = "\n".join(textwrap.wrap(text, 12))
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font)

    x = (w - (bbox[2] - bbox[0])) // 2
    y = (h - (bbox[3] - bbox[1])) // 2

    draw.multiline_text((x + 3, y + 3), wrapped, font=font, fill=(0, 0, 0))
    draw.multiline_text((x, y), wrapped, font=font, fill=(255, 255, 255))

    img.save(out)


def build_scenes(chunks, config, wd, slug):
    scenes = []
    scene_dir = wd / "scenes"
    scene_dir.mkdir(exist_ok=True)

    w = config["video"]["width"]
    h = config["video"]["height"]
    backgrounds = list_background_images(config, slug)

    for i, c in enumerate(chunks):
        path = scene_dir / f"s{i}.png"
        background_group = c.background_group
        background_path = backgrounds[background_group % len(backgrounds)] if backgrounds else None
        make_scene(w, h, c.text, path, background_path, background_group)
        scenes.append(path)

    return scenes


# ---------------------------
# 🎬 FFmpeg render
# ---------------------------
def pick_music_track(config):
    music_dir = resolve_path(config.get("music", {}).get("library_dir", "assets/music/library"))

    if not music_dir.exists():
        return None

    tracks = [
        p for p in music_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
    ]

    if not tracks:
        return None

    return random.choice(tracks)


def write_concat(scenes, chunks, out):
    lines = []

    for s, c in zip(scenes, chunks):
        rel = s.relative_to(out.parent).as_posix()
        duration = max(0.033, c.end - c.start)

        lines.append(f"file '{rel}'")
        lines.append(f"duration {duration:.6f}")

    lines.append(f"file '{scenes[-1].relative_to(out.parent).as_posix()}'")
    out.write_text("\n".join(lines), encoding="utf-8")


def ffmpeg_render(config, concat, wav, out, music=None):
    ffmpeg = config["paths"]["ffmpeg"]
    music_config = config.get("music", {})
    music_volume = float(music_config.get("volume", 0.18))
    ducking_threshold = float(music_config.get("ducking_threshold", 0.03))

    cmd = [
            ffmpeg,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat),
            "-i", str(wav),
    ]

    if music:
        cmd.extend([
            "-stream_loop", "-1",
            "-i", str(music),
            "-filter_complex",
            f"[2:a]volume={music_volume}[music];"
            f"[music][1:a]sidechaincompress=threshold={ducking_threshold}:ratio=12:attack=50:release=300[ducked];"
            "[1:a][ducked]amix=inputs=2:duration=first:dropout_transition=0[aout]",
            "-map", "0:v:0",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            str(out)
        ])
    else:
        cmd.extend([
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            str(out)
        ])

    subprocess.run(cmd, check=True)


# ---------------------------
# 🚀 MAIN
# ---------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    args = parser.parse_args()

    config = load_config()
    model = os.getenv("OLLAMA_MODEL")
    url = os.getenv("OLLAMA_URL")

    OUTPUTS.mkdir(exist_ok=True)

    meta = ask_ollama(args.topic, model, url, config)

    meta["topic"] = args.topic

    slug = safe_slug(args.topic)
    wd = OUTPUTS / slug
    wd.mkdir(exist_ok=True)

    script = meta["script"]

    (wd / "script.txt").write_text(script, encoding="utf-8")
    (wd / "metadata.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    wav = wd / "voice.wav"
    run_piper(script, config, wav)

    fps = config["video"]["fps"]
    audio_duration = get_audio_duration(wav, config)
    validate_audio_duration(audio_duration, config)
    words = transcribe_words(wav, script)
    chunks = build_caption_chunks(words, fps, config)
    tail_padding = render_config(config)["tail_padding_seconds"]
    timeline = build_visual_timeline(chunks, audio_duration + tail_padding, fps)
    write_caption_timing(words, chunks, timeline, wd / "caption_timing.json")

    scenes = build_scenes(timeline, config, wd, slug)

    concat = wd / "scenes.txt"
    write_concat(scenes, timeline, concat)

    out = wd / "short.mp4"
    music = pick_music_track(config)
    if music:
        meta["music"] = str(music.relative_to(ROOT))
        (wd / "metadata.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"Selected music: {music}")
    else:
        print("No background music found; rendering voice-only video.")

    ffmpeg_render(config, concat, wav, out, music)

    print(json.dumps({
        "title": meta["title"],
        "video": str(out),
        "output_dir": str(wd)
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

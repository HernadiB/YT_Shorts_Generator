import argparse
import json
import re
import random
import subprocess
import textwrap
import os
import ctypes
from dataclasses import dataclass
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
NUMBER_SUFFIXES = {
    "k": "thousand",
    "m": "million",
    "b": "billion",
    "t": "trillion",
}


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


def tag_candidates(value: Any):
    if isinstance(value, list):
        return [normalize(v) for v in value]

    if isinstance(value, str):
        return [t.strip() for t in re.split(r",|\|", value) if t.strip()]

    return []


def clean_tag(tag: str):
    tag = normalize(tag).replace("#", "")
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


def ask_ollama(topic, model, url):
    system_prompt = (PROMPTS / "system_prompt.txt").read_text(encoding="utf-8")
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
- use 65 to 78 spoken words
- keep the first second sharp, then slow the explanation down for comprehension
- make the main takeaway clear on first watch, but reward a replay with the
  example, contrast, or final line
- end by looping back to the opening hook naturally
- avoid textbook phrasing
- avoid robotic filler
- keep attention in the first 2 seconds
- explain one concept clearly
- explain one finance mechanism, not a list of generic tips
- include one tiny number example or concrete wallet-level scenario
- name one precise finance term only if it is translated into plain English
- write numbers, percentages, and currencies exactly as they should be spoken
- end with a short CTA

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

    r = requests.post(
        url,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        },
        timeout=300
    )

    r.raise_for_status()

    raw = r.json()["response"]
    cleaned = clean_json_response(raw)
    parsed = json.loads(cleaned)

    parsed["script"] = normalize(parsed.get("script"))
    parsed["script"] = normalize_spoken_numbers(parsed["script"])
    parsed["title"] = normalize(parsed.get("title"))
    parsed["description"] = normalize(parsed.get("description"))
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
        parsed["description"] = "Simple personal finance education for beginners.\n\nEducation only. Not financial advice."
    parsed["description"] = append_hashtags_to_description(
        parsed["description"],
        parsed["hashtags"],
    )

    if not parsed["script"]:
        raise ValueError("No usable script returned by Ollama.")

    return parsed


# ---------------------------
# 🎙 TTS (Piper)
# ---------------------------
def run_piper(script_text: str, config: dict, out_wav: Path):
    piper_exe_path = resolve_path(config["paths"]["piper_exe"])
    voice_model_path = resolve_path(config["paths"]["voice_model"])
    voice_config_path = resolve_path(config["paths"]["voice_config"])
    tts_config = config.get("tts", {})

    piper_exe = short_path(piper_exe_path)
    voice_model = short_path(voice_model_path)
    voice_config = short_path(voice_config_path)
    out_wav_short = short_output_path(out_wav)

    cmd = [
        piper_exe,
        "--model",
        voice_model,
        "--config",
        voice_config,
    ]

    for option in ["length_scale", "sentence_silence", "noise_scale", "noise_w"]:
        value = tts_config.get(option)
        if value is not None:
            cmd.extend([f"--{option}", str(value)])

    cmd.extend([
        "--output_file",
        out_wav_short,
    ])

    result = subprocess.run(
        cmd,
        input=script_text,
        text=True,
        capture_output=True,
        check=False
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Piper crashed.\n"
            f"Return code: {result.returncode}\n\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )


# ---------------------------
# 🧠 WhisperX timing
# ---------------------------
def round_to_frame(t, fps):
    return round(t * fps) / fps


def transcribe_words(audio_path: Path):
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
    max_seconds = config.get("video", {}).get("max_seconds")
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
        lines.append(f"duration {duration:.3f}")

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

    meta = ask_ollama(args.topic, model, url)

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
    words = transcribe_words(wav)
    chunks = build_caption_chunks(words, fps, config)
    timeline = build_visual_timeline(chunks, audio_duration, fps)
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

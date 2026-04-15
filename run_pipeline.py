import argparse
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
DEFAULT_TOPICS_FILE = ROOT / "topics.txt"
DEFAULT_AUTO_GENERATE_TOPICS = 20


def safe_slug(text: str):
    return re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")[:80]


def run_cmd(cmd):
    print("RUN:", " ".join(cmd))
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise SystemExit(result.returncode)
    return result.stdout


def latest_output_dir() -> Path:
    dirs = [p for p in OUTPUTS.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return dirs[0]


def read_topics(path: Path):
    if not path.exists():
        return []

    topics = []
    for line in path.read_text(encoding="utf-8").splitlines():
        topic = line.strip()
        if topic and not topic.startswith("#") and topic not in topics:
            topics.append(topic)

    return topics


def append_topics(path: Path, topics):
    existing = read_topics(path)
    existing_keys = {safe_slug(topic) for topic in existing}
    additions = []

    for topic in topics:
        if not topic:
            continue

        topic_key = safe_slug(topic)
        if topic_key in existing_keys:
            continue

        additions.append(topic)
        existing_keys.add(topic_key)

    if not additions:
        return []

    prefix = "\n" if path.exists() and path.read_text(encoding="utf-8").strip() else ""
    with path.open("a", encoding="utf-8") as f:
        f.write(prefix + "\n".join(additions) + "\n")

    return additions


def generated_topic_keys():
    keys = set()

    if not OUTPUTS.exists():
        return keys

    for output_dir in OUTPUTS.iterdir():
        if not output_dir.is_dir():
            continue

        keys.add(output_dir.name)
        metadata_path = output_dir / "metadata.json"
        if not metadata_path.exists():
            continue

        try:
            meta = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        for field in ["topic", "title"]:
            value = str(meta.get(field, "")).strip()
            if value:
                keys.add(safe_slug(value))

    return keys


def select_random_unused_topic(topics):
    unused = unused_topics(topics)

    if not unused:
        raise SystemExit("No unused topics left in topics.txt. Generate more with --generate-topics 20.")

    topic = random.choice(unused)
    print(f"Selected topic: {topic}")
    return topic


def unused_topics(topics):
    generated = generated_topic_keys()
    return [topic for topic in topics if safe_slug(topic) not in generated]


def ensure_unused_topic(topics_file: Path, auto_generate_count: int):
    auto_generate_count = max(0, int(auto_generate_count))
    topics = read_topics(topics_file)
    if not topics and auto_generate_count > 0:
        print(f"No topics found in {topics_file}. Generating {auto_generate_count} topics.")
        generate_topic_titles(auto_generate_count, topics_file)
        topics = read_topics(topics_file)

    unused = unused_topics(topics)
    if not unused and auto_generate_count > 0:
        print(
            f"No unused topics left in {topics_file}. "
            f"Generating {auto_generate_count} fresh topics."
        )
        generate_topic_titles(auto_generate_count, topics_file)
        topics = read_topics(topics_file)
        unused = unused_topics(topics)

    if not unused:
        raise SystemExit(
            f"No unused topics found in {topics_file}. "
            "Generate fresh topics with --generate-topics 20."
        )

    topic = random.choice(unused)
    print(f"Selected topic: {topic}")
    return topic


def clean_json_response(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()

    start = text.find("{")
    end = text.rfind("}")
    return text[start:end + 1]


def generate_topic_titles(count, topics_file: Path):
    load_dotenv(ROOT / ".env")
    model = os.getenv("OLLAMA_MODEL")
    url = os.getenv("OLLAMA_URL")

    if not model or not url:
        raise SystemExit("OLLAMA_MODEL and OLLAMA_URL must be set in .env before generating topics.")

    existing = read_topics(topics_file)
    prompt = f"""Create {count} original YouTube Shorts topic titles about beginner personal finance.

Audience: normal adults who want practical financial education that feels
slightly more professional than generic beginner content.

Channel position:
- Professional finance explained like a smart friend would explain it.
- Not a guru, not a bank, not a motivational channel.
- Series feel: Money Mechanics in 45 Seconds, The Hidden Cost, Finance Terms
  That Actually Matter, One Chart, One Lesson, What This Really Means For Your
  Wallet, Beginner Finance But Not Dumbed Down.

Rules:
- Write clean English titles only.
- Every title must be grammatically correct, natural, and easy to read aloud.
- Make every title a concrete, slightly contrarian financial statement.
- The first second must work as a hook, so avoid generic questions.
- Explain one financial mechanism per title, not a list of tips.
- Prefer titles that imply a hidden cost, misunderstood mechanism, or surprising
  wallet-level consequence.
- Avoid malformed finance terms, misleading claims, impossible causality,
  awkward word order, and sentence fragments.
- Avoid hype, clickbait, spam, investing guarantees, and duplicate ideas.
- Prefer topics about inflation, debt, fees, credit scores, ETFs, emergency
  funds, car payments, subscriptions, tax drag, liquidity, risk, compounding,
  index funds, cash flow, and long-term investing basics.
- If an existing topic already covers the same broad area, use a meaningfully
  different angle or mechanism. Near-duplicates are not useful.
- Match this style without repeating these examples:
  - Your savings account is not safe from inflation
  - The problem with debt is not the payment, it is the interest curve
  - An ETF is not boring, it is risk control in disguise
- Do not repeat any of these existing topics:
{json.dumps(existing, ensure_ascii=False)}

Return valid JSON only in this format:
{{
  "topics": ["string", "string"]
}}
"""

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
    parsed = json.loads(clean_json_response(raw))
    topics = parsed.get("topics", [])
    if not isinstance(topics, list):
        raise SystemExit("Ollama did not return a usable topics list.")

    cleaned = []
    for topic in topics:
        topic = str(topic).strip()
        if topic and topic not in cleaned:
            cleaned.append(topic)

    additions = append_topics(topics_file, cleaned)
    print(f"Added {len(additions)} new topics to {topics_file}:")
    for topic in additions:
        print(f"- {topic}")

    return additions


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic")
    parser.add_argument("--topics-file", default=str(DEFAULT_TOPICS_FILE))
    parser.add_argument("--generate-topics", type=int, default=0)
    parser.add_argument("--auto-generate-topics", type=int, default=DEFAULT_AUTO_GENERATE_TOPICS)
    parser.add_argument("--topics-only", action="store_true")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--privacy", default="private", choices=["private", "public", "unlisted"])
    args = parser.parse_args()

    topics_file = Path(args.topics_file)
    if not topics_file.is_absolute():
        topics_file = ROOT / topics_file

    if args.generate_topics:
        generate_topic_titles(args.generate_topics, topics_file)
        if args.topics_only:
            raise SystemExit(0)

    topic = args.topic
    if not topic:
        topic = ensure_unused_topic(topics_file, args.auto_generate_topics)

    py = sys.executable

    run_cmd([py, str(ROOT / "generate_short.py"), "--topic", topic])
    out_dir = latest_output_dir()
    print(f"Generated at: {out_dir}")

    if args.upload:
        run_cmd([
            py, str(ROOT / "upload_youtube.py"),
            "--video", str(out_dir / "short.mp4"),
            "--metadata", str(out_dir / "metadata.json"),
            "--privacy", args.privacy,
        ])

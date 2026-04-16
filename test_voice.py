from pathlib import Path
import json

from generate_short import run_piper

ROOT = Path(__file__).resolve().parent

with open(ROOT / "config.json", "r", encoding="utf-8-sig") as f:
    config = json.load(f)

text = """Most beginners think investing is complicated.
It isn't.
An ETF lets you buy many companies in one move.
That's why it's one of the easiest ways to start."""

out = ROOT / "test_voice.wav"

run_piper(text, config, out)
print(f"Done: {out}")

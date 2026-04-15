import subprocess
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent

with open(ROOT / "config.json", "r", encoding="utf-8-sig") as f:
    config = json.load(f)

text = """Most beginners think investing is complicated.
It isn't.
An ETF lets you buy many companies in one move.
That's why it's one of the easiest ways to start."""

out = ROOT / "test_voice.wav"

cmd = [
    config["paths"]["piper_exe"],
    "--model",
    config["paths"]["voice_model"],
    "--config",
    config["paths"]["voice_config"],
    "--output_file",
    str(out)
]

for option in ["length_scale", "sentence_silence", "noise_scale", "noise_w"]:
    value = config.get("tts", {}).get(option)
    if value is not None:
        cmd.extend([f"--{option}", str(value)])

subprocess.run(cmd, input=text, text=True, check=True)
print(f"Done: {out}")

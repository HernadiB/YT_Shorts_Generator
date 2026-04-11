import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--privacy", default="private", choices=["private", "public", "unlisted"])
    args = parser.parse_args()

    py = sys.executable

    run_cmd([py, str(ROOT / "generate_short.py"), "--topic", args.topic])
    out_dir = latest_output_dir()
    print(f"Generated at: {out_dir}")

    if args.upload:
        run_cmd([
            py, str(ROOT / "upload_youtube.py"),
            "--video", str(out_dir / "short.mp4"),
            "--metadata", str(out_dir / "metadata.json"),
            "--privacy", args.privacy,
        ])
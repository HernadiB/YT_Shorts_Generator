import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def safe_slug(text: str):
    return re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")[:80]


def load_config():
    with open(ROOT / "config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_path(path):
    path = Path(path)
    if path.is_absolute():
        return path
    return ROOT / path


def build_prompt(topic, index):
    styles = [
        "clean editorial finance background, modern banking app atmosphere",
        "abstract stock market chart background, premium fintech visual style",
        "personal budgeting desk scene, financial planning mood",
        "minimal investment education background, soft depth of field",
        "macro finance concept background, subtle charts and numbers",
    ]
    return (
        f"{styles[index % len(styles)]}, topic: {topic}, "
        "vertical 9:16 composition, cinematic lighting, sharp details, "
        "no text, no letters, no logos, no watermark, no people, uncluttered center"
    )


def generate_backgrounds(topic, count, force=False):
    try:
        import torch
        from diffusers import AutoPipelineForText2Image
    except ImportError as exc:
        raise SystemExit(
            "Diffusers background generation dependencies are missing. "
            "Run: pip install diffusers transformers accelerate torch"
        ) from exc

    config = load_config()
    background_config = config.get("backgrounds", {})
    model_id = background_config.get("diffusers_model", "stabilityai/sd-turbo")
    steps = int(background_config.get("diffusers_steps", 4))
    guidance_scale = float(background_config.get("diffusers_guidance_scale", 0.0))
    seed = int(background_config.get("diffusers_seed", 42))
    width = int(background_config.get("diffusers_width", 768))
    height = int(background_config.get("diffusers_height", 1344))

    slug = safe_slug(topic)
    out_dir = resolve_path(background_config.get("image_dir", "assets/backgrounds")) / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    existing = sorted(out_dir.glob("*.png"))
    if existing and not force:
        print(f"Backgrounds already exist in {out_dir}. Use --force to regenerate.")
        return out_dir

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    pipe = AutoPipelineForText2Image.from_pretrained(
        model_id,
        torch_dtype=dtype,
        variant="fp16" if device == "cuda" else None,
    )
    pipe = pipe.to(device)

    if hasattr(pipe, "enable_attention_slicing"):
        pipe.enable_attention_slicing()

    generator = torch.Generator(device=device).manual_seed(seed)

    for i in range(count):
        prompt = build_prompt(topic, i)
        image = pipe(
            prompt=prompt,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            generator=generator,
        ).images[0]

        path = out_dir / f"bg_{i + 1:02d}.png"
        image.save(path)
        print(f"Saved {path}")

    return out_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    generate_backgrounds(args.topic, args.count, args.force)

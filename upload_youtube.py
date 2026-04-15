import argparse
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).resolve().parent
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
DEFAULT_TAGS = ["personal finance", "finance", "money", "financial education"]
DEFAULT_HASHTAGS = ["#Shorts", "#PersonalFinance", "#FinanceTips"]
MAX_YOUTUBE_TAG_CHARS = 480


def resolve_path(p):
    p = Path(p)
    if p.is_absolute():
        return p
    return ROOT / p


def load_config():
    with open(ROOT / "config.json", "r", encoding="utf-8-sig") as f:
        return json.load(f)


def metadata_items(value):
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]

    if isinstance(value, str):
        return [item.strip() for item in re.split(r",|\|", value) if item.strip()]

    return []


def normalize_tags(value):
    tags = metadata_items(value) or DEFAULT_TAGS
    cleaned = []
    seen = set()
    total_chars = 0

    for tag in tags:
        tag = re.sub(r"\s+", " ", tag.replace("#", "")).strip(" ,|#")[:60]
        key = tag.casefold()
        if not tag or key in seen:
            continue

        next_total = total_chars + len(tag) + (1 if cleaned else 0)
        if next_total > MAX_YOUTUBE_TAG_CHARS:
            continue

        cleaned.append(tag)
        seen.add(key)
        total_chars = next_total

    return cleaned or DEFAULT_TAGS


def hashtag_from_text(text: str):
    text = str(text).strip()
    if re.fullmatch(r"#[A-Za-z0-9_]+", text):
        return text[:51]

    parts = re.findall(r"[A-Za-z0-9]+", text)
    if not parts:
        return ""

    pieces = [part if part.isupper() else part.capitalize() for part in parts]
    return f"#{''.join(pieces)[:50]}"


def normalize_hashtags(value, fallback_tags):
    hashtags = ["#Shorts"]
    seen = {"#shorts"}

    for candidate in metadata_items(value) + fallback_tags + DEFAULT_HASHTAGS:
        hashtag = hashtag_from_text(candidate)
        key = hashtag.casefold()
        if hashtag and key not in seen:
            hashtags.append(hashtag)
            seen.add(key)

        if len(hashtags) >= 3:
            break

    return hashtags


def description_with_hashtags(description: str, hashtags):
    description = (description or "Education only. Not financial advice.").strip()
    missing = [
        hashtag for hashtag in hashtags
        if hashtag.casefold() not in description.casefold()
    ]

    if missing:
        return f"{description}\n\n{' '.join(missing)}"

    return description


def get_credentials(client_secret_path: Path, token_path: Path) -> Credentials:
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
        creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def upload_video(video_path: Path, metadata_path: Path, privacy_status: str):
    config = load_config()
    upload_defaults = config.get("upload_defaults", {})

    video_path = resolve_path(video_path)
    metadata_path = resolve_path(metadata_path)

    meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    tags = normalize_tags(meta.get("tags"))
    hashtags = normalize_hashtags(meta.get("hashtags"), tags)
    description = description_with_hashtags(
        meta.get("description", "Education only. Not financial advice."),
        hashtags,
    )
    category_id = str(
        upload_defaults.get("category_id")
        or os.getenv("YOUTUBE_CATEGORY_ID")
        or "27"
    )
    language = upload_defaults.get("default_language") or config.get("language", "en")
    audio_language = upload_defaults.get("default_audio_language") or language
    made_for_kids = bool(upload_defaults.get("made_for_kids", False))

    client_secret_path = resolve_path(config["paths"]["client_secret_json"])
    token_path = resolve_path("token.json")

    creds = get_credentials(client_secret_path, token_path)
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": meta.get("title", "Finance Short")[:100],
            "description": description,
            "tags": tags,
            "categoryId": category_id,
            "defaultLanguage": language,
            "defaultAudioLanguage": audio_language,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": made_for_kids,
            "embeddable": bool(upload_defaults.get("embeddable", True)),
            "publicStatsViewable": bool(upload_defaults.get("public_stats_viewable", True)),
            "license": upload_defaults.get("license", "youtube")
        }
    }

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")

    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--privacy", default="private", choices=["private", "public", "unlisted"])
    args = parser.parse_args()

    upload_video(args.video, args.metadata, args.privacy)

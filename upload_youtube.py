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
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).resolve().parent
SCOPES = ["https://www.googleapis.com/auth/youtube"]
CHANNEL_STATE_FILE = ROOT / "channel_state.json"
DEFAULT_TAGS = ["personal finance", "finance", "money", "financial education"]
DEFAULT_HASHTAGS = ["#Shorts", "#PersonalFinance", "#FinanceTips"]
MAX_YOUTUBE_TAG_CHARS = 480


def resolve_path(p):
    p = Path(p)
    if p.is_absolute():
        return p
    return ROOT / p


def load_config():
    return load_json(ROOT / "config.json")


def load_json(path: Path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_optional_json(path: Path):
    if not path.exists():
        return {}

    return load_json(path)


def normalize_title(title: str):
    return " ".join(str(title).split()).casefold()


def token_scopes(token_path: Path):
    if not token_path.exists():
        return set()

    try:
        token = json.loads(token_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()

    scopes = token.get("scopes") or []
    if isinstance(scopes, str):
        return set(scopes.split())

    if isinstance(scopes, list):
        return {str(scope) for scope in scopes}

    return set()


def token_has_required_scopes(token_path: Path):
    return set(SCOPES).issubset(token_scopes(token_path))


def metadata_items(value):
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]

    if isinstance(value, str):
        return [item.strip() for item in re.split(r",|\|", value) if item.strip()]

    return []


def flatten_metadata_text(value):
    if value is None:
        return []

    if isinstance(value, dict):
        items = []
        for nested in value.values():
            items.extend(flatten_metadata_text(nested))
        return items

    if isinstance(value, list):
        items = []
        for nested in value:
            items.extend(flatten_metadata_text(nested))
        return items

    text = str(value).strip()
    return [text] if text else []


def metadata_text(meta):
    fields = [
        "topic",
        "title",
        "description",
        "tags",
        "hashtags",
        "search_keywords",
        "sections",
        "script",
        "playlist",
        "series",
    ]
    pieces = []
    for field in fields:
        pieces.extend(flatten_metadata_text(meta.get(field)))
    return " ".join(pieces).casefold()


def playlist_title_map(state):
    return {
        normalize_title(title): title
        for title in state.get("playlists", {})
        if str(title).strip()
    }


def canonical_playlist_title(title, state):
    return playlist_title_map(state).get(normalize_title(title))


def add_unique_playlist_title(selected, title, state):
    canonical = canonical_playlist_title(title, state)
    if not canonical:
        return

    if canonical not in selected:
        selected.append(canonical)


def keyword_match_count(text, keyword):
    keyword = str(keyword).strip().casefold()
    if not keyword:
        return 0

    escaped = re.escape(keyword)
    if re.search(r"\s", keyword):
        return len(re.findall(escaped, text))

    return len(re.findall(rf"\b{escaped}\b", text))


def select_playlist_titles(meta, state):
    routing = state.get("upload_routing", {})
    selected = []
    explicit_titles = []

    for field in ["playlist", "series"]:
        for candidate in metadata_items(meta.get(field)):
            canonical = canonical_playlist_title(candidate, state)
            if canonical and canonical not in explicit_titles:
                explicit_titles.append(canonical)

    text = metadata_text(meta)
    best_playlist = None
    best_score = 0

    for rule in routing.get("rules", []):
        playlist = rule.get("playlist")
        score = 0
        for keyword in rule.get("keywords", []):
            weight = 2 if re.search(r"\s", str(keyword).strip()) else 1
            score += keyword_match_count(text, keyword) * weight

        if score > best_score:
            best_playlist = playlist
            best_score = score

    if best_playlist and best_score > 0:
        add_unique_playlist_title(selected, best_playlist, state)
    else:
        for title in explicit_titles:
            add_unique_playlist_title(selected, title, state)

    for title in routing.get("always_add_playlists", []):
        add_unique_playlist_title(selected, title, state)

    if not selected:
        default_playlist = routing.get("default_playlist")
        add_unique_playlist_title(selected, default_playlist, state)

    return selected


def resolve_playlist_ids(titles, state):
    playlists = state.get("playlists", {})
    normalized_ids = {
        normalize_title(title): (title, playlist_id)
        for title, playlist_id in playlists.items()
        if str(playlist_id).strip()
    }

    resolved = []
    for title in titles:
        match = normalized_ids.get(normalize_title(title))
        if match:
            resolved.append(match)

    return resolved


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

    if token_path.exists() and token_has_required_scopes(token_path):
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    elif token_path.exists():
        print(
            "Existing token.json does not include playlist management scope; "
            "opening OAuth again."
        )

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
        creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def video_in_playlist(youtube, playlist_id, video_id):
    response = youtube.playlistItems().list(
        part="id",
        playlistId=playlist_id,
        videoId=video_id,
        maxResults=1,
    ).execute()
    return bool(response.get("items"))


def add_video_to_playlist(youtube, playlist_id, video_id):
    return youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id,
                },
            },
        },
    ).execute()


def assign_playlists(youtube, video_id, meta, skip_playlists: bool):
    if skip_playlists:
        print("Playlist assignment skipped by --skip-playlists.")
        return []

    state = load_optional_json(CHANNEL_STATE_FILE)
    if not state:
        print(
            "No channel_state.json found; skipping playlist assignment. "
            "Run python setup_channel.py --apply or --write-state first."
        )
        return []

    titles = select_playlist_titles(meta, state)
    if not titles:
        print("No playlist matched the metadata; skipping playlist assignment.")
        return []

    playlist_refs = resolve_playlist_ids(titles, state)
    resolved_titles = {title for title, _playlist_id in playlist_refs}
    for title in titles:
        if title not in resolved_titles:
            print(f"Playlist ID missing in channel_state.json: {title}")

    assigned = []
    for title, playlist_id in playlist_refs:
        try:
            if video_in_playlist(youtube, playlist_id, video_id):
                print(f"Already in playlist: {title}")
            else:
                add_video_to_playlist(youtube, playlist_id, video_id)
                print(f"Added to playlist: {title}")
            assigned.append(title)
        except HttpError as exc:
            raise RuntimeError(
                f"Could not add video {video_id} to playlist {title}."
            ) from exc

    return assigned


def upload_video(
    video_path: Path,
    metadata_path: Path,
    privacy_status: str,
    skip_playlists: bool = False,
):
    config = load_config()
    upload_defaults = config.get("upload_defaults", {})

    video_path = resolve_path(video_path)
    metadata_path = resolve_path(metadata_path)

    meta = load_json(metadata_path)
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

    video_id = response.get("id")
    assigned_playlists = []
    if video_id:
        assigned_playlists = assign_playlists(
            youtube,
            video_id,
            meta,
            skip_playlists,
        )

    print(json.dumps({
        "upload": response,
        "assigned_playlists": assigned_playlists,
    }, indent=2))


if __name__ == "__main__":
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--privacy", default="private", choices=["private", "public", "unlisted"])
    parser.add_argument("--skip-playlists", action="store_true")
    args = parser.parse_args()

    upload_video(args.video, args.metadata, args.privacy, args.skip_playlists)

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parent
SCOPES = ["https://www.googleapis.com/auth/youtube"]
TOKEN_FILE = ROOT / "channel_token.json"
CHANNEL_STATE_FILE = ROOT / "channel_state.json"
DEFAULT_PROFILE = ROOT / "channel_profile.json"


def load_json(path: Path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_config():
    return load_json(ROOT / "config.json")


def get_credentials(client_secret_path: Path) -> Credentials:
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
        creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    return creds


def normalize_title(title: str):
    return " ".join(str(title).split()).casefold()


def is_real_playlist_id(playlist_id: str):
    return playlist_id and not str(playlist_id).startswith("DRY_RUN_")


def keywords_to_api_string(keywords):
    cleaned = []
    seen = set()

    for keyword in keywords:
        keyword = " ".join(str(keyword).split())
        key = keyword.casefold()
        if not keyword or key in seen:
            continue
        seen.add(key)
        if " " in keyword:
            cleaned.append(f'"{keyword}"')
        else:
            cleaned.append(keyword)

    return " ".join(cleaned)


def get_own_channel(youtube):
    response = youtube.channels().list(
        part="id,brandingSettings",
        mine=True,
        maxResults=1,
    ).execute()
    items = response.get("items", [])
    if not items:
        raise RuntimeError("No YouTube channel found for the authorized account.")
    return items[0]


def print_manual_checklist(profile):
    print("\nManual YouTube Studio checklist:")
    for item in profile.get("manual_studio_checklist", []):
        print(f"- {item}")

    if profile.get("banner_headline") or profile.get("banner_subtitle"):
        print("\nBanner copy:")
        print(profile.get("banner_headline", ""))
        print(profile.get("banner_subtitle", ""))

    if profile.get("default_video_description"):
        print("\nUpload defaults description:")
        print(profile["default_video_description"])

    if profile.get("pinned_comment_template"):
        print("\nPinned comment template:")
        print(profile["pinned_comment_template"])


def apply_branding(youtube, channel, profile, apply_changes: bool):
    channel_id = channel["id"]
    branding = channel.get("brandingSettings", {})
    channel_branding = dict(branding.get("channel", {}))
    image_branding = dict(branding.get("image", {}))

    updates = {
        "description": profile["description"].strip(),
        "keywords": keywords_to_api_string(profile.get("keywords", [])),
        "defaultLanguage": profile.get("default_language", "en"),
    }

    if profile.get("country"):
        updates["country"] = profile["country"]

    channel_branding.update(updates)

    body = {
        "id": channel_id,
        "brandingSettings": {
            "channel": channel_branding,
        },
    }
    if image_branding:
        body["brandingSettings"]["image"] = image_branding

    print("\nChannel branding:")
    print(f"- Description: {profile['description'].splitlines()[0]}")
    print(f"- Keywords: {', '.join(profile.get('keywords', []))}")
    print(f"- Default language: {updates['defaultLanguage']}")
    if updates.get("country"):
        print(f"- Country: {updates['country']}")

    if not apply_changes:
        print("DRY RUN: channel branding was not updated.")
        return

    youtube.channels().update(part="brandingSettings", body=body).execute()
    print("Updated channel branding.")


def list_playlists(youtube):
    playlists = {}
    request = youtube.playlists().list(
        part="id,snippet,status",
        mine=True,
        maxResults=50,
    )

    while request is not None:
        response = request.execute()
        for item in response.get("items", []):
            title = item.get("snippet", {}).get("title", "")
            playlists[normalize_title(title)] = item
        request = youtube.playlists().list_next(request, response)

    return playlists


def ensure_playlists(youtube, profile, apply_changes: bool):
    existing = list_playlists(youtube)
    playlist_ids = {}

    print("\nPlaylists:")
    for playlist in profile.get("playlists", []):
        title = playlist["title"]
        key = normalize_title(title)
        existing_item = existing.get(key)

        if existing_item:
            playlist_ids[title] = existing_item["id"]
            print(f"- Exists: {title}")
            continue

        print(f"- Create: {title}")
        if not apply_changes:
            playlist_ids[title] = f"DRY_RUN_PLAYLIST_{len(playlist_ids) + 1}"
            continue

        body = {
            "snippet": {
                "title": title,
                "description": playlist.get("description", ""),
                "defaultLanguage": profile.get("default_language", "en"),
            },
            "status": {
                "privacyStatus": playlist.get("privacy_status", "public"),
            },
        }
        response = youtube.playlists().insert(
            part="snippet,status",
            body=body,
        ).execute()
        playlist_ids[title] = response["id"]

    if not apply_changes:
        print("DRY RUN: missing playlists were not created.")

    return playlist_ids


def existing_profile_playlist_ids(youtube, profile):
    existing = list_playlists(youtube)
    playlist_ids = {}

    for playlist in profile.get("playlists", []):
        title = playlist["title"]
        existing_item = existing.get(normalize_title(title))
        if existing_item:
            playlist_ids[title] = existing_item["id"]

    return playlist_ids


def write_channel_state(channel, profile, playlist_ids, state_path: Path):
    real_playlist_ids = {
        title: playlist_id
        for title, playlist_id in playlist_ids.items()
        if is_real_playlist_id(playlist_id)
    }

    if not real_playlist_ids:
        print(
            "\nNo real playlist IDs available for channel_state.json. "
            "Run setup_channel.py --apply after playlists are created."
        )
        return

    state = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "channel_id": channel["id"],
        "recommended_channel_name": profile.get("recommended_channel_name"),
        "recommended_handle": profile.get("recommended_handle"),
        "default_language": profile.get("default_language", "en"),
        "country": profile.get("country"),
        "playlists": real_playlist_ids,
        "upload_routing": profile.get("upload_routing", {}),
        "home_sections": profile.get("home_sections", []),
    }

    state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nSaved playlist routing state to {state_path}.")


def list_channel_sections(youtube):
    sections = {}
    response = youtube.channelSections().list(
        part="id,snippet,contentDetails",
        mine=True,
    ).execute()

    for item in response.get("items", []):
        snippet = item.get("snippet", {})
        title = snippet.get("title") or snippet.get("type") or ""
        sections[normalize_title(title)] = item

    return sections


def ensure_home_sections(youtube, profile, playlist_ids, apply_changes: bool):
    existing = list_channel_sections(youtube)

    print("\nHome tab sections:")
    for title in profile.get("home_sections", []):
        playlist_id = playlist_ids.get(title)
        if not playlist_id:
            print(f"- Skipped, playlist id unavailable: {title}")
            continue

        key = normalize_title(title)
        if key in existing:
            print(f"- Exists: {title}")
            continue

        print(f"- Create section: {title}")
        if not apply_changes:
            continue

        body = {
            "snippet": {
                "type": "singlePlaylist",
                "style": "horizontalRow",
                "title": title,
            },
            "contentDetails": {
                "playlists": [playlist_id],
            },
        }
        youtube.channelSections().insert(
            part="snippet,contentDetails",
            body=body,
        ).execute()

    if not apply_changes:
        print("DRY RUN: missing home sections were not created.")


def main():
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--skip-branding", action="store_true")
    parser.add_argument("--skip-playlists", action="store_true")
    parser.add_argument("--skip-sections", action="store_true")
    parser.add_argument(
        "--write-state",
        action="store_true",
        help="Save existing playlist IDs to channel_state.json without applying changes.",
    )
    args = parser.parse_args()

    profile_path = Path(args.profile)
    if not profile_path.is_absolute():
        profile_path = ROOT / profile_path

    profile = load_json(profile_path)
    config = load_config()
    client_secret_path = ROOT / config["paths"]["client_secret_json"]

    print("Channel setup mode:", "APPLY" if args.apply else "DRY RUN")
    print("Do not paste OAuth tokens into chat. This script uses local browser OAuth.")

    creds = get_credentials(client_secret_path)
    youtube = build("youtube", "v3", credentials=creds)
    channel = get_own_channel(youtube)

    if not args.skip_branding:
        apply_branding(youtube, channel, profile, args.apply)

    playlist_ids = {}
    if not args.skip_playlists:
        playlist_ids = ensure_playlists(youtube, profile, args.apply)
    elif args.write_state:
        playlist_ids = existing_profile_playlist_ids(youtube, profile)

    if not args.skip_sections:
        ensure_home_sections(youtube, profile, playlist_ids, args.apply)

    if args.apply or args.write_state:
        write_channel_state(channel, profile, playlist_ids, CHANNEL_STATE_FILE)

    print_manual_checklist(profile)


if __name__ == "__main__":
    main()

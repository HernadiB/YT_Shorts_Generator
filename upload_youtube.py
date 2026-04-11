import argparse
import json
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).resolve().parent
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def resolve_path(p):
    p = Path(p)
    if p.is_absolute():
        return p
    return ROOT / p


def load_config():
    with open(ROOT / "config.json", "r", encoding="utf-8") as f:
        return json.load(f)


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

    video_path = resolve_path(video_path)
    metadata_path = resolve_path(metadata_path)

    meta = json.loads(metadata_path.read_text(encoding="utf-8"))

    client_secret_path = resolve_path(config["paths"]["client_secret_json"])
    token_path = resolve_path("token.json")

    creds = get_credentials(client_secret_path, token_path)
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": meta.get("title", "Finance Short")[:100],
            "description": meta.get("description", "Education only. Not financial advice."),
            "tags": meta.get("tags", ["finance", "money", "education"]),
            "categoryId": "27",
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
            "embeddable": True,
            "publicStatsViewable": True,
            "license": "youtube"
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
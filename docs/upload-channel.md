# Upload And Channel Setup

## Upload An Existing Video

```powershell
python upload_youtube.py --video "outputs/<slug>/short.mp4" --metadata "outputs/<slug>/metadata.json" --privacy private
```

The uploader reads title, description, tags, hashtags, and playlist routing from
the generated metadata. It uses the YouTube account authorized by local OAuth.

## Generate And Upload

```powershell
python run_pipeline.py --topic "How inflation quietly destroys cash savings" --upload --privacy private
```

Supported privacy values:

```powershell
--privacy private
--privacy unlisted
--privacy public
```

Use private uploads first until output quality is stable.

## OAuth Files

Local-only files:

- `client_secret.json`
- `token.json`
- `channel_token.json`
- `channel_state.json`

Do not commit or paste OAuth tokens into chat.

## First Upload Setup

1. Create a Google Cloud project.
2. Enable YouTube Data API v3.
3. Create an OAuth Client ID for a Desktop App.
4. Download the credentials JSON.
5. Rename it to `client_secret.json`.
6. Place it in the repository root.

The first upload opens a browser login flow and creates `token.json`.

## Channel Setup

Preview channel setup:

```powershell
python setup_channel.py
```

Apply channel description, keywords, playlists, and playlist sections:

```powershell
python setup_channel.py --apply
```

Refresh saved playlist IDs:

```powershell
python setup_channel.py --write-state --skip-branding --skip-sections
```

The setup token is separate from the upload token. `channel_state.json` stores
account-specific playlist IDs and remains ignored by git.

Manual YouTube Studio work still includes channel name, handle, profile picture,
banner upload, upload defaults, paid promotion disclosure, and altered/synthetic
disclosure decisions.

# Finance Shorts Factory

Local Python pipeline for generating faceless English YouTube Shorts about
beginner finance topics.

It uses local tools for the heavy work:

- Ollama for script and metadata generation.
- Piper for text-to-speech.
- WhisperX for word-level caption timing.
- Pillow for scene image generation.
- FFmpeg and FFprobe for final rendering.
- YouTube Data API v3 for optional private-first upload.

The default output is a vertical 1080x1920 Short with reviewed script metadata,
synced captions, generated or topic-specific backgrounds, optional background
music, and YouTube-ready metadata.

## Quick Start

First-time Windows setup:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup_windows.ps1
```

Daily development session:

```powershell
.\start_dev.ps1
```

Generate one Short:

```powershell
.\.venv\Scripts\python.exe run_pipeline.py --topic "What an ETF is in under 60 seconds"
```

Stop local dev services:

```powershell
.\stop_dev.ps1
```

## Documentation

The detailed README content has been split into focused docs:

| Topic | File |
| --- | --- |
| Setup and local development | [docs/setup.md](docs/setup.md) |
| Content and quality standards | [docs/content-quality.md](docs/content-quality.md) |
| Generation and rendering | [docs/generation.md](docs/generation.md) |
| Upload and channel setup | [docs/upload-channel.md](docs/upload-channel.md) |
| CI, troubleshooting, and operating workflow | [docs/operations.md](docs/operations.md) |
| Releases and packages | [docs/release-package.md](docs/release-package.md) |
| GitHub governance and setup log | [docs/github-governance.md](docs/github-governance.md) |

## Project Structure

```text
YT_Shorts_Generator/
|-- generate_short.py                 # Generate script, voice, scenes, and final video
|-- run_pipeline.py                   # Generate one Short and optionally upload it
|-- upload_youtube.py                 # Upload an existing rendered Short to YouTube
|-- setup_channel.py                  # Apply channel branding, playlists, and sections
|-- test_voice.py                     # Quick Piper voice test
|-- setup_windows.ps1                 # Windows installer/bootstrap helper
|-- start_dev.ps1                     # Start local development services
|-- stop_dev.ps1                      # Stop local development services
|-- CONTRIBUTING.md                   # Development and review guidance
|-- SECURITY.md                       # Security policy and private reporting guidance
|-- requirements.txt                  # Python dependencies
|-- config.example.json               # Template for local config.json
|-- channel_profile.json              # Public channel positioning config
|-- .env.example                      # Template for local .env
|-- topics.txt                        # Topic pool for random generation
|-- docs/                             # Focused project documentation
|-- prompts/
|   `-- system_prompt.txt             # Script and metadata prompt
|-- assets/
|   |-- backgrounds/                  # Optional background images
|   |-- images/                       # Documentation diagrams and public images
|   `-- music/
|       `-- library/                  # Optional local music files, ignored by git
|-- outputs/                          # Generated videos and intermediates, ignored by git
`-- voices/                           # Optional local Piper install/voices, ignored by git
```

Local-only files such as `.env`, `config.json`, `client_secret.json`,
`token.json`, `channel_token.json`, `channel_state.json`, `.venv/`, `outputs/`,
generated media, and voice assets must not be committed.

## Core Commands

Run static checks:

```powershell
python -m compileall -q generate_short.py run_pipeline.py setup_channel.py upload_youtube.py test_voice.py
ruff check --output-format=github .
bandit -q -r . --severity-level medium --confidence-level high -x ./.git,./.venv,./outputs,./voices,./assets/music
```

Generate topics only:

```powershell
python run_pipeline.py --generate-topics 20 --topics-only
```

Generate and upload privately:

```powershell
python run_pipeline.py --topic "ETF basics" --upload --privacy private
```

Create a release tag:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

## Operating Standard

- Generate videos as private first.
- Review finance accuracy, voice quality, caption sync, background relevance,
  and metadata before publishing.
- Keep each PR focused and labeled.
- Use milestones for planned work.
- Keep generated media and secrets out of git.
- Treat this repository as source for local automation, not as a place to store
  rendered Shorts or OAuth state.

Education only. Not financial advice.

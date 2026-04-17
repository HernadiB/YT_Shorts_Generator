# Setup And Local Development

## Prerequisites

- Python 3.11+
- Git
- FFmpeg and FFprobe in `PATH`
- Ollama
- Piper with an English voice model
- Optional Google Cloud OAuth credentials for YouTube upload

Quick checks:

```powershell
py --version
git --version
ffmpeg -version
ffprobe -version
ollama --version
```

## First-Time Setup

Run the Windows setup helper:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup_windows.ps1
```

Useful options:

```powershell
.\setup_windows.ps1 -ForceConfig
.\setup_windows.ps1 -SkipToolInstall
.\setup_windows.ps1 -SkipPiperDownload
.\setup_windows.ps1 -SkipOllamaPull
.\setup_windows.ps1 -OllamaModel "llama3.1:8b" -PiperVoice "en_US-lessac-medium"
```

The setup script owns installation/bootstrap work. The daily dev scripts should
not duplicate installer logic.

## Daily Development

Start local services and verify the Python environment:

```powershell
.\start_dev.ps1
```

Stop local services:

```powershell
.\stop_dev.ps1
```

If PowerShell blocks script execution:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_dev.ps1
powershell -ExecutionPolicy Bypass -File .\stop_dev.ps1
```

`start_dev.ps1` loads `.env`, starts Ollama when needed, verifies the configured
model, writes `.dev/services.json`, and stores startup logs under `.dev/`.

## Local Config

Create local config files from templates if they do not exist:

```powershell
Copy-Item .env.example .env
Copy-Item config.example.json config.json
```

Important `.env` fields:

```text
OLLAMA_MODEL=llama3.1:8b
OLLAMA_URL=http://localhost:11434/api/generate
CHANNEL_DEFAULT_PRIVACY=private
YOUTUBE_CATEGORY_ID=27
```

Important `config.json` areas:

- `video`: dimensions, FPS, min/max duration, caption mode.
- `tts`: Piper speech pace.
- `paths`: Piper, voice model, FFmpeg, FFprobe, OAuth client path.
- `music`: optional local background music directory.
- `upload_defaults`: YouTube upload defaults.

Never commit `.env`, `config.json`, OAuth files, token files, generated media,
or local voice assets.

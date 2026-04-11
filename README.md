# Finance Shorts Factory

Local Python pipeline for generating faceless English YouTube Shorts about beginner finance topics.

It uses:

- Ollama for local script and metadata generation
- Piper for local text-to-speech
- WhisperX for word-level audio timing
- Pillow for scene image generation
- FFmpeg and FFprobe for final video rendering
- YouTube Data API v3 for optional upload

The default output is a vertical 1080x1920 short with semantic caption blocks, synced voice, generated or topic-specific backgrounds, optional background music, and YouTube-ready metadata.

## Project Structure

```text
YT_Shorts_Generator/
|-- generate_short.py                 # Generate script, voice, scenes, and final video
|-- run_pipeline.py                   # Generate one short and optionally upload it
|-- upload_youtube.py                 # Upload an existing rendered short to YouTube
|-- test_voice.py                     # Quick Piper voice test
|-- setup_windows.ps1                 # Human-readable Windows setup helper
|-- requirements.txt                  # Python dependencies
|-- config.example.json               # Template for local config.json
|-- .env.example                      # Template for local .env
|-- topics.txt                        # Topic pool for random generation
|-- prompts/
|   `-- system_prompt.txt             # Script and metadata prompt for the local LLM
|-- assets/
|   |-- backgrounds/
|   |   `-- default/                  # Optional fallback background images
|   |-- images/                       # README diagrams
|   `-- music/
|       `-- library/                  # Optional local music files, ignored by git
|-- outputs/                          # Generated videos and intermediate files, ignored by git
|   `-- <video-slug>/
|       |-- script.txt
|       |-- metadata.json
|       |-- voice.wav
|       |-- scenes/
|       |-- scenes.txt
|       `-- short.mp4
`-- voices/                           # Optional local Piper install/voices, ignored by git
```

Local-only files such as `.env`, `config.json`, `client_secret.json`, `token.json`, `.venv/`, `outputs/`, generated media, and voice assets should not be committed.

## Prerequisites

Install these before running the project on a fresh Windows machine:

- Python 3.11+
- Git
- FFmpeg with `ffmpeg` and `ffprobe` available in `PATH`
- Ollama for local LLM generation
- Piper with at least one English voice model
- Optional: Google Cloud OAuth credentials for YouTube upload

Quick checks:

```powershell
py --version
git --version
ffmpeg -version
ffprobe -version
ollama --version
```

## Fresh Machine Setup

Clone the repository:

```powershell
git clone https://github.com/HernadiB/YT_Shorts_Generator.git
cd YT_Shorts_Generator
git checkout development
```

Create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation scripts:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Install Python dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create local config files:

```powershell
Copy-Item config.example.json config.json
Copy-Item .env.example .env
```

Pull the default local Ollama model:

```powershell
ollama pull llama3.1:8b
```

Start Ollama in a separate terminal if it is not already running:

```powershell
ollama serve
```

You can automate the Windows setup with the included script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup_windows.ps1
```

Useful setup script options:

```powershell
.\setup_windows.ps1 -ForceConfig
.\setup_windows.ps1 -SkipToolInstall
.\setup_windows.ps1 -SkipPiperDownload
.\setup_windows.ps1 -SkipOllamaPull
.\setup_windows.ps1 -OllamaModel "llama3.1:8b" -PiperVoice "en_US-lessac-medium"
```

## Configure `.env`

Default `.env.example`:

```text
OLLAMA_MODEL=llama3.1:8b
OLLAMA_URL=http://localhost:11434/api/generate
CHANNEL_DEFAULT_PRIVACY=private
YOUTUBE_CATEGORY_ID=27
```

Use a different local model by changing `OLLAMA_MODEL`, then pull it with Ollama.

## Configure `config.json`

Edit `config.json` after copying it from `config.example.json`.

Important fields:

```json
{
  "video": {
    "width": 1080,
    "height": 1920,
    "fps": 30,
    "max_seconds": 55,
    "captions": {
      "mode": "semantic",
      "min_words": 3,
      "max_words": 8,
      "max_seconds": 3.4
    }
  },
  "backgrounds": {
    "image_dir": "assets/backgrounds"
  },
  "paths": {
    "piper_exe": "C:/AI/piper/piper.exe",
    "voice_model": "C:/AI/piper/voices/en_US-lessac-medium.onnx",
    "voice_config": "C:/AI/piper/voices/en_US-lessac-medium.onnx.json",
    "ffmpeg": "ffmpeg",
    "ffprobe": "ffprobe",
    "client_secret_json": "client_secret.json"
  }
}
```

Recommended Piper voices:

- `en_US-lessac-medium`
- `en_US-lessac-high`
- `en_US-amy-medium`

Test Piper before generating a full video:

```powershell
python test_voice.py
```

## Core Commands

Generate one short:

```powershell
python run_pipeline.py --topic "What an ETF is in under 60 seconds"
```

Generate one short from a random unused topic in `topics.txt`:

```powershell
python run_pipeline.py
```

Generate new beginner finance topic titles with Ollama and append them to `topics.txt`:

```powershell
python run_pipeline.py --generate-topics 20 --topics-only
```

Generate more topics, then immediately pick one random unused topic and render it:

```powershell
python run_pipeline.py --generate-topics 20
```

Generate one short and upload it as private:

```powershell
python run_pipeline.py --topic "How inflation quietly destroys cash savings" --upload --privacy private
```

Upload an already rendered video:

```powershell
python upload_youtube.py --video "outputs/<slug>/short.mp4" --metadata "outputs/<slug>/metadata.json" --privacy private
```

Run the static checks used by CI:

```powershell
pip install ruff bandit
python -m compileall -q generate_short.py run_pipeline.py upload_youtube.py test_voice.py
ruff check --output-format=github .
bandit -q -r . --severity-level medium --confidence-level high -x ./.git,./.venv,./outputs,./voices,./assets/music
```

## Backgrounds

The renderer supports topic-specific background image sequences. Add `.jpg`, `.jpeg`, `.png`, or `.webp` files under:

```text
assets/backgrounds/default/
assets/backgrounds/<topic-slug>/
```

For example, a topic titled `What Is an ETF?` usually becomes a slug like:

```text
assets/backgrounds/what-is-an-etf/
```

If no matching background images exist, the renderer generates finance-themed chart backgrounds automatically. The generated fallback backgrounds change per scene, so the result is not a single static image.

## Captions and Sync

Captions are built from WhisperX word timings. The default mode is semantic captioning:

```json
"captions": {
  "mode": "semantic",
  "min_words": 3,
  "max_words": 8,
  "max_seconds": 3.4
}
```

This keeps captions synced to the voice while avoiding word-by-word flashing. For fixed-size caption blocks, use:

```json
"captions": {
  "mode": "fixed",
  "words_per_chunk": 4
}
```

## YouTube Upload Setup

Before the first upload:

1. Create a Google Cloud project.
2. Enable YouTube Data API v3.
3. Create an OAuth Client ID for a Desktop App.
4. Download the credentials JSON.
5. Rename it to `client_secret.json`.
6. Place it in the repository root.

First upload:

```powershell
python run_pipeline.py --topic "ETF basics" --upload --privacy private
```

The first upload opens a browser login flow and creates a local `token.json`. Both `client_secret.json` and `token.json` are local secrets and must not be committed.

## Generated Output

Each generated short is written to:

```text
outputs/<video-slug>/
```

Typical files:

```text
script.txt          # Final script spoken by Piper
metadata.json       # Title, description, tags, sections, optional music
voice.wav           # TTS output
scenes/             # Rendered scene images
scenes.txt          # FFmpeg concat timing file
short.mp4           # Final video
```

`metadata.json` stores the original selected `topic`. The random topic picker uses that metadata and output folder names to avoid generating the same topic twice.

## CI

GitHub Actions runs a free static analysis workflow on `development` and `master`:

- Python syntax check with `compileall`
- Ruff lint/static analysis
- Bandit security/static analysis

Workflow file:

```text
.github/workflows/static-analysis.yml
```

## Troubleshooting

If Ollama fails:

```powershell
ollama serve
ollama pull llama3.1:8b
```

If FFmpeg fails, confirm both tools are available:

```powershell
ffmpeg -version
ffprobe -version
```

If Piper fails, check these `config.json` paths:

```json
"piper_exe": "C:/AI/piper/piper.exe",
"voice_model": "C:/AI/piper/voices/en_US-lessac-medium.onnx",
"voice_config": "C:/AI/piper/voices/en_US-lessac-medium.onnx.json"
```

If captions or timing fail, confirm WhisperX installed correctly:

```powershell
python -c "import whisperx; print('whisperx ok')"
```

If YouTube upload fails, delete the local `token.json` and retry the upload flow after confirming `client_secret.json` is valid.

## Recommended Workflow

Generate videos as private first, review script accuracy, voice quality, caption sync, background relevance, and finance claims, then publish manually. Automate scheduling only after the output quality is stable.

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
python -m pip install -r requirements.txt
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
    "max_seconds": 50,
    "captions": {
      "mode": "progressive",
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

`max_seconds` is a hard quality guard for the generated voice duration. The
current content target is a 35 to 50 second Short, which usually means a script
around 75 to 90 spoken words.

Recommended Piper voices:

- `en_US-lessac-medium`
- `en_US-lessac-high`
- `en_US-amy-medium`

Test Piper before generating a full video:

```powershell
python test_voice.py
```

## Content Standard

The generator is tuned for finance Shorts that match the current short-form
education market without copying generic "money hacks" content.

Target format:

- Length: 35 to 50 seconds.
- Script: 75 to 90 spoken words.
- Tone: professionally simple. Credible and slightly more expert than generic
  beginner content, but still clear to a normal adult without rewinding.
- Scope: one financial mechanism per Short, not a list of tips.
- Structure: contrarian hook, precise term, plain-English translation, tiny
  number example, practical takeaway, short CTA.
- Discovery focus: retention, click/watch behavior, engagement, relevance, and
  viewer personalization. Metadata supports relevance but should not become
  keyword stuffing.

Preferred content lanes:

- `Money Mechanics in 45 Seconds`
- `The Hidden Cost`
- `Finance Terms That Actually Matter`
- `One Chart, One Lesson`

Avoid get-rich framing, fake urgency, broad motivation, unrelated trend terms,
and overcomplicated academic explanations.

## TTS-Friendly Numbers

The generator normalizes the spoken script before Piper receives it. This avoids
awkward text-to-speech readings of finance notation.

Examples:

- `$1,000` becomes `one thousand dollars`
- `4%` becomes `four percent`
- `$1.50` becomes `one dollar and fifty cents`
- `$1.5M` becomes `one point five million dollars`
- `401(k)` becomes `four oh one k`

The prompt also asks the LLM to write numbers, currencies, and percentages in
spoken form inside the script. Symbols can still appear in titles, tags, and
metadata when useful.

## Video Generation Commands

### Generate a video from a specific topic

Command:

```powershell
python run_pipeline.py --topic "What an ETF is in under 60 seconds"
```

What happens:

- Ollama writes the title, description, tags, sections, and script.
- Piper turns the script into `voice.wav`.
- WhisperX creates word timings for caption sync.
- The renderer creates scene images and the final vertical `short.mp4`.
- Nothing is uploaded to YouTube unless `--upload` is also used.

Output folder:

```text
outputs/what-an-etf-is-in-under-60-seconds/
```

### Generate a video from a random unused topic

Command:

```powershell
python run_pipeline.py
```

What happens:

- The pipeline reads `topics.txt`.
- It checks `outputs/` and existing `metadata.json` files.
- It randomly picks a topic that has not been generated before.
- If `topics.txt` is empty, or every topic has already been generated, it asks
  Ollama for 20 fresh market-standard topic titles and appends the non-duplicate
  results before picking one.
- It generates the video the same way as a manual `--topic` run.

Override the automatic refill count:

```powershell
python run_pipeline.py --auto-generate-topics 30
```

Set it to `0` to disable automatic refill and fail when no unused topics remain:

```powershell
python run_pipeline.py --auto-generate-topics 0
```

### Generate and upload in one command

Command:

```powershell
python run_pipeline.py --topic "How inflation quietly destroys cash savings" --upload --privacy private
```

What happens:

- Generates the video locally first.
- Uploads the final `short.mp4` to the YouTube account authorized by `client_secret.json` and `token.json`.
- Uses the generated `metadata.json` title, description, and tags.
- Upload privacy is controlled by `--privacy`.

Supported privacy values:

```powershell
--privacy private
--privacy unlisted
--privacy public
```

## Topic Commands

### Generate new topic titles only

Command:

```powershell
python run_pipeline.py --generate-topics 20 --topics-only
```

What happens:

- Ollama generates 20 topic titles in the channel style: concrete, slightly
  contrarian, one financial mechanism per title, and suitable for a one-second
  Shorts hook.
- New, non-duplicate topics are appended to `topics.txt`.
- No video is rendered.
- Nothing is uploaded to YouTube.

### Generate topics and immediately render one

Command:

```powershell
python run_pipeline.py --generate-topics 20
```

What happens:

- Ollama appends new topics to `topics.txt`.
- The pipeline randomly selects one unused topic.
- It generates a video for that selected topic.
- Nothing is uploaded unless `--upload` is also passed.

### Use a custom topic list

Command:

```powershell
python run_pipeline.py --topics-file "my_topics.txt"
```

What happens:

- The random picker reads from `my_topics.txt` instead of `topics.txt`.
- Output still goes to `outputs/<video-slug>/`.

## Upload Commands

### Upload an existing rendered video

Command:

```powershell
python upload_youtube.py --video "outputs/<slug>/short.mp4" --metadata "outputs/<slug>/metadata.json" --privacy private
```

What happens:

- Uploads the selected local `short.mp4`.
- Reads YouTube title, description, and tags from the selected `metadata.json`.
- Uploads to the YouTube account that completes the OAuth browser login.
- Creates or reuses local `token.json`.

Upload destination:

```text
YouTube account authorized by client_secret.json/token.json
```

The script does not upload anywhere else. It does not publish to GitHub, cloud storage, or another video platform.

## Command Outputs

Every video generation command writes a folder under:

```text
outputs/<video-slug>/
```

Typical output:

```text
outputs/<video-slug>/
|-- script.txt          # Final script spoken by Piper
|-- metadata.json       # Topic, title, description, tags, sections, optional music
|-- voice.wav           # Piper TTS audio
|-- scenes/             # Rendered caption/background scene images
|-- scenes.txt          # FFmpeg concat timing file
`-- short.mp4           # Final vertical video
```

`short.mp4` is the file to review, publish manually, or upload with `upload_youtube.py`.

`metadata.json` stores the original selected `topic`. The random topic picker uses that metadata and output folder names to avoid generating the same topic twice.

## Quality Commands

Run the static checks used by CI:

```powershell
python -m pip install ruff bandit
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

Captions are built from WhisperX word timings. The default mode is progressive semantic captioning:

```json
"captions": {
  "mode": "progressive",
  "min_words": 3,
  "max_words": 8,
  "max_seconds": 3.4
}
```

This keeps captions synced to the voice across the full video: each semantic phrase builds up as the words are spoken, so the viewer does not see words before the narration reaches them. For full phrase-at-once captions, use:

```json
"captions": {
  "mode": "phrase",
  "min_words": 3,
  "max_words": 8,
  "max_seconds": 3.4
}
```

For fixed-size caption blocks, use:

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

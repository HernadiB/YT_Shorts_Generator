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
|-- setup_channel.py                  # Apply channel branding, playlists, and sections
|-- test_voice.py                     # Quick Piper voice test
|-- setup_windows.ps1                 # Human-readable Windows setup helper
|-- requirements.txt                  # Python dependencies
|-- config.example.json               # Template for local config.json
|-- channel_profile.json              # Public channel positioning and setup config
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

Local-only files such as `.env`, `config.json`, `client_secret.json`, `token.json`, `channel_token.json`, `channel_state.json`, `.venv/`, `outputs/`, generated media, and voice assets should not be committed.

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
    "min_seconds": 35,
    "max_seconds": 60,
    "captions": {
      "mode": "progressive",
      "min_words": 3,
      "max_words": 6,
      "max_seconds": 2.8
    }
  },
  "backgrounds": {
    "image_dir": "assets/backgrounds"
  },
  "tts": {
    "length_scale": 1.1,
    "sentence_silence": 0.24
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

`min_seconds` and `max_seconds` are hard quality guards for the generated voice
duration. The current content target is a 35 to 60 second Short, which usually
means a script around 105 to 145 spoken words at natural Piper pace.

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

- Length: 35 to 60 seconds.
- Script: 105 to 145 spoken words.
- Pace: fast first-second hook, then slower explanation with natural breathing
  room. The goal is retention through comprehension, not maximum information
  density.
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

## Script Quality Gate

The generator runs an LLM quality review before TTS. The review acts as an
English copy editor and personal finance fact-checker, then rewrites the script
when needed.

It checks for:

- Grammar, word order, punctuation, sentence fragments, and run-on sentences.
- Awkward or unclear sentence structure.
- Misleading finance terminology, guarantees, market-timing claims, and
  investment advice phrasing.
- Claims that require current rate or market data.
- Economic claims that are not logically, mathematically, or financially
  coherent from the information in the script.
- Overloaded sentences that are hard to follow in voiceover.
- TTS-hostile finance notation such as `$1,000`, `4%`, or `dollar one thousand`
  in the spoken script.

Default config:

```json
"quality_gate": {
  "enabled": true,
  "max_revision_attempts": 3,
  "min_script_words": 105,
  "hard_min_script_words": 95,
  "max_script_words": 145,
  "hard_max_script_words": 165,
  "min_complete_sentences": 4,
  "fail_on_unresolved_issues": true
}
```

Minor length or pacing drift becomes a warning, not a hard failure. For example,
a clean 98-word script can continue, but very short drafts are still repaired or
blocked before rendering. If a review accidentally returns a script below the
hard minimum, the generator appends safe finance-context closing sentences and
checks it again. Grammar problems, broken sentence structure,
risky finance claims, current-data finance claims, placeholders, TTS-hostile
finance notation, and inconsistent loan math still fail before voice, captions,
or video rendering start. LLM review notes are retained as warnings unless the
deterministic gate also finds a blocking issue.

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

## Finance Math Guardrails

The quality gate includes a deterministic check for loan examples. When a
script combines loan principal, APR, term, monthly payment, or total interest,
the generator estimates the amortized payment and total interest before TTS.

This catches examples where the story sounds plausible but the numbers cannot
all be true at the same time, such as a payment schedule that does not even
repay the principal. If the math is inconsistent, generation fails before
voice, captions, or rendering start.

If a script states a loan's principal, APR, and total interest without a term,
the gate also fails it. That example is under-specified, so the script must add
the term or stay qualitative.

## Video Generation Commands

### Generate a video from a specific topic

Command:

```powershell
python run_pipeline.py --topic "What an ETF is in under 60 seconds"
```

What happens:

- Ollama writes the title, description, tags, sections, and script.
- Piper turns the script into `voice.wav`.
- WhisperX creates word timings for caption sync, then caption text is aligned
  back to the approved script so recognition slips do not change the displayed
  words.
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
- Adds the uploaded video to the best matching saved playlist when `channel_state.json` exists.
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
- Adds the uploaded video to the best matching playlist from local `channel_state.json`.

Upload destination:

```text
YouTube account authorized by client_secret.json/token.json
```

The script does not upload anywhere else. It does not publish to GitHub, cloud storage, or another video platform.

Skip automatic playlist assignment:

```powershell
python upload_youtube.py --video "outputs/<slug>/short.mp4" --metadata "outputs/<slug>/metadata.json" --privacy private --skip-playlists
```

## Command Outputs

Every video generation command writes a folder under:

```text
outputs/<video-slug>/
```

Typical output:

```text
outputs/<video-slug>/
|-- script.txt          # Final script spoken by Piper
|-- metadata.json       # Topic, title, description, tags, playlist, sections, optional music
|-- voice.wav           # Piper TTS audio
|-- scenes/             # Rendered caption/background scene images
|-- scenes.txt          # FFmpeg concat timing file
`-- short.mp4           # Final vertical video
```

`short.mp4` is the file to review, publish manually, or upload with `upload_youtube.py`.

`metadata.json` stores the original selected `topic`. It may also include a best-fit `playlist` title for upload routing. The random topic picker uses the topic metadata and output folder names to avoid generating the same topic twice.

## Quality Commands

Run the static checks used by CI:

```powershell
python -m pip install ruff bandit
python -m compileall -q generate_short.py run_pipeline.py setup_channel.py upload_youtube.py test_voice.py
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

After WhisperX returns timings, the generator aligns the recognized words back
to the approved script text. The timings still come from the audio, but the
visible captions follow the script. This prevents small ASR mistakes, such as
confusing "low" with "loan", from becoming visible in the final Short.

```json
"captions": {
  "mode": "progressive",
  "min_words": 3,
  "max_words": 6,
  "max_seconds": 2.8
}
```

This keeps captions synced to the voice across the full video: each semantic phrase builds up as the words are spoken, so the viewer does not see words before the narration reaches them. The default phrase size is intentionally tighter so each visual beat carries less information. For full phrase-at-once captions, use:

```json
"captions": {
  "mode": "phrase",
  "min_words": 3,
  "max_words": 6,
  "max_seconds": 2.8
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

## YouTube Channel Setup

The repository includes a channel setup profile and helper script for applying
the integrity-focused channel positioning:

- Channel concept: `Money Mechanics`
- Banner copy: `Money Mechanics in 45 Seconds` / `Clear finance. No hype. No guarantees.`
- About text: professional finance explained in plain English, with clear
  education-only and no-advice disclaimers.
- Playlists and home sections: `Start Here`, `Money Mechanics in 45 Seconds`,
  `The Hidden Cost`, `Finance Terms That Actually Matter`, `One Chart, One
  Lesson`, `Debt and Credit`, `Inflation and Cash`, `Investing Basics`.

Preview the channel changes without applying them:

```powershell
python setup_channel.py
```

Apply channel description, keywords, playlists, and playlist sections:

```powershell
python setup_channel.py --apply
```

The first run opens a local browser OAuth flow and creates
`channel_token.json`, even in preview mode, because it reads the current channel
state before deciding what would change. Do not paste OAuth tokens into chat.
The setup token is separate from `token.json`, which is used for uploads.
When playlists are available, the setup script also writes local
`channel_state.json` with the playlist IDs and routing rules used by uploads.
This file is ignored by git because it is account-specific.

If the playlists already exist and you only want to refresh the saved IDs:

```powershell
python setup_channel.py --write-state --skip-branding --skip-sections
```

Automatic upload routing uses:

- Keyword routing from `channel_profile.json` based on the topic, title,
  description, tags, search keywords, and script.
- The generated `metadata.json` `playlist` field as a fallback when no routing
  rule matches.
- `Money Mechanics in 45 Seconds` as the default/general playlist.

If `channel_state.json` is missing, upload still succeeds, but playlist
assignment is skipped. Run `python setup_channel.py --apply` or
`python setup_channel.py --write-state --skip-branding --skip-sections` first.
If `token.json` was created before playlist routing existed, the next upload may
open OAuth again so the script can request playlist management permission.

What the script can update through the YouTube Data API:

- Channel description, keywords, default language, and country.
- Public playlists from `channel_profile.json`.
- Home tab playlist sections for those playlists.

What still needs manual YouTube Studio work:

- Channel name and handle.
- Profile picture and banner image upload.
- Upload defaults description.
- Paid promotion disclosure when a sponsor, affiliate relationship, or
  endorsement exists.
- Altered/synthetic disclosure when realistic AI-generated content could
  mislead viewers.

Recommended manual values are stored in:

```text
channel_profile.json
```

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

On Windows, Piper is run from its own directory with a relative
`--espeak_data` path. This avoids crashes when the repository path contains
accented characters.

If captions or timing fail, confirm WhisperX installed correctly:

```powershell
python -c "import whisperx; print('whisperx ok')"
```

If YouTube upload fails, delete the local `token.json` and retry the upload flow after confirming `client_secret.json` is valid.

## Recommended Workflow

Generate videos as private first, review script accuracy, voice quality, caption sync, background relevance, and finance claims, then publish manually. Automate scheduling only after the output quality is stable.

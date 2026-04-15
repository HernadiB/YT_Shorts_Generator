# Agent Project Context

Last updated: 2026-04-15

Use this file as the first-read project summary for future coding sessions.
When the user asks to update the project/session context, append a concise entry
to "Session Log" with the date, changed files, commands run, and unresolved
questions. Do not include secrets, OAuth tokens, API keys, or generated media.
For generated code changes, create a focused git commit and push it to the
current remote branch after verification, unless the user explicitly says not to.
On this Windows sandbox, plain `git push` can time out with a Git `sh.exe`
signal pipe error. For pushes, request escalated execution directly instead of
trying a sandboxed push first.

## Project Snapshot

- Project name: Finance Shorts Factory.
- Current branch observed at creation: `development`.
- Git status at creation: clean.
- Main goal: generate faceless English YouTube Shorts about beginner personal
  finance topics from local tools.
- Primary runtime: Python 3.11+ on Windows/PowerShell.
- Core dependencies: Ollama, Piper, WhisperX, Pillow, FFmpeg/FFprobe, YouTube
  Data API v3, python-dotenv, requests.
- Generated outputs and local assets are intentionally gitignored.

## Repository Map

- `generate_short.py`: core generator. Creates script metadata with Ollama,
  generates TTS audio with Piper, gets word timings with WhisperX, renders scene
  PNGs with Pillow, and produces `short.mp4` with FFmpeg.
- `run_pipeline.py`: CLI orchestrator. Can generate topic titles, pick a random
  unused topic, call the generator, and optionally upload the latest output.
- `upload_youtube.py`: uploads an existing rendered video using YouTube OAuth
  credentials from `client_secret.json` and `token.json`, then assigns it to
  saved playlists when `channel_state.json` exists.
- `setup_channel.py`: applies integrity-focused channel branding, keywords,
  playlists, and home tab playlist sections using a separate local
  `channel_token.json`; it can also write local playlist IDs to
  `channel_state.json`.
- `channel_profile.json`: public channel positioning config for the recommended
  `Money Mechanics` identity, descriptions, playlist structure, pinned comment
  template, and manual Studio checklist.
- `test_voice.py`: quick Piper smoke test that writes `test_voice.wav`.
- `setup_windows.ps1`: Windows setup helper for dependencies and local config.
- `prompts/system_prompt.txt`: system prompt for Shorts script and metadata.
- `config.example.json`: template for local `config.json`.
- `.env.example`: template for Ollama and upload default environment values.
- `topics.txt`: source topic pool for random generation.
- `assets/backgrounds/`: optional topic-specific or default background images.
- `assets/music/library/`: optional local background tracks; audio files are
  ignored by git.
- `outputs/`: generated videos and intermediates; ignored by git.
- `voices/`: local Piper install/voices; ignored by git.

## Pipeline Flow

1. `run_pipeline.py` receives `--topic`, or reads `topics.txt` and selects a
   random topic whose slug is not already represented in `outputs/`.
2. Optional topic generation uses Ollama and appends non-duplicate titles to the
   selected topics file.
3. `generate_short.py --topic "<topic>"` loads `.env` and `config.json`.
4. Ollama returns JSON metadata: title, description, tags, script, sections.
5. The output directory is `outputs/<safe-topic-slug>/`.
6. The script and metadata are written as `script.txt` and `metadata.json`.
7. Piper creates `voice.wav`.
8. FFprobe reads the audio duration.
9. WhisperX creates word-level timings.
10. Captions are built from word timings. Modes are `progressive`, `phrase`, or
    `fixed`, configured under `video.captions`.
11. A visual timeline is created so scene durations cover the full audio.
12. Scene PNGs are rendered into `outputs/<slug>/scenes/`.
13. Backgrounds come from `assets/backgrounds/<slug>/`, then
    `assets/backgrounds/default/`, then generated procedural finance charts.
14. A random music file can be selected from `assets/music/library/`.
15. FFmpeg renders `short.mp4`; with music it uses sidechain compression.
16. If `run_pipeline.py --upload` is set, `upload_youtube.py` uploads the final
    video using generated metadata and assigns saved playlists when
    `channel_state.json` is available.

## Configuration Notes

- Local secrets/config files should remain uncommitted: `.env`, `config.json`,
  `client_secret.json`, `token.json`, `channel_token.json`,
  `channel_state.json`.
- `.env` should define at least `OLLAMA_MODEL` and `OLLAMA_URL`.
- `config.json` controls video size, FPS, max length, caption settings,
  background/music directories, branding text, Piper paths, FFmpeg paths, and
  upload defaults.
- Upload defaults in `config.json` control category, language, made-for-kids,
  embeddable, stats visibility, and license fields.
- `channel_state.json` is account-specific local state. It stores channel ID,
  playlist IDs, and upload routing copied from `channel_profile.json`; never
  commit it.
- The README recommends generating videos as private first, reviewing accuracy,
  voice quality, caption sync, background relevance, and finance claims, then
  publishing manually.

## Current Local State Observed

- Topic pool in `topics.txt` currently contains:
  - `How inflation quietly destroys cash savings`
  - `What an ETF is in under 60 seconds`
  - `Why high-interest debt keeps people poor`
  - `Emergency fund basics for beginners`
  - `Compound interest explained simply`
- Existing generated output directory observed:
  - `outputs/what-an-etf-is-in-under-60-seconds`
- Background directories observed:
  - `assets/backgrounds/default`
  - `assets/backgrounds/what-an-etf-is-in-under-60-seconds`
- Music library observed with ambient, cinematic, and pop MP3 files.
- `voices/piper` exists locally.

## Useful Commands

Generate a short from a specific topic:

```powershell
python run_pipeline.py --topic "What an ETF is in under 60 seconds"
```

Generate from a random unused topic:

```powershell
python run_pipeline.py
```

Generate topics only:

```powershell
python run_pipeline.py --generate-topics 20 --topics-only
```

Generate and upload privately:

```powershell
python run_pipeline.py --topic "ETF basics" --upload --privacy private
```

Upload an existing short:

```powershell
python upload_youtube.py --video "outputs/<slug>/short.mp4" --metadata "outputs/<slug>/metadata.json" --privacy private
```

Refresh saved playlist IDs after channel setup:

```powershell
python setup_channel.py --write-state --skip-branding --skip-sections
```

Run static checks used by CI:

```powershell
python -m compileall -q generate_short.py run_pipeline.py setup_channel.py upload_youtube.py test_voice.py
ruff check --output-format=github .
bandit -q -r . --severity-level medium --confidence-level high -x ./.git,./.venv,./outputs,./voices,./assets/music
```

## Implementation Notes And Risks

- The generator has a few mojibake comment headings from emoji encoding. They
  are cosmetic; avoid unrelated cleanup unless requested.
- YouTube Shorts discovery work should optimize for the official core signals:
  viewer personalization, video performance, retention, click/watch behavior,
  engagement, and content relevance. Metadata supports relevance, but avoid
  spammy tags, misleading hashtags, or exaggerated promises.
- Progressive captions use `Chunk.background_group` so captions can advance
  word by word while backgrounds change only between semantic phrase groups.
- Metadata generation is tuned for YouTube Shorts discovery without keyword
  stuffing: the prompt asks for relevant tags, exactly 3 hashtags, and search
  keyword phrases, plus a best-fit playlist when channel playlists are known;
  upload code cleans/deduplicates tags and appends missing hashtags to the
  description.
- Upload playlist routing scores topic/title/description/tags/search
  keywords/script against `channel_profile.json` rules first, uses a valid
  generated `playlist` field only when no rule matches, always adds the general
  `Money Mechanics in 45 Seconds` playlist, and falls back to that default when
  nothing else matches.
- `upload_youtube.py` now requests the broader
  `https://www.googleapis.com/auth/youtube` scope because uploads plus playlist
  assignment require both video insert and playlist item insert permissions. If
  an older `token.json` only has upload scope, the next upload opens OAuth again.
- Script tone should be "professionally simple": credible and slightly more
  expert than generic beginner content, but still clear to a normal adult
  without rewinding.
- `generate_short.py` has a default-enabled script quality gate. After the
  first LLM draft, it asks Ollama to act as an English copy editor and finance
  fact-checker, rewrite weak copy, and approve the result before TTS. A
  deterministic gate also rejects unresolved grammar/structure, risky finance
  claims, placeholder text, overloaded sentences, and TTS-hostile finance
  notation.
- Content strategy target: 38 to 50 second Shorts, 65 to 78 spoken words, one
  financial mechanism per video, contrarian hook, precise term, plain-English
  translation, tiny number example, practical takeaway, and short CTA.
- Pacing strategy: keep the first-second hook sharp, then slow the explanation
  for comprehension. Current defaults use Piper `length_scale = 1.12`,
  `sentence_silence = 0.28`, and progressive caption groups capped around 6
  words or 2.8 seconds.
- Replay strategy: do not make scripts confusing to force replays. The main
  takeaway should be clear on first watch, while the example, contrast, or final
  line rewards a second watch and loops back to the opening hook.
- Preferred positioning is "professional finance explained like a smart friend":
  series concepts include `Money Mechanics in 45 Seconds`, `The Hidden Cost`,
  `Finance Terms That Actually Matter`, `One Chart, One Lesson`, `What This
  Really Means For Your Wallet`, and `Beginner Finance, But Not Dumbed Down`.
- Topic titles should work in the first second: use concrete, slightly
  contrarian finance statements, not generic questions.
- `run_pipeline.py` refills exhausted topic lists automatically with 20 fresh
  Ollama-generated titles by default; use `--auto-generate-topics 0` to disable.
- Spoken script text is normalized before TTS so finance notation reads
  naturally: `$1,000` -> `one thousand dollars`, `4%` -> `four percent`,
  `$1.50` -> `one dollar and fifty cents`, and `401(k)` -> `four oh one k`.
- `pick_font()` uses `C:/Windows/Fonts/arialbd.ttf`, so rendering is currently
  Windows-specific.
- `run_pipeline.py` assumes the latest modified directory under `outputs/` is
  the just-generated video after `generate_short.py` completes.
- `test_voice.py` does not pass `voice_config`, while `generate_short.py` does.
- Full video generation can be slow and depends on local Ollama, Piper,
  WhisperX models, FFmpeg, and local paths being correctly configured.
- Do not inspect or print OAuth tokens or local credential files unless the user
  explicitly asks and there is a clear reason.
- Do not ask the user to paste OAuth tokens into chat. Channel setup should use
  `python setup_channel.py --apply`, which opens local browser OAuth and stores
  `channel_token.json`.

## Session Log

### 2026-04-15

- Created this `AGENTS.md` project context file for future sessions.
- Analyzed README, config template, prompt, CI workflow, main Python scripts,
  topics, output directories, background directories, music library, and local
  voice directory presence.
- No code behavior changed.
- Verification so far: repository tree inspection and `git status --short`
  showed a clean working tree before this file was added.
- Updated `generate_short.py` so progressive caption chunks from the same
  semantic phrase share a `background_group`. This keeps the word-by-word
  caption reveal, but the selected/procedural background changes only when the
  next phrase group starts.
- Verification: `python -m compileall -q generate_short.py`, `ruff check
  generate_short.py`, and a targeted sample confirmed background groups like
  `[0, 0, 0, 1, 1, 1]` for two phrase groups.
- Updated the script prompt and metadata handling for YouTube Shorts discovery:
  titles now prioritize topic keywords naturally, descriptions keep the topic
  clear early, metadata includes `hashtags` and `search_keywords`, and tag
  output is capped/deduplicated.
- Updated `upload_youtube.py` to normalize tags, append up to 3 hashtags to the
  description when missing, use category/language upload defaults, and keep
  YouTube API tag payload under a conservative character budget.
- Updated `config.example.json` with upload defaults for category and language.
- Verification: `python -m compileall -q generate_short.py upload_youtube.py
  run_pipeline.py test_voice.py`, `ruff check generate_short.py
  upload_youtube.py run_pipeline.py test_voice.py`, and a targeted metadata
  normalization sample.
- Added the standing workflow preference that generated code changes should get
  a focused git commit and be pushed to the current remote branch after
  verification.
- Added the official YouTube Shorts discovery signal summary to the project
  context: viewer personalization, video performance, retention, click/watch
  behavior, engagement, and relevance.
- Refined `prompts/system_prompt.txt` tone guidance so generated scripts sound
  credible and slightly professional for average viewers without becoming
  academic, bank-like, or overloaded with jargon.
- Built the Shorts market-standard strategy into the project: prompt targeted
  one finance mechanism per Short, contrarian hook, plain-English translation,
  tiny number example, and practical takeaway.
- Updated `README.md` with the content standard and preferred content lanes.
- Updated `config.example.json` and local ignored `config.json` to use
  `video.max_seconds = 50`.
- Updated `generate_short.py` to validate generated voice duration against
  `video.max_seconds` before WhisperX/rendering, so overlong scripts fail fast.
- Added TTS-friendly spoken number normalization for the generated script:
  currency symbols/codes, percentages, compact magnitudes, plain numbers, and
  `401(k)` are converted to words before Piper and caption timing.
- Updated `prompts/system_prompt.txt` to ask the model to write spoken script
  numbers, currencies, and percentages exactly as they should be read aloud.
- Updated `README.md` with examples of the TTS number normalization behavior.
- Added 20 new market-standard finance topic titles to `topics.txt`, using
  one-second hook statements around hidden costs, misunderstood mechanisms, and
  wallet-level consequences.
- Updated `run_pipeline.py` so random generation automatically refills an empty
  or exhausted topics file with fresh Ollama-generated titles, defaulting to 20.
- Updated the topic-generation prompt to avoid generic questions and produce
  concrete, slightly contrarian finance statements aligned with the channel
  lanes.
- Updated `README.md` with the automatic topic refill behavior and
  `--auto-generate-topics` override.
- Tuned pacing for finance comprehension without weakening the first-second
  hook: prompt now targets 65 to 78 spoken words and 38 to 50 seconds,
  `run_piper()` passes optional Piper `tts` settings from config, defaults use
  `length_scale = 1.12` and `sentence_silence = 0.28`, and caption groups are
  capped at 6 words or 2.8 seconds.
- Updated replay/retention prompt guidance: scripts should be clear on first
  watch, rewarding on second watch, and end by looping the final takeaway back
  to the opening hook instead of becoming intentionally unclear.
- Added `channel_profile.json` and `setup_channel.py` so the recommended
  integrity-focused YouTube channel positioning can be applied through local
  OAuth without sharing tokens in chat.
- Channel setup can update description, keywords, default language/country,
  public playlists, and home tab playlist sections. Channel name, handle,
  profile picture, banner upload, upload defaults, paid promotion disclosures,
  and altered/synthetic disclosures remain manual YouTube Studio steps.
- Added local playlist-state persistence and upload routing: `.gitignore` now
  ignores `channel_state.json`, `setup_channel.py` can save real playlist IDs,
  `channel_profile.json` stores routing rules, `generate_short.py` asks the LLM
  for a best-fit playlist, and `upload_youtube.py` adds uploaded videos to the
  resolved playlist(s).
- Added script quality gating before TTS: generated metadata is normalized,
  reviewed by Ollama as an English editor and finance fact-checker, rewritten up
  to the configured retry limit, and rejected if grammar, sentence structure,
  risky finance claims, placeholders, overloaded sentences, or spoken-number
  issues remain.

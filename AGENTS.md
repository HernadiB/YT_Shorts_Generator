# Agent Project Context

Last updated: 2026-04-17

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
  claims, current-data finance claims, placeholder text, overloaded sentences,
  TTS-hostile finance notation, and inconsistent loan/APR/payment math. Minor
  length, pacing drift, and LLM review notes are stored as warnings when the
  deterministic gate finds no blocking issue. If the review returns a script
  below the hard minimum, the generator appends safe finance-context closing
  sentences before the final gate.
- Content strategy target: 35 to 60 second Shorts, 105 to 145 spoken words, one
  financial mechanism per video, contrarian hook, precise term, plain-English
  translation, tiny number example, practical takeaway, and short CTA.
- Pacing strategy: keep the first-second hook sharp, then slow the explanation
  for comprehension. Current defaults use `video.min_seconds = 35`,
  `video.max_seconds = 60`, Piper `length_scale = 1.1`,
  `sentence_silence = 0.24`, and progressive caption
  groups capped around 6 words or 2.8 seconds.
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
- Prompt guidance requires pronounceable finance terminology in the spoken
  script: acronyms that should be read letter by letter should be written as
  spaced letters, such as `E T F` and `A P R`, while titles/tags may keep
  standard acronym spelling.
- Every generated script should end with the exact CTA `Follow for more
  practical money tips.` Avoid using `advice` in the CTA because the channel
  disclaimer says `Not financial advice.`
- WhisperX supplies caption timings, but caption text is aligned back to the
  approved script before chunking. This keeps visible captions from inheriting
  ASR slips such as `low` becoming `loan`.
- Render timeline uses a small `render.tail_padding_seconds` visual buffer so
  FFmpeg has video frames available until the narration has fully finished.
- `pick_font()` uses `C:/Windows/Fonts/arialbd.ttf`, so rendering is currently
  Windows-specific.
- `run_pipeline.py` assumes the latest modified directory under `outputs/` is
  the just-generated video after `generate_short.py` completes.
- `test_voice.py` uses the same `run_piper()` helper as `generate_short.py`, so
  voice tests cover the actual Piper invocation path.
- Piper is run from its own directory with a relative `--espeak_data` path and a
  temporary WAV in the Piper directory. This avoids Windows crashes when the
  repo path contains accented characters such as `Hernádi Barnabás`.
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
  `video.min_seconds = 35` and `video.max_seconds = 60`.
- Updated `generate_short.py` to validate generated voice duration against
  `video.min_seconds` and `video.max_seconds` before WhisperX/rendering, so
  pacing outliers fail fast.
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
  hook: prompt now targets 105 to 145 spoken words and 35 to 60 seconds,
  `run_piper()` passes optional Piper `tts` settings from config, defaults use
  `length_scale = 1.1` and `sentence_silence = 0.24`, and caption groups are
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
- Relaxed quality gate failure semantics so target word-count and sentence-count
  misses are warnings, while hard length limits and actual language, structure,
  finance-claim, placeholder, and spoken-number issues remain blocking.
- Added deterministic short-script repair for cases where the LLM quality review
  returns an otherwise clean script below the hard minimum.
- Fixed the follow-up generation failures for the `Liquidity is the reason cash
  still matters` topic: quality gate length/style drift no longer crashes,
  malformed spoken currency phrases are normalized, text encoding/dash artifacts
  are cleaned before TTS, and Piper now runs with relative espeak data to handle
  accented Windows paths.

### 2026-04-16

- Reviewed the generated `A low monthly payment can hide a bad deal` output and
  found the message direction usable, but not publication-ready because the
  loan/APR/payment example was mathematically inconsistent and WhisperX changed
  the visible caption text from `low` to `loan`.
- Added deterministic loan math validation in `generate_short.py`: when a
  script combines principal, APR, term, monthly payment, or total interest, the
  gate estimates amortized payment and total interest before TTS.
- Loan examples that state principal, APR, and total interest without a term are
  blocked as under-specified instead of being treated as publishable.
- Updated caption timing so WhisperX still supplies word timings, but displayed
  caption words are aligned back to the approved script before chunking.
- Updated `prompts/system_prompt.txt` and the quality-review prompt so future
  scripts avoid unverifiable finance math and use qualitative wallet examples
  when exact amortization is not known.
- Prompt and review prompt now require economic, logical, mathematical, and
  background-information coherence. The model should not invent market averages,
  typical rates, hidden fees, or performance data unless the topic/caller
  supplied them.
- Added `video.min_seconds` as a hard post-TTS guard and slowed the local/config
  example Piper defaults to keep finance explanations from rendering as
  overloaded sub-30-second Shorts.
- Made LLM review notes non-blocking when the deterministic gate is clean, and
  added a hard check for finance claims that depend on current market-rate data.
- Retuned natural speech pacing after the local `length_scale = 1.1` setting:
  scripts now target 105 to 145 spoken words, videos target 35 to 60 seconds,
  and `config.example.json` uses the same natural TTS pace as local config.
- Added a schema guard for LLM metadata: narrated text found outside the `script`
  field is folded back into the script before quality checks, and unknown
  metadata keys are removed from the final metadata output.
- Added a render tail padding config so the final scene extends past the voice
  track before FFmpeg applies `-shortest`; this prevents end-of-video narration
  clipping.
- Tightened prompt and review wording for language quality: clearer grammar,
  active voice, fewer vague pronouns, TTS-friendly professional terms, and a
  mandatory final CTA asking viewers to follow for more practical money tips.

### 2026-04-17

- Added daily development environment scripts without duplicating the existing
  Windows installer/bootstrap flow: `start_dev.ps1` delegates missing baseline
  setup to `setup_windows.ps1`, loads `.env`, starts/tracks Ollama, checks the
  configured model, and runs a quick Python syntax check.
- Added `stop_dev.ps1` to stop only the Ollama process tracked as started by
  this project by default, with an explicit `-ForceAllOllama` option for
  stopping every local Ollama process.
- Updated `.gitignore` to ignore `.dev/` runtime service state.
- Updated `README.md` with the new development-session workflow and PowerShell
  execution-policy bypass example.
- Verification: parsed both PowerShell scripts with
  `[System.Management.Automation.Language.Parser]::ParseFile`, ran
  `python -m compileall -q generate_short.py run_pipeline.py setup_channel.py
  upload_youtube.py test_voice.py`, `ruff check .`, `bandit -q -r .
  --severity-level medium --confidence-level high -x
  ./.git,./.venv,./outputs,./voices,./assets/music`, and `start_dev.ps1` /
  `stop_dev.ps1` dry runs via
  `powershell -NoProfile -ExecutionPolicy Bypass -File`.
- Direct `.\start_dev.ps1` / `.\stop_dev.ps1` execution was blocked by the
  local PowerShell execution policy, so the README documents the bypass path.
- Follow-up fix: `stop_dev.ps1` originally left Ollama running when no
  `.dev/services.json` state file existed or when Ollama had been started
  before `start_dev.ps1`; it now stops local `ollama app.exe` and `ollama.exe`
  processes by default because the tray app can respawn the server, with
  `-KeepExternalOllama` available to preserve externally started Ollama.
- Updated `README.md` to reflect the new shutdown behavior.
- Verification for the follow-up: `stop_dev.ps1 -DryRun` saw both `ollama app`
  and `ollama`, actual `stop_dev.ps1` stopped both, `Get-Process` found no
  remaining `ollama*` processes, `netstat` found no `:11434` listener, and
  `http://localhost:11434/api/tags` was down afterward.
- Follow-up fix: `start_dev.ps1` could time out even after Ollama had started
  because the readiness check depended on PowerShell `Invoke-RestMethod` against
  `localhost`. It now checks `/api/tags` through `curl.exe`/`Invoke-WebRequest`,
  includes a `127.0.0.1` fallback for localhost, writes startup logs to
  `.dev/ollama.stdout.log` and `.dev/ollama.stderr.log`, and avoids triggering
  `ollama pull` when the model list cannot be verified.
- Verification for the start follow-up: after stopping Ollama, `start_dev.ps1
  -SkipChecks` started the server and confirmed `llama3.1:8b` through the HTTP
  model list without pulling. The Codex shell environment did not preserve the
  background server after the command returned, but the original user shell did
  preserve `ollama.exe` after timeout, so the fixed readiness/model checks
  address the reported interactive failure.
- Added GitHub governance setup on branch `chore/github-governance-pages`:
  CODEOWNERS, PR template, issue templates, Dependabot config, Pages workflow,
  `CONTRIBUTING.md`, `SECURITY.md`, `docs/index.html`, and
  `docs/github-governance.md`.
- Created PR #3 (`Add GitHub governance and Pages setup`) and applied
  governance metadata: labels, `v0.1 Repository Governance` milestone, and
  assignee `HernadiB`.
- Created or updated the standard label set, milestones, repo settings, and
  initial issue backlog (#4 through #8).
- Applied the same governance metadata to the pre-existing PR #2
  (`Improve development environment scripts and handle Ollama issues`): labels,
  `v0.1 Repository Governance` milestone, assignee `HernadiB`, and a comment
  documenting that GitHub cannot request a review from the PR author.
- Follow-up GitHub hardening: ran a quick public-readiness scan, made the repo
  public, enabled Pages workflow deployments, set homepage/topics, enabled
  Dependabot/security alert features where GitHub allowed them, and created a
  `Protect development and master` repository ruleset after classic branch
  protection failed on user-owned repo restrictions validation.
- Added release/package handling on the governance PR branch: package workflow,
  release workflow, CodeQL workflow, `docs/release-package.md`, and a shorter
  README split into focused docs under `docs/`.
- PR #3 was merged before the release/docs follow-up was complete, so the
  release/docs commit was moved onto a fresh branch
  `chore/release-packaging-docs` from latest `origin/development`; PR #16 was
  opened, labeled, assigned to `HernadiB`, and attached to
  `v0.1 Repository Governance`.
- Project v2 remains blocked by missing token scopes
  (`project`/`read:project`/org-related scopes).
- Follow-up governance rule: every non-dependency PR must reference at least
  one issue, and every active issue must link back to the PR carrying the work.
  Use closing keywords only when the PR fully completes the issue; otherwise use
  `Related #...`.
- Updated `.github/pull_request_template.md` and the issue templates so future
  PRs/issues explicitly capture linked issue/PR references.
- Investigated the failed GitHub Pages deploys. The `Configure Pages` step
  failed with a Pages site lookup 404 even though the repo Pages config existed
  and used workflow deployments. Updated `.github/workflows/pages.yml` so
  `actions/configure-pages` runs with `enablement: true`.
- Updated `docs/github-governance.md` and `docs/release-package.md` with the
  issue/PR association rule, Pages deploy fix, and release-from-`master`
  policy.
- Updated the repository ruleset with a PR-only `RepositoryRole` admin bypass
  after GitHub blocked a green owner-authored PR because required self-review
  cannot be satisfied in this one-user repo. The ruleset remains active for
  direct branch protection.
- Merged PR #16 to `development`; the follow-up Pages workflow run on
  `development` succeeded.
- Created PR #18 from `release/master-promotion` after PR #9 was dirty against
  `master`; PR #18 resolved `README.md` and `AGENTS.md` by keeping the current
  `development` documentation set, then merged to `master`.
- Tagged `v0.1.0-rc.1`, but the release workflow failed in the version
  validation step because the bash regex escaped literal dots twice. The fix is
  being carried on `fix/release-version-regex` and future prerelease publishing
  should use the next prerelease tag rather than rewriting the failed tag.
- Merged PR #19 to fix release workflow version validation and PR #20 to promote
  that fix to `master`.
- Published GitHub Release `v0.1.0-rc.2` as a prerelease with ZIP, TAR.GZ, and
  SHA256SUMS assets.
- Closed issue #4, issue #15, and milestone `v0.1 Repository Governance` as
  completed.
- Updated the repository ruleset required checks to include
  `Python syntax and static checks`, `Build source package`, and
  `CodeQL analysis`.
- Unresolved questions: none.

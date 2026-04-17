# Generation And Rendering

## Generate A Specific Topic

```powershell
python run_pipeline.py --topic "What an ETF is in under 60 seconds"
```

The pipeline asks Ollama for metadata and script, runs the quality gate,
generates voice with Piper, creates timings with WhisperX, renders scenes with
Pillow, and builds `short.mp4` with FFmpeg.

## Generate A Random Unused Topic

```powershell
python run_pipeline.py
```

The random picker reads `topics.txt`, avoids topics already represented under
`outputs/`, and can refill exhausted topic lists with Ollama-generated titles.

Disable automatic refill:

```powershell
python run_pipeline.py --auto-generate-topics 0
```

## Generate Topics Only

```powershell
python run_pipeline.py --generate-topics 20 --topics-only
```

## Outputs

Each generated video writes to:

```text
outputs/<video-slug>/
|-- script.txt
|-- metadata.json
|-- voice.wav
|-- scenes/
|-- scenes.txt
`-- short.mp4
```

Generated outputs are ignored by git.

## Captions

WhisperX supplies timings, but displayed caption words are aligned back to the
approved script before chunking. This prevents ASR slips from becoming visible
caption text.

Default caption mode is progressive semantic captioning:

```json
"captions": {
  "mode": "progressive",
  "min_words": 3,
  "max_words": 6,
  "max_seconds": 2.8
}
```

## Backgrounds And Music

Optional background images:

```text
assets/backgrounds/default/
assets/backgrounds/<topic-slug>/
```

Optional local music:

```text
assets/music/library/
```

If no background images exist, the renderer generates finance-themed chart
backgrounds automatically.

## Quality Commands

```powershell
python -m compileall -q generate_short.py run_pipeline.py setup_channel.py upload_youtube.py test_voice.py
ruff check --output-format=github .
bandit -q -r . --severity-level medium --confidence-level high -x ./.git,./.venv,./outputs,./voices,./assets/music
```

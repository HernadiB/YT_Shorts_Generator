# Contributing

This repository is a local-first pipeline for generating and reviewing finance
YouTube Shorts. Keep changes focused, auditable, and safe for a workflow that
uses local credentials and generated media.

## Development Flow

1. Branch from `development`.
2. Keep secrets, OAuth files, generated videos, local config, and voice assets
   out of commits.
3. Run the relevant checks before opening a pull request.
4. Use private YouTube uploads for review until the output quality is stable.

## Local Checks

```powershell
python -m compileall -q generate_short.py run_pipeline.py setup_channel.py upload_youtube.py test_voice.py
ruff check --output-format=github .
bandit -q -r . --severity-level medium --confidence-level high -x ./.git,./.venv,./outputs,./voices,./assets/music
```

## Review Standard

Runtime changes should preserve:

- Script factual accuracy and finance-claim safety.
- Caption sync against the approved script.
- Local-only handling of OAuth credentials and generated media.
- Private-first upload review before publication.

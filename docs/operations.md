# Operations

## CI

GitHub Actions runs static analysis on `development`, `master`, and pull
requests. Package builds run on pull requests and on pushes to `development` and
`master`.

- Python syntax check with `compileall`
- Ruff
- Bandit
- Package artifact build
- CodeQL

Workflow files:

```text
.github/workflows/static-analysis.yml
.github/workflows/package.yml
.github/workflows/codeql.yml
```

## Troubleshooting

Ollama:

```powershell
ollama serve
ollama pull llama3.1:8b
```

FFmpeg:

```powershell
ffmpeg -version
ffprobe -version
```

Piper:

```powershell
python test_voice.py
```

WhisperX:

```powershell
python -c "import whisperx; print('whisperx ok')"
```

If YouTube upload fails, confirm `client_secret.json` is valid and delete local
`token.json` only when you intentionally want to restart the OAuth flow.

## Recommended Workflow

1. Start the dev session with `.\start_dev.ps1`.
2. Generate a private Short.
3. Review script accuracy, voice, captions, background relevance, and metadata.
4. Upload privately first.
5. Publish manually only after review.
6. Stop local services with `.\stop_dev.ps1`.

## Public Repository Safety

The repository is public so GitHub Pages and branch/ruleset protection can be
used without a paid private-repo plan.

Before committing:

- Check `git status --short`.
- Keep secrets and generated files ignored.
- Do not add OAuth files or local config.
- Keep local auth inventory in `.dev/auth.local.md` and keep temporary auth
  scratch files under ignored paths such as `.dev/`, `.secrets/`, or
  `auth.local.*`.
- Do not commit generated media.
- Prefer source-only release packages built from git-tracked files.

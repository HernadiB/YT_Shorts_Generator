# Releases And Packages

Last updated: 2026-04-17

This project is a local automation pipeline, not a published Python library.
Release packages are source archives attached to GitHub Releases until the
project has a stable installable CLI or module layout.

## Versioning

Use semantic versions with a leading `v`:

- `v0.1.0`
- `v0.2.0`
- `v1.0.0`
- `v1.0.0-rc.1`

Recommended milestone mapping:

- `v0.1.x`: repository governance, setup, and operating workflow.
- `v0.2.x`: generation quality, tests, and rendering reliability.
- `v1.0.0`: stable private-first Shorts generation and upload workflow.

## Release Rules

- Release from reviewed and merged code.
- Merge `development` into `master` through a reviewed PR before tagging a
  release.
- Create release tags from `master`.
- Run static analysis before a release.
- Do not include generated media, local voice assets, OAuth files, token files,
  `.env`, or local `config.json` in release assets.
- Mark early releases as prereleases until the generation and upload workflow is
  stable.
- If a prerelease tag triggers a failed workflow before a GitHub Release is
  published, fix the workflow and publish the next prerelease tag instead of
  rewriting public release history.

## Package Format

The release workflow builds:

- `finance-shorts-factory-<version>.zip`
- `finance-shorts-factory-<version>.tar.gz`
- `SHA256SUMS.txt`

These packages are produced with `git archive`, so ignored local files and
untracked generated media are not included.

## Workflows

Package workflow:

```text
.github/workflows/package.yml
```

The package workflow runs for PRs, pushes to `development`, and manual dispatch.
It creates downloadable build artifacts without creating a GitHub Release.

Release workflow:

```text
.github/workflows/release.yml
```

The release workflow runs for tags matching `v*` and manual dispatch. It runs
the static checks, builds source archives, creates checksums, and publishes a
GitHub Release.

CodeQL workflow:

```text
.github/workflows/codeql.yml
```

CodeQL runs on pushes, PRs, and manual dispatch to add another security check.

## Manual Release Flow

1. Confirm the target branch is clean and reviewed.
2. Confirm static checks pass.
3. Create and push a tag:

```powershell
git switch master
git pull
git tag v0.1.0-rc.2
git push origin v0.1.0-rc.2
```

4. Review the generated GitHub Release.
5. Verify archive checksums from `SHA256SUMS.txt`.

## Release History

- `v0.1.0-rc.1`: tag workflow started but failed before release publication
  because version validation used an over-escaped bash regex.
- `v0.1.0-rc.2`: first published prerelease. Assets:
  ZIP, TAR.GZ, and `SHA256SUMS.txt`.

## Future Package Options

Only add these when there is a real need:

- Python package: requires a proper package layout and `pyproject.toml`.
- Windows installer: useful only after dependency setup stabilizes.
- Container image: not recommended yet because the pipeline depends on local
  Windows paths, Piper voice assets, GPU/WhisperX behavior, and OAuth flows.

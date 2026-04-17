# GitHub Governance

Last updated: 2026-04-17

This file records the repository operating rules and the GitHub setup actions
already applied to `HernadiB/YT_Shorts_Generator`.

## Repository Operating Rules

- Treat `development` as the default development branch.
- Use pull requests for non-trivial changes.
- Keep each PR focused on one change set.
- Assign every PR to `HernadiB` until more maintainers exist.
- Add labels that describe type, area, status, and priority.
- Add each PR or issue to the closest active milestone.
- Do not commit generated media, local config, OAuth tokens, API keys, or
  credential files.
- Run static checks before review:

```powershell
python -m compileall -q generate_short.py run_pipeline.py setup_channel.py upload_youtube.py test_voice.py
ruff check --output-format=github .
bandit -q -r . --severity-level medium --confidence-level high -x ./.git,./.venv,./outputs,./voices,./assets/music
```

## Pull Request Rules

Every PR should include:

- Clear summary.
- Verification commands or manual review notes.
- Risk note for runtime, upload, OAuth, or generated-media behavior.
- Relevant labels.
- Milestone.
- Assignee.

Reviewer rule:

- Request a reviewer when the reviewer is not the PR author.
- GitHub does not allow requesting the PR author as reviewer. When `HernadiB`
  authors a PR, assign it to `HernadiB` instead of requesting review from
  `HernadiB`.

## Label Set

Type labels:

- `type: bug`
- `type: feature`
- `type: task`
- `type: docs`

Status labels:

- `status: triage`
- `status: in progress`
- `status: blocked`
- `status: ready for review`

Priority labels:

- `priority: p0`
- `priority: p1`
- `priority: p2`

Area labels:

- `area: setup`
- `area: generation`
- `area: quality`
- `area: rendering`
- `area: upload`
- `area: documentation`
- `area: github-actions`

Dependency labels:

- `dependencies`
- `python`

## Milestones

- `v0.1 Repository Governance`: GitHub governance, Pages, templates, labels,
  milestones, and branch protection.
- `v0.2 Generation Quality`: generation quality, pacing, captions, finance
  checks, and review workflows.
- `v1.0 Stable Shorts Pipeline`: stable private-first generation and upload
  workflow for reviewed finance Shorts.

## Desired Branch Protection

The intended protection for `development` and `master` is:

- Require pull request before merging.
- Require at least one approving review.
- Dismiss stale approvals after new commits.
- Require code owner review.
- Require status checks to pass.
- Require the static analysis check.
- Require conversation resolution.
- Enforce for admins.
- Disallow force pushes.
- Disallow branch deletion.
- Prefer linear history.

Current blocker:

- GitHub returned `Upgrade to GitHub Pro or make this repository public to
  enable this feature.` for protected branches on this private repository.

Do not make the repository public only to enable branch protection unless the
local credential and generated-media risks have been reviewed.

## GitHub Pages

The repository contains a workflow-based Pages setup:

- `.github/workflows/pages.yml`
- `docs/index.html`

Current blocker:

- GitHub returned `Your current plan does not support GitHub Pages for this
  repository.` for this private repository.

When the plan supports private Pages, or when the repository is intentionally
made public, enable Pages with workflow deployments.

## GitHub Projects

Desired board:

- `Finance Shorts Factory Development`

Suggested columns:

- `Triage`
- `Ready`
- `In Progress`
- `Review`
- `Done`

Current blocker:

- Project v2 commands require additional token scopes such as `project`,
  `read:project`, `read:org`, and `read:discussion`.

## Applied Setup Log

Completed:

- Installed GitHub CLI locally.
- Used the existing Git Credential Manager token without printing it.
- Confirmed authenticated user is `HernadiB`.
- Confirmed repository permission is `ADMIN`.
- Created branch `chore/github-governance-pages`.
- Added CODEOWNERS, PR template, issue templates, Dependabot, Pages workflow,
  contributing guide, security policy, and static Pages site.
- Pushed `chore/github-governance-pages`.
- Created PR #3: `Add GitHub governance and Pages setup`.
- Assigned PR #3 to `HernadiB`.
- Applied labels to PR #3:
  - `type: task`
  - `area: documentation`
  - `area: github-actions`
  - `status: ready for review`
- Assigned PR #3 to milestone `v0.1 Repository Governance`.
- Created or updated the standard label set.
- Created milestones `v0.1 Repository Governance`, `v0.2 Generation Quality`,
  and `v1.0 Stable Shorts Pipeline`.
- Patched repository settings for issues, projects, merge strategy, auto-merge,
  update branch, and delete branch on merge where GitHub allowed it.
- Created initial issue backlog:
  - #4 `Harden development environment startup and shutdown`
  - #5 `Document private-first upload review checklist`
  - #6 `Add quality-gate regression fixtures`
  - #7 `Add caption and render smoke tests`
  - #8 `Define v1.0 release checklist for stable Shorts pipeline`
- Applied governance metadata to PR #2:
  - Labels: `type: task`, `area: setup`, `area: github-actions`,
    `status: ready for review`, `priority: p1`
  - Milestone: `v0.1 Repository Governance`
  - Assignee: `HernadiB`
  - Added a PR comment explaining the reviewer-author limitation.

Blocked or partial:

- GitHub Pages could not be enabled because the private repository plan does
  not support Pages.
- Branch protection could not be enabled because the private repository plan
  does not support protected branches.
- Project v2 could not be created because the current token lacks required
  project/org scopes.
- `HernadiB` could not be requested as reviewer on PRs authored by `HernadiB`
  because GitHub rejects review requests from the PR author.

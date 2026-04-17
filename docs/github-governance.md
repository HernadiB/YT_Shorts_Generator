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
- `type: release`

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
- `area: release`

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

## Branch Protection

Protection for `development` and `master` is managed with a repository ruleset:

```text
Protect development and master
```

Rules:

- Require pull request before merging.
- Require at least one approving review.
- Dismiss stale approvals after new commits.
- Require code owner review.
- Require status checks to pass.
- Require the static analysis check now.
- Add package and CodeQL checks to the required list after those workflows are
  merged to the protected branches.
- Require conversation resolution.
- Disallow force pushes.
- Disallow branch deletion.
- Prefer linear history.

Implementation notes:

- The repository was made public on 2026-04-17 after a quick tracked-file and
  history-name scan did not find committed local secret files such as `.env`,
  `config.json`, OAuth token files, or generated media.
- The classic branch protection endpoint was not usable for this user-owned
  repository because of `restrictions` payload validation. A repository ruleset
  was created instead.

## GitHub Pages

The repository contains a workflow-based Pages setup:

- `.github/workflows/pages.yml`
- `docs/index.html`

Current state:

- GitHub Pages is enabled with workflow deployments.
- URL: `https://hernadib.github.io/YT_Shorts_Generator/`
- HTTPS is enforced.
- The Pages workflow will publish after the workflow is merged to
  `development`.

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

## Release And Package Rules

- Use semantic versions with a leading `v`.
- Build packages through `.github/workflows/package.yml`.
- Publish releases through `.github/workflows/release.yml`.
- Attach ZIP, TAR.GZ, and SHA256 checksum assets to each GitHub Release.
- Keep generated media, local assets, OAuth files, tokens, `.env`, and
  `config.json` out of release packages.
- Treat source release archives as the package format until the project has a
  stable installable CLI or Python module layout.

Details are stored in:

```text
docs/release-package.md
```

## Applied Setup Log

Completed:

- Installed GitHub CLI locally.
- Used the existing Git Credential Manager token without printing it.
- Confirmed authenticated user is `HernadiB`.
- Confirmed repository permission is `ADMIN`.
- Ran a quick public-readiness scan for committed local secret file names and
  tracked secret-like patterns.
- Made the repository public so GitHub Pages and branch/ruleset protection can
  be enabled without a paid private-repo plan.
- Created branch `chore/github-governance-pages`.
- Added CODEOWNERS, PR template, issue templates, Dependabot, Pages workflow,
  contributing guide, security policy, and static Pages site.
- Added release/package governance with package, release, and CodeQL workflows.
- Pushed `chore/github-governance-pages`.
- Created PR #3: `Add GitHub governance and Pages setup`.
- PR #3 was merged to `development`.
- Assigned PR #3 to `HernadiB`.
- Applied labels to PR #3:
  - `type: task`
  - `type: release`
  - `area: documentation`
  - `area: github-actions`
  - `area: release`
  - `status: ready for review`
- Assigned PR #3 to milestone `v0.1 Repository Governance`.
- Created or updated the standard label set.
- Created milestones `v0.1 Repository Governance`, `v0.2 Generation Quality`,
  and `v1.0 Stable Shorts Pipeline`.
- Patched repository settings for issues, projects, merge strategy, auto-merge,
  update branch, and delete branch on merge where GitHub allowed it.
- Enabled GitHub Pages with workflow deployments.
- Set repository homepage and topics.
- Enabled Dependabot vulnerability alerts, automated security fixes, secret
  scanning, secret scanning push protection, and Dependabot security updates
  where GitHub allowed it.
- Created the `Protect development and master` repository ruleset.
- Created initial issue backlog:
  - #4 `Harden development environment startup and shutdown`
  - #5 `Document private-first upload review checklist`
  - #6 `Add quality-gate regression fixtures`
  - #7 `Add caption and render smoke tests`
  - #8 `Define v1.0 release checklist for stable Shorts pipeline`
  - #15 `Prepare v0.1.0 prerelease`
- Applied governance metadata to PR #2:
  - Labels: `type: task`, `area: setup`, `area: github-actions`,
    `status: ready for review`, `priority: p1`
  - Milestone: `v0.1 Repository Governance`
  - Assignee: `HernadiB`
  - Added a PR comment explaining the reviewer-author limitation.
- Created PR #16: `Add release packaging and split documentation`.
- Assigned PR #16 to `HernadiB`.
- Applied labels to PR #16:
  - `type: task`
  - `type: release`
  - `area: release`
  - `area: documentation`
  - `area: github-actions`
  - `status: ready for review`
- Assigned PR #16 to milestone `v0.1 Repository Governance`.
- Deleted stale remote branch `chore/github-governance-pages` after PR #3 was
  merged; release/docs work now lives on `chore/release-packaging-docs`.

Blocked or partial:

- GitHub Pages initially could not be enabled because the private repository
  plan did not support Pages. This was resolved by making the repository public.
- Classic branch protection could not be enabled through the branch protection
  endpoint because of user-owned repository restrictions validation. This was
  handled with a repository ruleset instead.
- Project v2 could not be created because the current token lacks required
  project/org scopes.
- `HernadiB` could not be requested as reviewer on PRs authored by `HernadiB`
  because GitHub rejects review requests from the PR author.

# GitHub Governance

Last updated: 2026-04-17

This file records the repository operating rules and the GitHub setup actions
already applied to `HernadiB/YT_Shorts_Generator`.

## Repository Operating Rules

- Treat `master` as the GitHub default branch and stable release branch.
- Use `development` as the integration branch for work that is not ready for a
  stable release.
- Use pull requests for non-trivial changes.
- Keep each PR focused on one change set.
- Assign every PR to `HernadiB` until more maintainers exist.
- Add labels that describe type, area, status, and priority.
- Add each PR or issue to the closest active milestone.
- Keep issues and pull requests linked in both directions. Every non-dependency
  PR must reference at least one issue, and every active issue must link back to
  the PR carrying the work.
- Do not commit generated media, local config, OAuth tokens, API keys, or
  credential files.
- Keep local auth inventory and any temporary auth scratch files in ignored
  paths such as `.dev/`, `.secrets/`, or `auth.local.*`.
- Run static checks before review:

```powershell
python -m compileall -q generate_short.py run_pipeline.py setup_channel.py upload_youtube.py test_voice.py
ruff check --output-format=github .
bandit -q -r . --severity-level medium --confidence-level high -x ./.git,./.venv,./outputs,./voices,./assets/music
```

## Pull Request Rules

Every PR should include:

- Clear summary.
- Related issue reference, using `Fixes #...`, `Closes #...`, or `Related #...`.
- Verification commands or manual review notes.
- Risk note for runtime, upload, OAuth, or generated-media behavior.
- Relevant labels.
- Milestone.
- Assignee.

Issue association rule:

- Use closing keywords only when the PR fully completes the issue.
- Use `Related #...` for planning, partial work, follow-up work, or release
  coordination that should not close the issue.
- Add a reciprocal issue comment when the issue body does not already reference
  the PR.
- Dependabot PRs can stand alone when the PR itself is the complete update.
- Keep PR labels, milestone, assignee, and status label current whenever scope
  or review status changes.

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
- Require these status checks:
  - `Python syntax and static checks`
  - `Build source package`
  - `CodeQL analysis`
- Require conversation resolution.
- Disallow force pushes.
- Disallow branch deletion.
- Prefer linear history.
- Allow repository admins to bypass pull-request requirements only through a
  PR merge when required self-review rules cannot be satisfied in this one-user
  repository. Status checks should still be green before using this bypass.
- Keep merge commits enabled at repository level for controlled branch
  promotion PRs, while normal feature PRs should still prefer focused squash
  merges.

Implementation notes:

- The repository was made public on 2026-04-17 after a quick tracked-file and
  history-name scan did not find committed local secret files such as `.env`,
  `config.json`, OAuth token files, or generated media.
- The classic branch protection endpoint was not usable for this user-owned
  repository because of `restrictions` payload validation. A repository ruleset
  was created instead.
- The ruleset includes a PR-only repository-admin bypass so the owner can merge
  green PRs when GitHub blocks self-review, without allowing direct force pushes
  or branch deletion.
- Package and CodeQL checks were added to the required status check list after
  those workflows had passed on PRs and protected branches.

## GitHub Pages

The repository contains a workflow-based Pages setup:

- `.github/workflows/pages.yml`
- `docs/index.html`

Current state:

- GitHub Pages is enabled with workflow deployments.
- URL: `https://hernadib.github.io/YT_Shorts_Generator/`
- HTTPS is enforced.
- The Pages workflow publishes from `master`.
- The workflow uses `actions/configure-pages` with `enablement: true` so the
  deployment can create or repair the Actions-backed Pages configuration when
  GitHub returns a Pages site lookup as not found.

## MCP And Cloud Agent

Use MCP servers only when they materially improve a task.

Current state:

- This local Codex session has no configured MCP resources or resource
  templates.
- GitHub Copilot coding agent has built-in MCP support for GitHub and browser
  automation, so do not add a third-party MCP server unless a concrete project
  task needs it.
- Any new MCP server must have a narrow purpose, minimal permissions, and a
  documented auth path before it is enabled.

References:

- `https://docs.github.com/en/copilot/concepts/coding-agent/mcp-and-coding-agent`
- `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/extend-coding-agent-with-mcp`

## Local Auth Inventory

Local auth files are intentionally untracked:

- `.dev/auth.local.md`: local inventory of auth sources used during agent work.
- `.dev/*.local.env`: optional local environment files for temporary tokens if
  the user explicitly wants to manage them outside Git Credential Manager.
- `.secrets/`: local scratch area for credentials that must never be committed.

The GitHub API work in this repository uses the existing Git Credential Manager
credential for `github.com` and exports it only into the current shell as
`GH_TOKEN`. The token value is not copied into project documentation or tracked
files.

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
- Changed the GitHub default branch from `development` to `master`.
- Updated local `origin/HEAD` to resolve to `master`.
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
- Updated the PR/issue operating rule: every non-dependency PR must link an
  issue, and every active issue must link back to its carrying PR.
- Updated the PR template and issue templates with linked issue/PR fields.
- Fixed the Pages workflow after `actions/configure-pages` failed at the Pages
  site lookup step with a 404 despite Pages being enabled; the workflow now
  passes `enablement: true`.
- Added a PR-only repository-admin bypass actor to the ruleset after GitHub
  blocked a green owner-authored PR because the same user cannot approve their
  own last push.
- Merged PR #16 to `development`; the next Pages deployment succeeded.
- Closed issue #17 after the Pages deployment fix was verified.
- Closed issue #5 after the private-first upload review checklist moved into
  the split documentation.
- Created PR #18 from `release/master-promotion` after PR #9 was dirty against
  `master`; PR #18 kept the current `development` versions of `README.md` and
  `AGENTS.md`, passed checks, and merged to `master`.
- Closed PR #9 as superseded by PR #18.
- Tagged `v0.1.0-rc.1`; the release workflow failed before publishing because
  the version regex was over-escaped.
- Merged PR #19 to fix release version validation, then PR #20 to promote that
  fix to `master`.
- Published GitHub Release `v0.1.0-rc.2` as a prerelease with ZIP, TAR.GZ, and
  SHA256SUMS assets.
- Closed issues #4 and #15 as completed.
- Closed milestone `v0.1 Repository Governance`.
- Added `Build source package` and `CodeQL analysis` to the protected branch
  required status checks.
- Updated Pages publishing and public documentation links to use `master`.
- Recorded the MCP/cloud-agent policy and local auth inventory path.
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

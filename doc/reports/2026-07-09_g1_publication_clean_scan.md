# G1 Publication Clean Scan Report

Date: 2026-07-09

## Scope

G1 from `codex_github_publication_work_order.md` covers public-release cleanup before GitHub publication:

- scan current files for local paths, personal identifiers, environment paths, and token-like strings
- sanitize tracked documentation
- check screenshot artifacts
- inspect Git history for previously committed sensitive/local data
- report whether history rewrite is required before push

## Current Working Tree Scan

Patterns checked:

- user/environment markers, local user profile paths, local workspace paths, and runtime cache paths
- common token-like prefixes for API keys and cloud credentials
- email-like strings
- UNC path prefixes

Result after cleanup:

```text
current tracked/untracked text scan: no matches
```

Sanitized files:

- `doc/implementation_status_phase1_8.md`
- `doc/implementation_status_v2_1.md`
- `doc/implementation_status_v2_3_ui_i18n.md`

Changes made:

- replaced local Python runtime paths with `<python>`
- replaced local workspace paths with `<workspace>`
- removed user-specific temp path examples from reports

## Screenshots

Root-level `capture-*.png` files are present locally but are ignored by `.gitignore`.

```text
capture-*.png: ignored, untracked
```

These should not be published from the repository root. Clean screenshots for README use should be regenerated under `doc/images/` during G3.

## Git History Scan

History still contains local/private data:

- commit author identity contains a personal email address
- previous report revisions contain local absolute paths such as user profile and workspace paths

Examples found in history:

```text
Author: TJ16th <personal email>
<workspace absolute path>
<user profile python runtime path>
```

## History Rewrite Status

History rewrite was approved by the project owner after this scan and performed with a clean orphan-branch publication commit.

Post-rewrite expectations:

1. the public branch contains a single initial commit
2. old task-sized local commits are no longer reachable from branch refs
3. current-file scans remain clean before push
4. `git log --all -p` should no longer expose the previous local-path report revisions

## G1 Status

| Item | Status |
|---|---|
| Current file scan | Clean |
| Tracked docs sanitized | Done |
| Screenshot publication risk | Controlled by `.gitignore`; clean screenshots still needed for README |
| Git history scan | Findings were present before rewrite |
| History rewrite | Approved and performed after G1 scan |

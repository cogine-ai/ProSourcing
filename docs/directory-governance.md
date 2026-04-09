# Directory Governance

## Why This Exists

The repository root currently mixes production entrypoints, one-off scripts, debug helpers, generated data, backups, and temporary artifacts. That makes ownership unclear and increases the chance of duplicate files or new clutter landing in root.

This document defines the target placement rules for new work and a low-risk cleanup plan for existing files.

## Root Allowlist

The repository root should be limited to:

- project control files such as `.gitignore`, `.editorconfig`, `.gitattributes`, `.dockerignore`
- environment samples such as `.env.example`
- onboarding documents such as `README.md` and `AGENT.md`
- dependency manifests such as `package.json`, `package-lock.json`, `requirements.txt`
- root entrypoint infrastructure files such as `docker-compose.yml` and `Dockerfile.*`
- intentionally top-level SQL/bootstrap files that act as setup entrypoints

Everything else should normally live in a domain directory.

## Placement Rules

| File type | Target location | Notes |
| --- | --- | --- |
| Production backend code | `api/`, `core/`, `scrapers/`, `utils/` | Keep domain ownership explicit |
| Frontend code | `frontend/`, `frontend_pro/` | Keep app-specific assets close to the app |
| Operational scripts | `scripts/` | Includes backfills, exports, migrations, and repair tools |
| Automated tests | `tests/` | Keep fixtures close to tests where possible |
| Documentation | `docs/` | Design, runbook, governance, and migration docs |
| Runtime logs | `logs/` | Logs should not live in root |
| Generated outputs | `output/` | Exports, reports, generated deliverables |
| Temporary debug artifacts | `tmp/` | Scratch files, experimental JSON, one-off inspection outputs |
| Deployment-only artifacts | `deployment_package/` | Separate deployment payloads from source code |

## Naming Rules

Disallow low-signal duplicate naming patterns for new files:

- `*_bak`, `*.bak`
- `*_backup`
- `*_copy`
- `*_new`
- `*_final`
- `*_temp`
- `*_test`
- `*_v2`, `*_v3`

Preferred naming pattern:

- describe the action: `backfill_last_crawl_date.py`
- describe the scope: `export_full_seeds.py`
- describe the lifecycle when needed: `tmp/category-tree-snapshot.json`

## Current Root Inventory Assessment

Observed root-level clutter falls into a few categories:

1. Debug and inspection scripts such as `debug_*.py`, `check_*.py`, `probe_*.py`, `inspect_*.py`
2. Temporary or generated data such as `*_debug.json`, `pr_feedback*.json`, `kaspi_full_tree_raw.json`, `全部分类信息.txt`
3. Duplicate or suffix-based files such as `App.jsx.bak`, `debug_categories_v2.py`, `drop_and_rebuild_v2.sql`
4. Test-like scripts stored outside `tests/` such as `test_*.py`
5. One-off repair and export scripts that belong under `scripts/`

## Allowed Exceptions

Some current root files may remain temporarily because they are already referenced by tooling, docs, or deployment workflows. Those files should be treated as migration exceptions, not as a pattern to copy.

## Cleanup Plan

### Phase 1: Stop the Bleeding

- enforce `AGENT.md` for all future human and agent edits
- route all new temporary/debug files to `tmp/`, `logs/`, or `output/`
- route all new one-off scripts to `scripts/`

### Phase 2: Safe Rehoming

- move root-level debug helpers into `tmp/` or `scripts/` based on whether they are reusable
- move root-level `test_*.py` scripts into `tests/` or archive them if obsolete
- move generated JSON, HTML, TXT, and log artifacts into `tmp/` or `output/`
- move governance and process docs into `docs/`

### Phase 3: De-duplication

- consolidate suffix variants into one canonical script
- remove backup files once the canonical file is confirmed in git history
- rename ambiguous scripts to task-oriented names

### Phase 4: Guardrails

- add targeted `.gitignore` entries if new generated artifacts appear repeatedly
- update developer onboarding docs when directory ownership changes
- batch cleanup by category so each PR is reviewable and low risk

## Review Checklist For Future PRs

- Does this change create a new root-level file?
- Can an existing file be extended instead?
- Is the file in the correct directory for its lifecycle?
- Does the name avoid duplicate suffix patterns?
- If a file is temporary, is it isolated in `tmp/`, `logs/`, or `output/`?

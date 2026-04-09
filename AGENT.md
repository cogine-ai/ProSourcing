# Repository Working Rules

This repository already contains backend code, frontend apps, deployment assets, scripts, generated output, and historical debug artifacts. To keep the tree maintainable, humans and agents should follow these rules before creating or moving files.

## Core Principles

1. Do not create new files in the repository root unless they are root-level project controls.
2. Reuse an existing directory and an existing file before creating a new file.
3. Prefer extending the canonical implementation over creating suffix variants such as `*_v2`, `*_final`, `*_new`, `*_bak`, `*_copy`, or `*_test`.
4. Keep directory depth shallow and purposeful. Avoid adding extra nesting unless it improves ownership or discoverability.
5. Put temporary, generated, and debug artifacts in dedicated holding directories so they can be cleaned safely later.

## What May Stay In Root

Only a small set of files should live at the repository root:

- repository controls: `.gitignore`, `.gitattributes`, `.editorconfig`, `.dockerignore`
- environment samples: `.env.example`
- top-level onboarding docs: `README.md`, `AGENT.md`
- package and dependency entrypoints: `package.json`, `package-lock.json`, `requirements.txt`
- container and compose entrypoints: `docker-compose.yml`, `Dockerfile.*`
- root-level SQL/bootstrap files that are intentionally used as project entrypoints

If a new file does not clearly belong to one of those categories, it should not be added to root.

## Directory Ownership

- `api/`, `core/`, `scrapers/`, `utils/`: production Python code
- `frontend/`, `frontend_pro/`: frontend applications
- `scripts/`: operational scripts, one-off repair scripts, import/export helpers, and maintenance tooling
- `tests/`: automated tests and test fixtures
- `docs/`: design notes, runbooks, governance docs, migration notes, and collaboration guidance
- `deployment_package/`: deployment-only assets and packaged data
- `assets/`, `templates/`: reusable static assets and templates
- `logs/`: runtime logs
- `output/`: generated exports and deliverables
- `tmp/`: local experiments, scratch files, temporary debug helpers, and disposable intermediate data

## File Creation Rules

- Before creating a new script, check whether an existing script can be extended or renamed for clarity.
- New debugging helpers belong in `tmp/` unless they are reusable operational tools, in which case they belong in `scripts/`.
- New ad hoc JSON, HTML, TXT, and log outputs belong in `tmp/`, `output/`, or `logs/`, not root.
- New documentation belongs in `docs/` unless it is the main project entry document.
- New test helpers belong in `tests/`.
- Backups should be captured in git history, not as duplicate files in the working tree.

## Naming Rules

Avoid creating files with low-signal suffixes or duplicate semantics:

- forbidden patterns: `*_bak`, `*.bak`, `*_backup`, `*_copy`, `*_new`, `*_final`, `*_temp`, `*_test`, `*_v2`, `*_v3`
- prefer descriptive names that explain purpose, scope, and lifecycle
- if a script is one-time-use, place it in `scripts/` and name it after the task it performs

## Existing Root Clutter Guidance

The current repository still contains historical root-level debug files, generated JSON, backup files, and exploratory scripts. Do not add more files in that style. When touching related areas:

- migrate reusable scripts into `scripts/`
- move disposable artifacts into `tmp/` or `output/`
- fold duplicate script variants into one maintained file where safe
- document non-obvious exceptions in `docs/`

## Change Safety

- Do not reorganize large sets of files in the same PR as behavioral code changes.
- For cleanup work, prefer small batches grouped by file type or ownership.
- Before moving a file, confirm imports, references, docs, and automation paths still resolve.

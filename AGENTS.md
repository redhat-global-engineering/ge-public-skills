# ge-public-skills — agent context

## What this repo is

A curated registry of AI coding assistant skills from upstream open-source
repositories. Skills are declared in `registry.yaml`, pinned by commit SHA
digest, and validated nightly. The registry produces a Claude Code marketplace
file and a GitHub Pages documentation site.

Uses [opendatahub-io/skills-registry](https://github.com/opendatahub-io/skills-registry)
as a git submodule for validation, marketplace generation, and site generation.

## Architecture

`registry.yaml` is the source of truth. It declares plugins hosted in external
repos, each pinned by a 40-character commit SHA. No skill files are stored
locally — the registry is a collection of references.

### Nightly digest updates

A GitHub Actions cron job (`update-digests.yaml`) runs daily at 06:00 UTC:

1. Resolves the latest commit SHA for each plugin's declared branch
2. If the SHA has changed, clones the repo and runs the full lint pipeline
3. If linting passes, updates the SHA in `registry.yaml` and pushes to main
4. If linting fails, files or updates a GitHub issue tagged `digest-update-failure`

### Generated artifacts

All generated from `registry.yaml`:

- `.claude-plugin/marketplace.json` — Claude Code plugin marketplace
- `site/` — MkDocs Material documentation site (deployed to GitHub Pages)
- `catalog.md` — Human-readable skill catalog

## registry.yaml format

```yaml
name: ge-public-skills
owner:
  name: Red Hat Global Engineering
description: Curated AI coding assistant skills
categories:
  category-key:
    name: Category Name
    description: What this category covers
plugins:
  - name: plugin-name
    description: What this plugin does
    version: "1.0.0"
    category: category-key
    source:
      type: github
      repo: org/repo
      ref: main
      sha: <40-char commit SHA>
    skills:
      - name: skill-name
        description: What this skill does
```

### Adding a new plugin

Open a PR that adds an entry to `registry.yaml`. CI will validate the schema.
Once merged, the nightly workflow will resolve the SHA and run linting.

For plugins from repos without `.claude-plugin/plugin.json`, set `strict: false`
and specify `skills_dir`.

## Validation

Three layers of validation run on each plugin:

1. **Schema validation** — JSON schema check on `registry.yaml` structure
2. **Contract validation** — Canonical functions, metrics, problem statements
3. **Custom linters** (`scripts/custom_linters.py`) — SKILL.md presence,
   frontmatter validity, name-directory match

## Commands

```bash
# Run tests
pytest tests/ -v

# Generate marketplace.json
PYTHONPATH=skills-registry python scripts/generate.py marketplace

# Generate MkDocs site
PYTHONPATH=skills-registry python scripts/generate.py site

# Generate everything
PYTHONPATH=skills-registry python scripts/generate.py all

# Update digests (usually run by CI)
PYTHONPATH=skills-registry python scripts/update_digests.py

# Dry-run digest update
PYTHONPATH=skills-registry python scripts/update_digests.py --dry-run
```

## What NOT to do

- Do not manually edit `.claude-plugin/marketplace.json` — it is auto-generated
- Do not manually edit generated site files under `site/docs/plugins/` or
  `site/docs/categories/` — they are auto-generated
- Do not edit files in the `skills-registry/` submodule — it tracks upstream

# ge-public-skills — agent context

## What this repo is

A curated, automatically-synced collection of generally-useful AI coding assistant skills drawn from upstream open-source repositories. Skills are declared in `sync-manifest.yaml` and synced by CI automation that opens per-skill PRs with auto-merge.

## Skill layout

Skills follow the [AgentSkills.io](https://agentskills.io/) standard:

```
skills/<skill-name>/
├── SKILL.md              # Primary skill file (required)
├── references/           # Optional supporting docs
├── scripts/              # Optional helper scripts
└── evals/                # Optional evaluation cases
```

The `name` field in SKILL.md frontmatter must match the directory name (kebab-case).

## How skills get here

1. A contributor opens a PR that adds an entry to `sync-manifest.yaml`
2. The Lint CI workflow fetches the new skill from the upstream repo and lints it (without committing it to the PR)
3. If lint passes, a maintainer merges the PR
4. The Sync workflow runs post-merge, clones the upstream, and commits the skill content to `skills/`
5. Post-merge, `.claude-plugin/marketplace.json` is regenerated

### Adding a new skill

Open a PR that adds an entry to `sync-manifest.yaml`:

```yaml
sources:
  - repo: https://github.com/org/repo
    ref: main
    skills:
      - path: path/to/skill-directory
```

CI will automatically fetch the skill from the upstream repo and lint it. You don't need to include the skill content in your PR — only the manifest entry. If the upstream skill fails lint, CI will tell you what to fix upstream before the skill can be included.

## What you should know when working here

- **Never modify files under `skills/` directly.** They are mirrors of upstream content and will be overwritten on the next sync. To change which skills are included, edit `sync-manifest.yaml`.
- **Linting rules** (enforced by `scripts/lint.py` on every PR):
  1. No duplicate skill directory names across all sources
  2. Every `skills/<name>/` directory contains a SKILL.md
  3. SKILL.md has valid YAML frontmatter with non-empty `name` and `description`
  4. Frontmatter `name` matches the directory name
  5. `sync-manifest.yaml` is valid: all entries have `repo`, `ref`, `path`; no duplicate paths
- **Future linting** (not yet implemented): `skillsaw lint --strict`, evals presence check

## Commands

```bash
# Lint all skills and the manifest
python scripts/lint.py

# Generate marketplace.json from current skills/
python scripts/generate_marketplace.py

# Run tests
pytest tests/
```

## What NOT to do

- Do not manually add skill directories under `skills/` — use `sync-manifest.yaml`
- Do not edit synced skill content — changes will be overwritten
- Do not manually edit `.claude-plugin/marketplace.json` — it is auto-generated

# ge-public-skills

A curated, automatically-synced collection of AI coding assistant skills for use with [Claude Code](https://claude.ai/code), [Cursor](https://cursor.sh/), [Lola](https://github.com/LobsterTrap/lola), and other tools that support the [AgentSkills.io](https://agentskills.io/) standard.

Skills are drawn from upstream open-source repositories maintained by Red Hat teams. Automation syncs selected skills into this repo, where they're available for direct use or installation via plugin marketplaces.

## Using these skills

**Claude Code (plugin marketplace):**
```bash
/plugin marketplace add https://github.com/redhat-global-engineering/ge-public-skills.git
/plugin install <skill-name>
```

**Clone directly:**
```bash
git clone https://github.com/redhat-global-engineering/ge-public-skills.git
# Skills are in skills/<skill-name>/SKILL.md
```

**Lola:**
```bash
lola mod add https://github.com/redhat-global-engineering/ge-public-skills.git
lola install <skill-name>
```

## How it works

1. [`sync-manifest.yaml`](sync-manifest.yaml) declares which skills to pull from which upstream repos
2. A daily GitHub Actions workflow clones each upstream, compares content, and pushes updated skills directly to main
3. Skills removed from the manifest are automatically deleted
4. Post-merge, [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) is regenerated

## Adding a skill

Open a PR that adds an entry to [`sync-manifest.yaml`](sync-manifest.yaml):

```yaml
sources:
  - repo: https://github.com/org/repo
    ref: main
    skills:
      - path: path/to/skill-directory
```

You only need to edit the manifest — don't include the skill content in your PR. CI will automatically fetch the skill from the upstream repo and lint it. If the upstream skill fails lint, CI will tell you what needs to be fixed upstream before it can be included.

Once merged, the sync workflow will clone the upstream and commit the skill content.

## Layout

```
skills/<skill-name>/
├── SKILL.md              # Primary skill file (AgentSkills.io format)
├── references/           # Optional supporting docs
├── scripts/              # Optional helper scripts
└── evals/                # Optional evaluation cases
```

## License

[Apache-2.0](LICENSE)

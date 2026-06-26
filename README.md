# ge-public-skills

A curated registry of AI coding assistant skills for use with
[Claude Code](https://claude.ai/code) and other tools that support the
[AgentSkills.io](https://agentskills.io/) standard.

Skills are drawn from upstream open-source repositories maintained by Red Hat
teams. Each plugin is pinned by commit SHA and validated nightly.

**[Browse the catalog](https://redhat-global-engineering.github.io/ge-public-skills)**

## Using these skills

**Claude Code (plugin marketplace):**
```bash
claude plugin marketplace add redhat-global-engineering/ge-public-skills
/plugin install <plugin-name>@ge-public-skills
```

**Clone directly:**
```bash
git clone --recurse-submodules https://github.com/redhat-global-engineering/ge-public-skills.git
```

## How it works

1. [`registry.yaml`](registry.yaml) declares plugins and their source repos,
   each pinned by commit SHA
2. A nightly GitHub Actions workflow resolves the latest SHA for each plugin's
   branch
3. If the new SHA passes linting, the registry is updated automatically
4. If linting fails, a GitHub issue is filed with error details
5. On each registry update, the marketplace file and documentation site are
   regenerated

## Adding a plugin

Open a PR that adds an entry to [`registry.yaml`](registry.yaml):

```yaml
plugins:
  - name: my-plugin
    description: What it does
    version: "1.0.0"
    category: category-key
    source:
      type: github
      repo: org/repo
      ref: main
    skills:
      - name: my-skill
        description: What this skill does
```

The `sha` field will be filled in automatically by the nightly workflow once
your PR is merged.

## License

[Apache-2.0](LICENSE)

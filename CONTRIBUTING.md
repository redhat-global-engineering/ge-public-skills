# Contributing to ge-public-skills

This repo is a registry of pointers to public GitHub repos that contain AI coding assistant skills. No skill content is stored here — just `registry.yaml` entries that reference your repo by commit SHA.

## How to submit a plugin

1. **Your skills must be in a public GitHub repo** following the [AgentSkills.io](https://agentskills.io/) standard.

2. **Open a PR** adding your plugin to `registry.yaml`:

   ```yaml
   plugins:
     - name: your-plugin-name
       description: What it does
       version: "1.0.0"
       category: category-key
       source:
         type: github
         repo: your-org/your-repo
         ref: main
       skills:
         - name: skill-name
           description: What this skill does
   ```

   The `sha` field will be filled in automatically by the nightly workflow once your PR is merged.

3. **WG leads review and approve** the PR. They check:
   - Skills follow the AgentSkills.io standard
   - Skills pass `skillsaw lint`
   - The repo is actively maintained
   - The skills are useful to more than one team

4. **Once merged**, the nightly workflow resolves the SHA and your skills appear in the [catalog](https://redhat-global-engineering.github.io/ge-public-skills).

## How engineers install your plugin

```bash
claude plugin marketplace add redhat-global-engineering/ge-public-skills
/plugin install your-plugin-name@ge-public-skills
```

## Approval

WG leads are listed in CODEOWNERS as required reviewers on `registry.yaml`. One approval required to merge. All feedback and discussion happens on the PR.

## What belongs here vs. ge-common-skills

| Here (ge-public-skills) | ge-common-skills (internal GitLab) |
|---|---|
| Pointers to **public GitHub repos** | First-party, WG-maintained SKILL.md files |
| Any public skill repo that follows the standard | Cross-org SDLC plumbing with high pilot overlap |
| Plugin = whole repo, not individual skills | Individual skills committed and reviewed |
| Nightly CI resolves SHAs and lints | Stricter `skillsaw lint --strict` |

ge-common-skills auto-imports everything from this repo via its `registry.yaml` imports block.

## Questions

- **Slack:** `#wg-ge-agentic-sdlc`
- **WG repo:** [global-engineering/wg-agentic-sdlc](https://gitlab.cee.redhat.com/global-engineering/wg-agentic-sdlc)

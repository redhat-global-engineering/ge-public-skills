# Getting Started

## What is the Skills Registry?

The Red Hat Global Engineering Skills Registry is a curated marketplace of
Claude Code plugins for Red Hat engineering teams. Each plugin provides
AI-powered skills for software engineering workflows.

## Add the Marketplace

```bash
claude plugin marketplace add redhat-global-engineering/ge-public-skills
```

## Browse Plugins

Once the marketplace is added, use the `/plugin` command to see available plugins:

```bash
/plugin
```

## Install a Plugin

Install a specific plugin by name:

```bash
/plugin install <plugin-name>@ge-public-skills
```

After installation, the plugin's skills become available as slash commands.

## Test from a Branch

To test marketplace changes before they're merged:

```bash
claude plugin marketplace add redhat-global-engineering/ge-public-skills#branch-name
```

#!/usr/bin/env python3
"""Generate .claude-plugin/marketplace.json from skills/ directory."""
import json
import os
import sys

import yaml


def _parse_frontmatter(skill_md_path):
    """Extract YAML frontmatter from a SKILL.md file. Returns dict or None."""
    with open(skill_md_path) as f:
        content = f.read()
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def generate_marketplace(repo_root):
    """Build marketplace manifest dict from skills/ directory."""
    manifest = {
        "name": "ge-public-skills",
        "owner": "RedHatProductSecurity",
        "plugins": [],
    }

    skills_dir = os.path.join(repo_root, "skills")
    if not os.path.isdir(skills_dir):
        return manifest

    for entry in sorted(os.listdir(skills_dir)):
        skill_path = os.path.join(skills_dir, entry)
        if not os.path.isdir(skill_path):
            continue
        skill_md = os.path.join(skill_path, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue
        data = _parse_frontmatter(skill_md)
        if not data or not data.get("name") or not data.get("description"):
            continue

        manifest["plugins"].append({
            "name": data["name"],
            "source": f"./skills/{entry}",
            "description": data["description"],
            "version": str(data.get("version", "1.0.0")),
            "author": {"name": "Red Hat"},
        })

    return manifest


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = generate_marketplace(repo_root)
    out_dir = os.path.join(repo_root, ".claude-plugin")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "marketplace.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(f"Wrote {out_path} with {len(result['plugins'])} plugin(s)")


if __name__ == "__main__":
    main()

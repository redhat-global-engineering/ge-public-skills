#!/usr/bin/env python3
"""Linter for ge-public-skills repository.

Checks:
1. Every skills/<name>/ directory contains a SKILL.md
2. SKILL.md has valid YAML frontmatter with non-empty name and description
3. Frontmatter name matches the directory name
4. No duplicate skill names across sources (checked via manifest)
5. sync-manifest.yaml is valid with required fields and no duplicates

Future checks (not yet implemented):
- skillsaw lint --strict
- evals presence check
"""
import os
import sys

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


def _parse_frontmatter(skill_md_path):
    """Extract YAML frontmatter from a SKILL.md file.

    Returns (dict, error_string). On success error_string is None.
    """
    with open(skill_md_path) as f:
        content = f.read()
    if not content.startswith("---"):
        return None, f"{skill_md_path}: missing YAML frontmatter (must start with ---)"
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, f"{skill_md_path}: malformed YAML frontmatter (missing closing ---)"
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        return None, f"{skill_md_path}: invalid YAML in frontmatter: {e}"
    if not isinstance(data, dict):
        return None, f"{skill_md_path}: frontmatter is not a YAML mapping"
    return data, None


def lint_skill(repo_root, skill_name):
    """Lint a single skill directory.

    Returns a list of error strings. Empty list means the skill passed.
    """
    errors = []
    skill_path = os.path.join(repo_root, "skills", skill_name)
    if not os.path.isdir(skill_path):
        return [f"skills/{skill_name}: directory does not exist"]

    skill_md = os.path.join(skill_path, "SKILL.md")
    if not os.path.isfile(skill_md):
        return [f"skills/{skill_name}: missing SKILL.md"]

    data, err = _parse_frontmatter(skill_md)
    if err:
        return [err]

    name = data.get("name")
    if not name or (isinstance(name, str) and not name.strip()):
        errors.append(f"skills/{skill_name}/SKILL.md: frontmatter 'name' is empty or missing")

    desc = data.get("description")
    if not desc or (isinstance(desc, str) and not desc.strip()):
        errors.append(f"skills/{skill_name}/SKILL.md: frontmatter 'description' is empty or missing")

    if name and isinstance(name, str) and name.strip() != skill_name:
        errors.append(
            f"skills/{skill_name}/SKILL.md: frontmatter name '{name.strip()}' "
            f"does not match directory name '{skill_name}'"
        )

    return errors


def lint_skills_dir(repo_root):
    """Lint all skill directories under repo_root/skills/.

    Returns a list of error strings. Empty list means all checks passed.
    """
    errors = []
    skills_dir = os.path.join(repo_root, "skills")
    if not os.path.isdir(skills_dir):
        return errors

    for entry in sorted(os.listdir(skills_dir)):
        if not os.path.isdir(os.path.join(skills_dir, entry)):
            continue
        errors.extend(lint_skill(repo_root, entry))

    return errors


def lint_manifest(manifest_path):
    """Lint sync-manifest.yaml.

    Returns a list of error strings. Empty list means all checks passed.
    """
    errors = []
    try:
        with open(manifest_path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"{manifest_path}: failed to parse YAML: {e}"]
    except FileNotFoundError:
        return [f"{manifest_path}: file not found"]

    if not isinstance(data, dict) or "sources" not in data:
        return [f"{manifest_path}: must contain a 'sources' key"]

    sources = data["sources"]
    if not sources:
        return errors

    if not isinstance(sources, list):
        return [f"{manifest_path}: 'sources' must be a list"]

    seen_skill_names = {}

    for i, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"{manifest_path}: source {i} is not a mapping")
            continue

        if "repo" not in source:
            errors.append(f"{manifest_path}: source {i} missing required field 'repo'")
        if "ref" not in source:
            errors.append(f"{manifest_path}: source {i} missing required field 'ref'")

        skills = source.get("skills", [])
        if not isinstance(skills, list):
            errors.append(f"{manifest_path}: source {i} 'skills' must be a list")
            continue

        seen_paths = set()
        for j, skill in enumerate(skills):
            if not isinstance(skill, dict):
                errors.append(f"{manifest_path}: source {i} skill {j} is not a mapping")
                continue
            path = skill.get("path")
            if not path:
                errors.append(f"{manifest_path}: source {i} skill {j} missing required field 'path'")
                continue

            if path in seen_paths:
                errors.append(f"{manifest_path}: source {i} has duplicate path '{path}'")
            seen_paths.add(path)

            skill_name = os.path.basename(path.rstrip("/"))
            repo = source.get("repo", f"source {i}")
            if skill_name in seen_skill_names:
                prev_repo = seen_skill_names[skill_name]
                errors.append(
                    f"{manifest_path}: duplicate skill name '{skill_name}' "
                    f"in {repo} and {prev_repo}"
                )
            else:
                seen_skill_names[skill_name] = repo

    return errors


def main():
    repo_root = REPO_ROOT
    manifest_path = os.path.join(repo_root, "sync-manifest.yaml")

    if "--fetch-new" in sys.argv:
        from scripts.sync import fetch_new_skills
        fetch_new_skills(repo_root, manifest_path)

    errors = []
    errors.extend(lint_skills_dir(repo_root))
    if os.path.isfile(manifest_path):
        errors.extend(lint_manifest(manifest_path))
    for err in errors:
        print(f"ERROR: {err}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

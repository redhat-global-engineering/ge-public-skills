"""Custom lint checks for skill directories.

These checks run on top of the upstream skill-linter and
validate_registry.py checks from the skills-registry submodule.
They operate on a cloned repo directory containing skill files.
"""

import json
import shutil
import subprocess
from pathlib import Path

import yaml


def _parse_frontmatter(skill_md_path: Path) -> dict | None:
    """Extract YAML frontmatter from a SKILL.md file.

    Returns the parsed dict, or None if no valid frontmatter is found.
    """
    text = skill_md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None


def lint_skill_dir(skill_dir: Path) -> list[str]:
    """Lint a single skill directory. Returns a list of error strings."""
    errors = []
    skill_name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.exists():
        errors.append(f"{skill_name}: SKILL.md not found")
        return errors

    frontmatter = _parse_frontmatter(skill_md)
    if frontmatter is None:
        errors.append(f"{skill_name}: SKILL.md has no valid YAML frontmatter")
        return errors

    fm_name = frontmatter.get("name")
    fm_desc = frontmatter.get("description")

    if not fm_name or not str(fm_name).strip():
        errors.append(f"{skill_name}: frontmatter 'name' is missing or empty")
    if not fm_desc or not str(fm_desc).strip():
        errors.append(f"{skill_name}: frontmatter 'description' is missing or empty")

    if fm_name and str(fm_name).strip() and str(fm_name).strip() != skill_name:
        errors.append(
            f"{skill_name}: frontmatter name '{fm_name}' does not match "
            f"directory name '{skill_name}'"
        )

    return errors


def run_skillsaw(repo_root: Path) -> list[str]:
    """Run skillsaw lint on a repo root. Returns a list of error strings.

    Skips gracefully if skillsaw is not installed.
    """
    if not shutil.which("skillsaw"):
        return []

    try:
        result = subprocess.run(
            ["skillsaw", "lint", "--strict", "--format", "json", str(repo_root)],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return ["skillsaw: timed out after 60 seconds"]

    if result.returncode == 0:
        return []

    errors = []
    try:
        data = json.loads(result.stdout)
        for v in data.get("violations", []):
            severity = v.get("severity", "error")
            rule = v.get("rule_id", "unknown")
            msg = v.get("message", "")
            path = v.get("file_path", "")
            prefix = f"{path}: " if path else ""
            errors.append(f"skillsaw [{rule}] {severity}: {prefix}{msg}")
    except (json.JSONDecodeError, KeyError):
        errors.append(f"skillsaw: non-zero exit ({result.returncode})")

    return errors

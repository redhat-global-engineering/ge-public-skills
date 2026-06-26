"""Resolve latest commit SHAs for registry plugins and update if linting passes.

Usage:
    python scripts/update_digests.py [--registry registry.yaml] [--dry-run]
"""

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

from scripts.custom_linters import lint_skill_dir

GIT_TIMEOUT = 120


def load_registry(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def save_registry(path: Path, registry: dict) -> None:
    with open(path, "w") as f:
        yaml.dump(registry, f, default_flow_style=False, sort_keys=False)


def _run_gh_api(endpoint: str) -> str:
    """Call gh api and return stdout. Raises RuntimeError on failure."""
    result = subprocess.run(
        ["gh", "api", endpoint, "--jq", ".sha"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh api failed: {result.stderr.strip()}")
    sha = result.stdout.strip()
    if not sha:
        raise RuntimeError("gh api returned empty SHA")
    return sha


def resolve_latest_sha(repo: str, ref: str) -> str | None:
    """Resolve the latest commit SHA for a repo's branch. Returns None on failure."""
    try:
        return _run_gh_api(f"repos/{repo}/commits/{ref}")
    except (RuntimeError, subprocess.TimeoutExpired):
        return None


def find_stale_plugins(registry: dict) -> list[tuple[dict, str]]:
    """Find plugins whose pinned SHA differs from the latest.

    Returns list of (plugin_dict, new_sha) tuples.
    """
    stale = []
    for plugin in registry.get("plugins", []):
        source = plugin.get("source", {})
        if source.get("type") != "github":
            continue
        repo = source.get("repo")
        ref = source.get("ref", "main")
        current_sha = source.get("sha")
        if not repo:
            continue
        latest_sha = resolve_latest_sha(repo, ref)
        if latest_sha is None:
            continue
        if latest_sha != current_sha:
            stale.append((plugin, latest_sha))
    return stale


def clone_at_sha(repo: str, sha: str, dest: Path) -> Path:
    """Shallow-clone a GitHub repo and checkout a specific SHA."""
    clone_url = f"https://github.com/{repo}.git"
    result = subprocess.run(
        ["git", "clone", "--depth", "1", clone_url, str(dest)],
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT,
    )
    if result.returncode != 0:
        raise RuntimeError(f"clone failed for {clone_url}: {result.stderr.strip()}")
    # Fetch the specific SHA
    fetch = subprocess.run(
        ["git", "-C", str(dest), "fetch", "--depth", "1", "origin", sha],
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT,
    )
    if fetch.returncode != 0:
        raise RuntimeError(f"fetch {sha} failed: {fetch.stderr.strip()}")
    checkout = subprocess.run(
        ["git", "-C", str(dest), "checkout", "--detach", sha],
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT,
    )
    if checkout.returncode != 0:
        raise RuntimeError(f"checkout {sha} failed: {checkout.stderr.strip()}")
    return dest


def run_custom_lints(repo_root: Path, skills_dir: str = "skills") -> list[str]:
    """Run custom lint checks on all skill directories in a cloned repo."""
    skills_path = repo_root / skills_dir
    if not skills_path.is_dir():
        return [f"skills directory '{skills_dir}' not found in repo"]
    errors = []
    for entry in sorted(skills_path.iterdir()):
        if entry.is_dir():
            errors.extend(lint_skill_dir(entry))
    return errors


def open_or_update_issue(
    plugin_name: str, repo: str, sha: str, errors: list[str]
) -> None:
    """Create or update a GitHub issue for a failed digest update."""
    title = f"Digest update failed: {plugin_name}"
    label = "digest-update-failure"
    error_text = "\n".join(f"- {e}" for e in errors)
    body = (
        f"Linting failed for **{plugin_name}** at commit `{sha}` "
        f"in `{repo}`.\n\n"
        f"## Errors\n\n{error_text}\n\n"
        f"The pinned SHA in `registry.yaml` was **not** updated."
    )

    # Ensure label exists
    subprocess.run(
        [
            "gh", "label", "create", label, "--color", "d73a4a",
            "--description", "Nightly digest update failed lint", "--force",
        ],
        capture_output=True,
        text=True,
    )

    # Search for existing open issue
    search = subprocess.run(
        [
            "gh", "issue", "list", "--label", label, "--state", "open",
            "--search", f"in:title {plugin_name}",
            "--json", "number", "--jq", ".[0].number",
        ],
        capture_output=True,
        text=True,
    )
    existing = search.stdout.strip()

    if existing:
        subprocess.run(
            ["gh", "issue", "comment", existing, "--body", body],
            capture_output=True,
            text=True,
        )
    else:
        subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body,
             "--label", label],
            capture_output=True,
            text=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default="registry.yaml")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would change without modifying files",
    )
    args = parser.parse_args()

    import tempfile

    registry_path = Path(args.registry)
    registry = load_registry(registry_path)
    stale = find_stale_plugins(registry)

    if not stale:
        print("All plugins are up to date.")
        return

    updated = 0
    for plugin, new_sha in stale:
        name = plugin["name"]
        source = plugin["source"]
        repo = source["repo"]
        skills_dir = plugin.get("skills_dir", "skills")

        print(
            f"Checking {name}: "
            f"{source.get('sha', 'none')[:12]} -> {new_sha[:12]}"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                clone_dest = Path(tmpdir) / name
                clone_at_sha(repo, new_sha, clone_dest)
                errors = run_custom_lints(clone_dest, skills_dir=skills_dir)
            except RuntimeError as e:
                errors = [str(e)]

        if errors:
            print(f"  FAIL: {len(errors)} error(s)")
            for e in errors:
                print(f"    - {e}")
            if not args.dry_run:
                open_or_update_issue(name, repo, new_sha, errors)
        else:
            print("  OK: updating SHA")
            if not args.dry_run:
                source["sha"] = new_sha
                updated += 1

    if updated > 0 and not args.dry_run:
        save_registry(registry_path, registry)
        print(f"Updated {updated} plugin(s) in {registry_path}")


if __name__ == "__main__":
    main()

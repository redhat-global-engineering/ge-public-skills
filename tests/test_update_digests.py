"""Tests for digest update logic."""

import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from scripts.update_digests import (
    load_registry,
    save_registry,
    resolve_latest_sha,
    find_stale_plugins,
    clone_at_sha,
    run_custom_lints,
)


@pytest.fixture
def registry_path(tmp_path):
    reg = tmp_path / "registry.yaml"
    reg.write_text(yaml.dump({
        "name": "test-registry",
        "owner": {"name": "Test"},
        "categories": {},
        "plugins": [
            {
                "name": "plugin-a",
                "description": "A plugin",
                "version": "1.0.0",
                "source": {
                    "type": "github",
                    "repo": "org/repo-a",
                    "ref": "main",
                    "sha": "a" * 40,
                },
            },
            {
                "name": "plugin-b",
                "description": "B plugin",
                "version": "1.0.0",
                "source": {
                    "type": "github",
                    "repo": "org/repo-b",
                    "ref": "main",
                    "sha": "b" * 40,
                },
            },
        ],
    }))
    return reg


class TestLoadSaveRegistry:
    def test_load(self, registry_path):
        reg = load_registry(registry_path)
        assert reg["name"] == "test-registry"
        assert len(reg["plugins"]) == 2

    def test_save_preserves_structure(self, registry_path):
        reg = load_registry(registry_path)
        reg["plugins"][0]["source"]["sha"] = "c" * 40
        save_registry(registry_path, reg)
        reloaded = load_registry(registry_path)
        assert reloaded["plugins"][0]["source"]["sha"] == "c" * 40
        assert reloaded["plugins"][1]["source"]["sha"] == "b" * 40


class TestResolveLatestSha:
    @patch("scripts.update_digests._run_gh_api")
    def test_resolves_sha(self, mock_gh):
        mock_gh.return_value = "d" * 40
        sha = resolve_latest_sha("org/repo", "main")
        assert sha == "d" * 40
        mock_gh.assert_called_once()

    @patch("scripts.update_digests._run_gh_api")
    def test_returns_none_on_failure(self, mock_gh):
        mock_gh.side_effect = RuntimeError("API error")
        sha = resolve_latest_sha("org/repo", "main")
        assert sha is None


class TestFindStalePlugins:
    @patch("scripts.update_digests.resolve_latest_sha")
    def test_finds_stale(self, mock_resolve, registry_path):
        mock_resolve.side_effect = lambda repo, ref: "new_sha_" + repo[-1] + "0" * 33
        reg = load_registry(registry_path)
        stale = find_stale_plugins(reg)
        assert len(stale) == 2
        assert stale[0][0]["name"] == "plugin-a"

    @patch("scripts.update_digests.resolve_latest_sha")
    def test_skips_current(self, mock_resolve, registry_path):
        reg = load_registry(registry_path)
        current_sha = reg["plugins"][0]["source"]["sha"]
        mock_resolve.side_effect = lambda repo, ref: current_sha if "repo-a" in repo else "x" * 40
        stale = find_stale_plugins(reg)
        assert len(stale) == 1
        assert stale[0][0]["name"] == "plugin-b"

    @patch("scripts.update_digests.resolve_latest_sha")
    def test_skips_resolve_failure(self, mock_resolve, registry_path):
        mock_resolve.return_value = None
        reg = load_registry(registry_path)
        stale = find_stale_plugins(reg)
        assert len(stale) == 0


class TestCloneAtSha:
    @patch("subprocess.run")
    def test_clone_success(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        result = clone_at_sha("org/repo", "a" * 40, tmp_path / "clone")
        assert result == tmp_path / "clone"

    @patch("subprocess.run")
    def test_clone_failure(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=1, stderr="fail")
        with pytest.raises(RuntimeError, match="clone failed"):
            clone_at_sha("org/repo", "a" * 40, tmp_path / "clone")


class TestRunCustomLints:
    def test_valid_skill(self, tmp_path):
        skill = tmp_path / "my-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(textwrap.dedent("""\
            ---
            name: my-skill
            description: A skill
            ---
            Content.
        """))
        errors = run_custom_lints(tmp_path, skills_dir=".")
        assert not errors

    def test_invalid_skill(self, tmp_path):
        skill = tmp_path / "bad-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("No frontmatter")
        errors = run_custom_lints(tmp_path, skills_dir=".")
        assert len(errors) > 0

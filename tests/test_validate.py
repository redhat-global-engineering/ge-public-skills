"""Tests for validate.py custom checks."""

from scripts.validate import check_sha_pinning


class TestCheckShaPinning:
    def test_missing_sha_is_error(self):
        registry = {
            "plugins": [
                {
                    "name": "no-sha-plugin",
                    "source": {"type": "github", "repo": "org/repo", "ref": "main"},
                }
            ]
        }
        errors = check_sha_pinning(registry)
        assert len(errors) == 1
        assert "no-sha-plugin" in errors[0]
        assert "sha" in errors[0]

    def test_present_sha_passes(self):
        registry = {
            "plugins": [
                {
                    "name": "pinned-plugin",
                    "source": {
                        "type": "github",
                        "repo": "org/repo",
                        "ref": "v1.0",
                        "sha": "a" * 40,
                    },
                }
            ]
        }
        errors = check_sha_pinning(registry)
        assert errors == []

    def test_git_subdir_also_requires_sha(self):
        registry = {
            "plugins": [
                {
                    "name": "subdir-plugin",
                    "source": {"type": "git-subdir", "repo": "org/repo"},
                }
            ]
        }
        errors = check_sha_pinning(registry)
        assert len(errors) == 1

    def test_non_git_source_skipped(self):
        registry = {
            "plugins": [
                {
                    "name": "npm-plugin",
                    "source": {"type": "npm", "repo": "some-package"},
                }
            ]
        }
        errors = check_sha_pinning(registry)
        assert errors == []

    def test_empty_registry(self):
        errors = check_sha_pinning({"plugins": []})
        assert errors == []

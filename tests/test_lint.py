"""tests/test_lint.py"""
import os
import tempfile
from unittest.mock import patch
import pytest
from scripts.lint import lint_skills_dir, lint_manifest, main


def _write_skill(base, name, frontmatter="---\nname: {name}\ndescription: A skill\n---\n# Content\n"):
    """Helper to create a skill directory with SKILL.md."""
    skill_dir = os.path.join(base, "skills", name)
    os.makedirs(skill_dir, exist_ok=True)
    with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
        f.write(frontmatter.format(name=name))
    return skill_dir


class TestSkillMdPresence:
    def test_missing_skill_md(self, tmp_path):
        skill_dir = tmp_path / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "README.md").write_text("not a skill")
        errors = lint_skills_dir(str(tmp_path))
        assert any("SKILL.md" in e for e in errors)

    def test_valid_skill_md(self, tmp_path):
        _write_skill(str(tmp_path), "my-skill")
        errors = lint_skills_dir(str(tmp_path))
        assert not any("SKILL.md" in e for e in errors)


class TestFrontmatterValidation:
    def test_missing_frontmatter(self, tmp_path):
        skill_dir = tmp_path / "skills" / "bad-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# No frontmatter here\n")
        errors = lint_skills_dir(str(tmp_path))
        assert any("frontmatter" in e.lower() for e in errors)

    def test_empty_name(self, tmp_path):
        _write_skill(str(tmp_path), "bad-skill",
                     frontmatter="---\nname: \ndescription: A skill\n---\n")
        errors = lint_skills_dir(str(tmp_path))
        assert any("name" in e.lower() for e in errors)

    def test_empty_description(self, tmp_path):
        _write_skill(str(tmp_path), "bad-skill",
                     frontmatter="---\nname: bad-skill\ndescription: \n---\n")
        errors = lint_skills_dir(str(tmp_path))
        assert any("description" in e.lower() for e in errors)


class TestNameDirectoryMatch:
    def test_name_mismatch(self, tmp_path):
        _write_skill(str(tmp_path), "my-skill",
                     frontmatter="---\nname: wrong-name\ndescription: A skill\n---\n")
        errors = lint_skills_dir(str(tmp_path))
        assert any("match" in e.lower() for e in errors)

    def test_name_matches(self, tmp_path):
        _write_skill(str(tmp_path), "my-skill")
        errors = lint_skills_dir(str(tmp_path))
        assert not errors


class TestDuplicateSkillNames:
    def test_no_duplicates_possible(self, tmp_path):
        """Directory names are inherently unique in a filesystem,
        so this check validates the skills/ directory itself.
        Duplicate detection matters when validating the manifest
        (two sources declaring skills that would land at the same path)."""
        _write_skill(str(tmp_path), "skill-a")
        _write_skill(str(tmp_path), "skill-b")
        errors = lint_skills_dir(str(tmp_path))
        assert not errors


class TestManifestValidation:
    def test_valid_manifest(self, tmp_path):
        manifest = tmp_path / "sync-manifest.yaml"
        manifest.write_text(
            "sources:\n"
            "  - repo: https://github.com/org/repo\n"
            "    ref: main\n"
            "    skills:\n"
            "      - path: skills/my-skill\n"
        )
        errors = lint_manifest(str(manifest))
        assert not errors

    def test_missing_repo(self, tmp_path):
        manifest = tmp_path / "sync-manifest.yaml"
        manifest.write_text(
            "sources:\n"
            "  - ref: main\n"
            "    skills:\n"
            "      - path: skills/my-skill\n"
        )
        errors = lint_manifest(str(manifest))
        assert any("repo" in e.lower() for e in errors)

    def test_missing_ref(self, tmp_path):
        manifest = tmp_path / "sync-manifest.yaml"
        manifest.write_text(
            "sources:\n"
            "  - repo: https://github.com/org/repo\n"
            "    skills:\n"
            "      - path: skills/my-skill\n"
        )
        errors = lint_manifest(str(manifest))
        assert any("ref" in e.lower() for e in errors)

    def test_missing_path_in_skill(self, tmp_path):
        manifest = tmp_path / "sync-manifest.yaml"
        manifest.write_text(
            "sources:\n"
            "  - repo: https://github.com/org/repo\n"
            "    ref: main\n"
            "    skills:\n"
            "      - name: bad\n"
        )
        errors = lint_manifest(str(manifest))
        assert any("path" in e.lower() for e in errors)

    def test_duplicate_skill_paths(self, tmp_path):
        manifest = tmp_path / "sync-manifest.yaml"
        manifest.write_text(
            "sources:\n"
            "  - repo: https://github.com/org/repo\n"
            "    ref: main\n"
            "    skills:\n"
            "      - path: skills/my-skill\n"
            "      - path: skills/my-skill\n"
        )
        errors = lint_manifest(str(manifest))
        assert any("duplicate" in e.lower() for e in errors)

    def test_duplicate_skill_names_across_sources(self, tmp_path):
        manifest = tmp_path / "sync-manifest.yaml"
        manifest.write_text(
            "sources:\n"
            "  - repo: https://github.com/org/repo-a\n"
            "    ref: main\n"
            "    skills:\n"
            "      - path: a/skills/same-name\n"
            "  - repo: https://github.com/org/repo-b\n"
            "    ref: main\n"
            "    skills:\n"
            "      - path: b/skills/same-name\n"
        )
        errors = lint_manifest(str(manifest))
        assert any("duplicate" in e.lower() for e in errors)

    def test_empty_sources(self, tmp_path):
        manifest = tmp_path / "sync-manifest.yaml"
        manifest.write_text("sources: []\n")
        errors = lint_manifest(str(manifest))
        assert not errors

    def test_invalid_yaml(self, tmp_path):
        manifest = tmp_path / "sync-manifest.yaml"
        manifest.write_text(": invalid: yaml: [")
        errors = lint_manifest(str(manifest))
        assert any("yaml" in e.lower() or "parse" in e.lower() for e in errors)


class TestFetchNewFlag:
    def test_fetch_new_calls_fetch_new_skills(self, tmp_path):
        """--fetch-new causes lint to fetch new manifest skills before linting."""
        manifest = tmp_path / "sync-manifest.yaml"
        manifest.write_text("sources: []\n")
        (tmp_path / "skills").mkdir()

        with patch("scripts.sync.fetch_new_skills", return_value=[]) as mock_fetch:
            with patch("sys.argv", ["lint.py", "--fetch-new"]):
                with patch("scripts.lint.REPO_ROOT", str(tmp_path)):
                    main()
            mock_fetch.assert_called_once()

    def test_no_fetch_without_flag(self, tmp_path):
        """Without --fetch-new, fetch_new_skills is not called."""
        manifest = tmp_path / "sync-manifest.yaml"
        manifest.write_text("sources: []\n")
        (tmp_path / "skills").mkdir()

        with patch("scripts.sync.fetch_new_skills", return_value=[]) as mock_fetch:
            with patch("sys.argv", ["lint.py"]):
                with patch("scripts.lint.REPO_ROOT", str(tmp_path)):
                    main()
            mock_fetch.assert_not_called()

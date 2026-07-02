"""Tests for custom skill linting checks."""

import json
import textwrap
from unittest.mock import patch, MagicMock

import pytest

from scripts.custom_linters import lint_skill_dir, run_skillsaw


@pytest.fixture
def skill_dir(tmp_path):
    """Create a valid skill directory with SKILL.md."""
    skill = tmp_path / "my-skill"
    skill.mkdir()
    skill_md = skill / "SKILL.md"
    skill_md.write_text(textwrap.dedent("""\
        ---
        name: my-skill
        description: A test skill
        ---
        Skill content here.
    """))
    return skill


class TestSkillMdPresence:
    def test_missing_skill_md(self, tmp_path):
        skill = tmp_path / "no-skill"
        skill.mkdir()
        errors = lint_skill_dir(skill)
        assert any("SKILL.md" in e for e in errors)

    def test_present_skill_md(self, skill_dir):
        errors = lint_skill_dir(skill_dir)
        assert not errors


class TestFrontmatterValidation:
    def test_no_frontmatter(self, tmp_path):
        skill = tmp_path / "bad-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("No frontmatter here.")
        errors = lint_skill_dir(skill)
        assert any("frontmatter" in e.lower() for e in errors)

    def test_empty_name(self, tmp_path):
        skill = tmp_path / "bad-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(textwrap.dedent("""\
            ---
            name: ""
            description: Something
            ---
        """))
        errors = lint_skill_dir(skill)
        assert any("name" in e.lower() for e in errors)

    def test_empty_description(self, tmp_path):
        skill = tmp_path / "bad-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(textwrap.dedent("""\
            ---
            name: bad-skill
            description: ""
            ---
        """))
        errors = lint_skill_dir(skill)
        assert any("description" in e.lower() for e in errors)

    def test_missing_name_field(self, tmp_path):
        skill = tmp_path / "bad-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(textwrap.dedent("""\
            ---
            description: Something
            ---
        """))
        errors = lint_skill_dir(skill)
        assert any("name" in e.lower() for e in errors)

    def test_missing_description_field(self, tmp_path):
        skill = tmp_path / "bad-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(textwrap.dedent("""\
            ---
            name: bad-skill
            ---
        """))
        errors = lint_skill_dir(skill)
        assert any("description" in e.lower() for e in errors)


class TestNameDirectoryMatch:
    def test_name_mismatch(self, tmp_path):
        skill = tmp_path / "actual-name"
        skill.mkdir()
        (skill / "SKILL.md").write_text(textwrap.dedent("""\
            ---
            name: wrong-name
            description: A skill
            ---
        """))
        errors = lint_skill_dir(skill)
        assert any("match" in e.lower() or "mismatch" in e.lower() for e in errors)

    def test_name_matches(self, skill_dir):
        errors = lint_skill_dir(skill_dir)
        assert not errors


class TestRunSkillsaw:
    @patch("scripts.custom_linters.shutil.which", return_value=None)
    def test_skips_when_not_installed(self, mock_which, tmp_path):
        errors = run_skillsaw(tmp_path)
        assert errors == []

    @patch("scripts.custom_linters.subprocess.run")
    @patch("scripts.custom_linters.shutil.which", return_value="/usr/bin/skillsaw")
    def test_clean_repo_returns_no_errors(self, mock_which, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        errors = run_skillsaw(tmp_path)
        assert errors == []

    @patch("scripts.custom_linters.subprocess.run")
    @patch("scripts.custom_linters.shutil.which", return_value="/usr/bin/skillsaw")
    def test_violations_returned_as_errors(self, mock_which, mock_run, tmp_path):
        output = json.dumps({
            "violations": [
                {
                    "rule_id": "agentskill-valid",
                    "severity": "error",
                    "message": "Missing required 'description' field",
                    "file_path": "skills/bad/SKILL.md",
                },
            ],
        })
        mock_run.return_value = MagicMock(returncode=1, stdout=output, stderr="")
        errors = run_skillsaw(tmp_path)
        assert len(errors) == 1
        assert "agentskill-valid" in errors[0]
        assert "Missing required" in errors[0]
        assert "skills/bad/SKILL.md" in errors[0]

    @patch("scripts.custom_linters.subprocess.run")
    @patch("scripts.custom_linters.shutil.which", return_value="/usr/bin/skillsaw")
    def test_timeout_returns_error(self, mock_which, mock_run, tmp_path):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="skillsaw", timeout=60)
        errors = run_skillsaw(tmp_path)
        assert len(errors) == 1
        assert "timed out" in errors[0]

    @patch("scripts.custom_linters.subprocess.run")
    @patch("scripts.custom_linters.shutil.which", return_value="/usr/bin/skillsaw")
    def test_invalid_json_returns_error(self, mock_which, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=1, stdout="not json", stderr="")
        errors = run_skillsaw(tmp_path)
        assert len(errors) == 1
        assert "non-zero exit" in errors[0]

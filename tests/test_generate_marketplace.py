"""tests/test_generate_marketplace.py"""
import json
import os
import pytest
from scripts.generate_marketplace import generate_marketplace


def _write_skill(base, name, frontmatter):
    skill_dir = os.path.join(base, "skills", name)
    os.makedirs(skill_dir, exist_ok=True)
    with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
        f.write(frontmatter)


class TestGenerateMarketplace:
    def test_empty_skills_dir(self, tmp_path):
        (tmp_path / "skills").mkdir()
        result = generate_marketplace(str(tmp_path))
        assert result["name"] == "ge-public-skills"
        assert result["plugins"] == []

    def test_no_skills_dir(self, tmp_path):
        result = generate_marketplace(str(tmp_path))
        assert result["plugins"] == []

    def test_single_skill(self, tmp_path):
        _write_skill(str(tmp_path), "my-skill",
                     "---\nname: my-skill\ndescription: Use when testing\n---\n# Content\n")
        result = generate_marketplace(str(tmp_path))
        assert len(result["plugins"]) == 1
        plugin = result["plugins"][0]
        assert plugin["name"] == "my-skill"
        assert plugin["source"] == "./skills/my-skill"
        assert plugin["description"] == "Use when testing"
        assert plugin["version"] == "1.0.0"

    def test_multiple_skills_sorted(self, tmp_path):
        _write_skill(str(tmp_path), "z-skill",
                     "---\nname: z-skill\ndescription: Zebra\n---\n")
        _write_skill(str(tmp_path), "a-skill",
                     "---\nname: a-skill\ndescription: Alpha\n---\n")
        result = generate_marketplace(str(tmp_path))
        names = [p["name"] for p in result["plugins"]]
        assert names == ["a-skill", "z-skill"]

    def test_version_from_frontmatter(self, tmp_path):
        _write_skill(str(tmp_path), "versioned",
                     "---\nname: versioned\ndescription: Has version\nversion: 2.1.0\n---\n")
        result = generate_marketplace(str(tmp_path))
        assert result["plugins"][0]["version"] == "2.1.0"

    def test_skips_invalid_skill(self, tmp_path):
        """Skills without valid frontmatter are skipped (lint catches them separately)."""
        skill_dir = tmp_path / "skills" / "broken"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# No frontmatter\n")
        _write_skill(str(tmp_path), "good-skill",
                     "---\nname: good-skill\ndescription: Works\n---\n")
        result = generate_marketplace(str(tmp_path))
        assert len(result["plugins"]) == 1
        assert result["plugins"][0]["name"] == "good-skill"

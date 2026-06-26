"""tests/test_sync.py"""
from scripts.sync import (
    parse_manifest,
    extract_skill_name,
    mirror_directory,
    detect_changes,
    find_orphaned_skills,
    find_new_manifest_skills,
)


class TestParseManifest:
    def test_empty_sources(self, tmp_path):
        manifest = tmp_path / "sync-manifest.yaml"
        manifest.write_text("sources: []\n")
        result = parse_manifest(str(manifest))
        assert result == []

    def test_parses_sources(self, tmp_path):
        manifest = tmp_path / "sync-manifest.yaml"
        manifest.write_text(
            "sources:\n"
            "  - repo: https://github.com/org/repo\n"
            "    ref: main\n"
            "    skills:\n"
            "      - path: module/skills/my-skill\n"
        )
        result = parse_manifest(str(manifest))
        assert len(result) == 1
        assert result[0]["repo"] == "https://github.com/org/repo"
        assert result[0]["ref"] == "main"
        assert len(result[0]["skills"]) == 1


class TestExtractSkillName:
    def test_simple_path(self):
        assert extract_skill_name("skills/my-skill") == "my-skill"

    def test_nested_path(self):
        assert extract_skill_name("module/skills/my-skill") == "my-skill"

    def test_trailing_slash(self):
        assert extract_skill_name("skills/my-skill/") == "my-skill"


class TestMirrorDirectory:
    def test_copies_files(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "SKILL.md").write_text("# Skill")
        mirror_directory(str(src), str(dst))
        assert (dst / "SKILL.md").read_text() == "# Skill"

    def test_copies_subdirectories(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        (src / "references").mkdir(parents=True)
        (src / "references" / "doc.md").write_text("# Doc")
        mirror_directory(str(src), str(dst))
        assert (dst / "references" / "doc.md").read_text() == "# Doc"

    def test_removes_old_files(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        (dst / "old-file.md").write_text("stale")
        (src / "SKILL.md").write_text("# Skill")
        mirror_directory(str(src), str(dst))
        assert not (dst / "old-file.md").exists()
        assert (dst / "SKILL.md").exists()

    def test_overwrites_changed_content(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        (src / "SKILL.md").write_text("# Updated")
        (dst / "SKILL.md").write_text("# Original")
        mirror_directory(str(src), str(dst))
        assert (dst / "SKILL.md").read_text() == "# Updated"


class TestDetectChanges:
    def test_new_skill(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "SKILL.md").write_text("# Skill")
        assert detect_changes(str(src), str(dst)) is True

    def test_no_changes(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        (src / "SKILL.md").write_text("# Skill")
        (dst / "SKILL.md").write_text("# Skill")
        assert detect_changes(str(src), str(dst)) is False

    def test_content_changed(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        (src / "SKILL.md").write_text("# Updated")
        (dst / "SKILL.md").write_text("# Original")
        assert detect_changes(str(src), str(dst)) is True

    def test_file_removed_upstream(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        (src / "SKILL.md").write_text("# Skill")
        (dst / "SKILL.md").write_text("# Skill")
        (dst / "old.md").write_text("stale")
        assert detect_changes(str(src), str(dst)) is True


class TestFindOrphanedSkills:
    def test_no_orphans(self, tmp_path):
        """All local skills have manifest entries."""
        skills_dir = tmp_path / "skills"
        (skills_dir / "skill-a").mkdir(parents=True)
        (skills_dir / "skill-a" / "SKILL.md").write_text("# A")
        sources = [
            {"repo": "https://github.com/org/repo", "ref": "main",
             "skills": [{"path": "skills/skill-a"}]},
        ]
        result = find_orphaned_skills(str(tmp_path), sources)
        assert result == []

    def test_orphan_detected(self, tmp_path):
        """A local skill with no manifest entry is orphaned."""
        skills_dir = tmp_path / "skills"
        (skills_dir / "skill-a").mkdir(parents=True)
        (skills_dir / "skill-a" / "SKILL.md").write_text("# A")
        (skills_dir / "skill-b").mkdir(parents=True)
        (skills_dir / "skill-b" / "SKILL.md").write_text("# B")
        sources = [
            {"repo": "https://github.com/org/repo", "ref": "main",
             "skills": [{"path": "skills/skill-a"}]},
        ]
        result = find_orphaned_skills(str(tmp_path), sources)
        assert result == ["skill-b"]

    def test_empty_manifest(self, tmp_path):
        """All skills are orphaned when manifest is empty."""
        skills_dir = tmp_path / "skills"
        (skills_dir / "skill-a").mkdir(parents=True)
        (skills_dir / "skill-a" / "SKILL.md").write_text("# A")
        (skills_dir / "skill-b").mkdir(parents=True)
        (skills_dir / "skill-b" / "SKILL.md").write_text("# B")
        result = find_orphaned_skills(str(tmp_path), [])
        assert result == ["skill-a", "skill-b"]

    def test_no_skills_dir(self, tmp_path):
        """No skills directory means no orphans."""
        result = find_orphaned_skills(str(tmp_path), [])
        assert result == []

    def test_ignores_non_directories(self, tmp_path):
        """Files in skills/ are not treated as skill directories."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "README.md").write_text("# Skills")
        result = find_orphaned_skills(str(tmp_path), [])
        assert result == []


class TestFindNewManifestSkills:
    def test_no_new_skills(self, tmp_path):
        """All manifest skills already exist on disk."""
        skills_dir = tmp_path / "skills"
        (skills_dir / "skill-a").mkdir(parents=True)
        (skills_dir / "skill-a" / "SKILL.md").write_text("# A")
        sources = [
            {"repo": "https://github.com/org/repo", "ref": "main",
             "skills": [{"path": "skills/skill-a"}]},
        ]
        result = find_new_manifest_skills(str(tmp_path), sources)
        assert result == []

    def test_new_skill_detected(self, tmp_path):
        """A manifest entry with no local directory is new."""
        skills_dir = tmp_path / "skills"
        (skills_dir / "skill-a").mkdir(parents=True)
        (skills_dir / "skill-a" / "SKILL.md").write_text("# A")
        sources = [
            {"repo": "https://github.com/org/repo", "ref": "main",
             "skills": [
                 {"path": "skills/skill-a"},
                 {"path": "skills/skill-b"},
             ]},
        ]
        result = find_new_manifest_skills(str(tmp_path), sources)
        assert len(result) == 1
        assert result[0]["name"] == "skill-b"
        assert result[0]["repo"] == "https://github.com/org/repo"
        assert result[0]["ref"] == "main"
        assert result[0]["path"] == "skills/skill-b"

    def test_all_new_when_no_skills_dir(self, tmp_path):
        """When skills/ doesn't exist, all manifest entries are new."""
        sources = [
            {"repo": "https://github.com/org/repo", "ref": "main",
             "skills": [{"path": "skills/skill-a"}]},
        ]
        result = find_new_manifest_skills(str(tmp_path), sources)
        assert len(result) == 1
        assert result[0]["name"] == "skill-a"

    def test_empty_manifest(self, tmp_path):
        """Empty manifest means no new skills."""
        result = find_new_manifest_skills(str(tmp_path), [])
        assert result == []

    def test_multiple_sources(self, tmp_path):
        """New skills detected across multiple sources."""
        (tmp_path / "skills").mkdir()
        sources = [
            {"repo": "https://github.com/org/repo-a", "ref": "main",
             "skills": [{"path": "skills/skill-a"}]},
            {"repo": "https://github.com/org/repo-b", "ref": "dev",
             "skills": [{"path": "skills/skill-b"}]},
        ]
        result = find_new_manifest_skills(str(tmp_path), sources)
        assert len(result) == 2
        assert result[0]["repo"] == "https://github.com/org/repo-a"
        assert result[1]["repo"] == "https://github.com/org/repo-b"
        assert result[1]["ref"] == "dev"

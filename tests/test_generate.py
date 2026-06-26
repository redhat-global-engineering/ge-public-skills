"""Tests for the generation wrapper."""

import json

import pytest
import yaml

from scripts.generate import (
    generate_marketplace,
    generate_site_config,
)


@pytest.fixture
def registry_path(tmp_path):
    reg = tmp_path / "registry.yaml"
    reg.write_text(yaml.dump({
        "name": "ge-public-skills",
        "owner": {"name": "Red Hat Global Engineering"},
        "description": "Test registry",
        "categories": {
            "security": {
                "name": "Security",
                "description": "Security skills",
            },
        },
        "plugins": [
            {
                "name": "test-plugin",
                "description": "A test plugin",
                "version": "1.0.0",
                "category": "security",
                "source": {
                    "type": "github",
                    "repo": "org/test-plugin",
                    "ref": "main",
                    "sha": "a" * 40,
                },
                "skills": [
                    {
                        "name": "test-skill",
                        "description": "A test skill",
                    },
                ],
            },
        ],
    }))
    return reg


class TestGenerateMarketplace:
    def test_produces_valid_json(self, registry_path, tmp_path):
        output = tmp_path / ".claude-plugin" / "marketplace.json"
        generate_marketplace(registry_path, output)
        assert output.exists()
        data = json.loads(output.read_text())
        assert data["name"] == "ge-public-skills"
        assert len(data["plugins"]) == 1
        assert data["plugins"][0]["name"] == "test-plugin"

    def test_empty_registry(self, tmp_path):
        reg = tmp_path / "registry.yaml"
        reg.write_text(yaml.dump({
            "name": "ge-public-skills",
            "owner": {"name": "Test"},
            "categories": {},
            "plugins": [],
        }))
        output = tmp_path / ".claude-plugin" / "marketplace.json"
        generate_marketplace(reg, output)
        data = json.loads(output.read_text())
        assert data["plugins"] == []


class TestSiteConfig:
    def test_config_has_red_hat_branding(self):
        config = generate_site_config()
        assert "Red Hat" in config
        assert "ge-public-skills" in config
        assert "red" in config.lower()

    def test_mkdocs_config_is_valid_yaml(self):
        config = generate_site_config()
        # Strip !!python/name: tags that MkDocs uses but PyYAML safe_load
        # cannot resolve without the material package installed.
        sanitized = config.replace("!!python/name:", "# python/name:")
        parsed = yaml.safe_load(sanitized)
        assert parsed["site_name"] is not None
        assert "material" in str(parsed.get("theme", {}).get("name", ""))

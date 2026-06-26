"""Generate marketplace.json, catalog.md, and MkDocs site.

Wraps submodule generation functions with our Red Hat branding config.

Usage:
    python scripts/generate.py marketplace [--registry registry.yaml]
    python scripts/generate.py site [--registry registry.yaml]
    python scripts/generate.py all [--registry registry.yaml]
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import yaml

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_SUBMODULE = _REPO_ROOT / "skills-registry"


def _load_submodule(module_name: str, file_name: str):
    """Load a script from the skills-registry submodule by file name.

    Uses importlib to avoid colliding with the local ``scripts`` package.
    The submodule's ``scripts`` package and ``scripts.registry_contracts``
    are registered in ``sys.modules`` so that internal imports within the
    submodule resolve correctly.
    """
    submodule_scripts = _SUBMODULE / "scripts"

    # Ensure the submodule's scripts package is registered so that
    # intra-package imports (e.g. ``from scripts.registry_contracts ...``)
    # inside the submodule work.  We use a private prefix to avoid
    # clobbering the local scripts package.
    pkg_key = "_sr_scripts"
    if pkg_key not in sys.modules:
        pkg_spec = importlib.util.spec_from_file_location(
            pkg_key,
            submodule_scripts / "__init__.py",
            submodule_search_locations=[str(submodule_scripts)],
        )
        pkg_mod = importlib.util.module_from_spec(pkg_spec)
        sys.modules[pkg_key] = pkg_mod
        pkg_spec.loader.exec_module(pkg_mod)

    # Also register under the canonical ``scripts`` key expected by the
    # submodule's own ``from scripts.X import ...`` statements, but only
    # if it has not already been set to our private package.
    if "scripts" in sys.modules:
        saved_scripts = sys.modules["scripts"]
    else:
        saved_scripts = None
    sys.modules["scripts"] = sys.modules[pkg_key]

    try:
        full_name = f"_sr_scripts.{module_name}"
        if full_name not in sys.modules:
            spec = importlib.util.spec_from_file_location(
                full_name,
                submodule_scripts / file_name,
            )
            mod = importlib.util.module_from_spec(spec)
            sys.modules[full_name] = mod
            # Also register as scripts.<module_name> so internal cross-imports
            # within the submodule resolve.
            sys.modules[f"scripts.{module_name}"] = mod
            spec.loader.exec_module(mod)
        return sys.modules[full_name]
    finally:
        # Restore the original scripts module
        if saved_scripts is not None:
            sys.modules["scripts"] = saved_scripts
        else:
            sys.modules.pop("scripts", None)


def _get_upstream_marketplace():
    mod = _load_submodule("sync_marketplace", "sync_marketplace.py")
    return mod.generate_marketplace


def _get_upstream_generate_site():
    mod = _load_submodule("generate_site", "generate_site.py")
    return mod


SITE_NAME = "Red Hat Global Engineering Skills Registry"
SITE_URL = "https://redhat-global-engineering.github.io/ge-public-skills"
REPO_URL = "https://github.com/redhat-global-engineering/ge-public-skills"
REPO_NAME = "redhat-global-engineering/ge-public-skills"


MKDOCS_CONFIG = f"""\
site_name: {SITE_NAME}
site_url: {SITE_URL}
repo_url: {REPO_URL}
repo_name: {REPO_NAME}

theme:
  name: material
  font: false
  custom_dir: overrides
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: custom
      accent: custom
      toggle:
        icon: material/weather-night
        name: Switch to dark mode
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: custom
      accent: custom
      toggle:
        icon: material/weather-sunny
        name: Switch to light mode
  features:
    - navigation.tabs
    - navigation.indexes
    - search.suggest
    - content.code.copy
    - toc.follow

markdown_extensions:
  - admonition
  - attr_list
  - md_in_html
  - pymdownx.superfences
  - pymdownx.details
  - pymdownx.emoji:
      emoji_index: !!python/name:material.extensions.emoji.twemoji
      emoji_generator: !!python/name:material.extensions.emoji.to_svg
  - tables
  - toc:
      permalink: true

extra_css:
  - assets/stylesheets/extra.css

"""


def _load_registry(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def generate_marketplace(registry_path: Path, output_path: Path) -> None:
    """Generate marketplace.json from registry.yaml."""
    registry = _load_registry(registry_path)
    upstream_fn = _get_upstream_marketplace()
    marketplace = upstream_fn(registry)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(marketplace, f, indent=2)
        f.write("\n")


def generate_site_config() -> str:
    """Return the MkDocs config YAML string."""
    return MKDOCS_CONFIG


def generate_site(registry_path: Path, output_dir: Path) -> None:
    """Generate the MkDocs site with Red Hat branding."""
    site_mod = _get_upstream_generate_site()

    # Monkey-patch the template so generate_site uses our config
    original_template = site_mod.MKDOCS_CONFIG_TEMPLATE
    site_mod.MKDOCS_CONFIG_TEMPLATE = MKDOCS_CONFIG
    try:
        registry = _load_registry(registry_path)
        site_mod.generate_site(registry, output_dir)
    finally:
        site_mod.MKDOCS_CONFIG_TEMPLATE = original_template


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("command", choices=["marketplace", "site", "all"])
    parser.add_argument("--registry", default="registry.yaml")
    args = parser.parse_args()

    registry_path = Path(args.registry)

    if args.command in ("marketplace", "all"):
        output = _REPO_ROOT / ".claude-plugin" / "marketplace.json"
        generate_marketplace(registry_path, output)
        print(f"Generated {output}")

    if args.command in ("site", "all"):
        output_dir = _REPO_ROOT / "site"
        generate_site(registry_path, output_dir)
        print(f"Generated site in {output_dir}/")


if __name__ == "__main__":
    main()

"""Validate registry.yaml against the submodule's JSON Schema.

Usage:
    python scripts/validate.py [--registry registry.yaml]
"""

import argparse
import importlib.util
import sys
from pathlib import Path

import yaml

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_SUBMODULE = _REPO_ROOT / "skills-registry"


def _load_submodule(module_name: str, file_name: str):
    """Load a script from the skills-registry submodule by file name."""
    submodule_scripts = _SUBMODULE / "scripts"

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
            sys.modules[f"scripts.{module_name}"] = mod
            spec.loader.exec_module(mod)
        return sys.modules[full_name]
    finally:
        if saved_scripts is not None:
            sys.modules["scripts"] = saved_scripts
        else:
            sys.modules.pop("scripts", None)


def check_sha_pinning(registry: dict) -> list[str]:
    """Require every plugin with a git-based source to have a sha field."""
    errors = []
    for plugin in registry.get("plugins", []):
        source = plugin.get("source", {})
        if source.get("type") in ("github", "git-subdir"):
            if not source.get("sha"):
                errors.append(
                    f"Plugin '{plugin.get('name', '?')}': source must include "
                    f"a 'sha' field pinning to an exact commit"
                )
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default="registry.yaml")
    args = parser.parse_args()

    validate_mod = _load_submodule("validate_registry", "validate_registry.py")

    with open(args.registry) as f:
        registry = yaml.safe_load(f)

    schema_path = _SUBMODULE / "schema" / "registry.schema.json"
    import json
    with open(schema_path) as f:
        schema = json.load(f)

    errors = validate_mod.validate_schema(registry, schema)
    errors += validate_mod.check_duplicates(registry)
    errors += validate_mod.check_categories(registry)
    errors += check_sha_pinning(registry)

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)

    print("Registry validation passed")


if __name__ == "__main__":
    main()

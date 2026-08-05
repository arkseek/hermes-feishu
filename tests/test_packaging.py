"""Guard against version drift across packaging metadata files."""

import re
from pathlib import Path

import hermes_feishu

ROOT = Path(__file__).resolve().parent.parent


def _version_from_yaml(path: str) -> str:
    text = (ROOT / path).read_text(encoding="utf-8")
    m = re.search(r"^version:\s*(\S+)", text, re.MULTILINE)
    assert m, f"version not found in {path}"
    return m.group(1)


def _version_from_pyproject() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m, "version not found in pyproject.toml"
    return m.group(1)


def test_versions_in_sync():
    """plugin.yaml (repo root and packaged copy), pyproject.toml and
    hermes_feishu.__version__ must all agree."""
    versions = {
        "plugin.yaml": _version_from_yaml("plugin.yaml"),
        "src/hermes_feishu/plugin.yaml": _version_from_yaml("src/hermes_feishu/plugin.yaml"),
        "pyproject.toml": _version_from_pyproject(),
        "hermes_feishu.__version__": hermes_feishu.__version__,
    }
    assert len(set(versions.values())) == 1, f"version drift: {versions}"


def test_plugin_yaml_copies_identical():
    """The repo-root plugin.yaml (git installs) and the packaged copy must
    not drift apart."""
    root = (ROOT / "plugin.yaml").read_text(encoding="utf-8")
    packaged = (ROOT / "src/hermes_feishu/plugin.yaml").read_text(encoding="utf-8")
    assert root == packaged

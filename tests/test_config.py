from __future__ import annotations

import json

import pytest

from birdeye import _config
from birdeye._config import DEFAULT_OPENER, load_opener


def test_load_opener_no_config_file(monkeypatch, tmp_path):
    """When opener.json doesn't exist, return default mappings."""
    monkeypatch.setattr(_config, "OPENER_FILE", tmp_path / "opener.json")

    result = load_opener()

    assert result == DEFAULT_OPENER
    # Ensure we get a copy, not the original
    assert result is not DEFAULT_OPENER


def test_load_opener_valid_config(monkeypatch, tmp_path):
    """When opener.json exists with valid JSON, return those mappings."""
    opener_file = tmp_path / "opener.json"
    custom_mappings = {".md": "typora", ".rs": "code"}
    opener_file.write_text(json.dumps(custom_mappings))
    monkeypatch.setattr(_config, "OPENER_FILE", opener_file)

    result = load_opener()

    assert result == custom_mappings


def test_load_opener_invalid_json(monkeypatch, tmp_path):
    """When opener.json contains invalid JSON, raise JSONDecodeError."""
    opener_file = tmp_path / "opener.json"
    opener_file.write_text("{ invalid json }")
    monkeypatch.setattr(_config, "OPENER_FILE", opener_file)

    with pytest.raises(json.JSONDecodeError):
        load_opener()


def test_load_opener_empty_config(monkeypatch, tmp_path):
    """When opener.json is an empty object, return empty dict."""
    opener_file = tmp_path / "opener.json"
    opener_file.write_text("{}")
    monkeypatch.setattr(_config, "OPENER_FILE", opener_file)

    result = load_opener()

    assert result == {}

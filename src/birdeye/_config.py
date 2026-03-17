from __future__ import annotations

import json
from pathlib import Path

from platformdirs import user_config_dir

CONFIG_DIR = Path(user_config_dir("birdeye"))
OPENER_FILE = CONFIG_DIR / "opener.json"

DEFAULT_OPENER: dict[str, str] = {".py": "code", ".toml": "code"}


def load_opener() -> dict[str, str]:
    """Load opener mappings from config file, or return defaults.

    Returns:
        A dictionary mapping file extensions to opener commands.

    Raises:
        json.JSONDecodeError: If the config file exists but contains invalid JSON.
    """
    if not OPENER_FILE.exists():
        return DEFAULT_OPENER

    with OPENER_FILE.open() as f:
        return json.load(f)

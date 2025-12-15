from pathlib import Path

from birdeye.cli import parse_args
from birdeye.file_tree_viewer import Settings


def test_parse_args(tmp_path: Path):
    settings = parse_args([str(tmp_path), "--no-gitignore"])

    assert settings == Settings(root_folder=tmp_path, use_git_ignore=False)

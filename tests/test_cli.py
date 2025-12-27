from pathlib import Path

from birdeye.cli import parse_args
from birdeye.file_tree_viewer import Settings


def test_parse_args(tmp_path: Path):
    settings = parse_args([str(tmp_path), "--no-gitignore"])

    assert settings == Settings(root_folder=tmp_path, use_git_ignore=False)


def test_parse_args_default_gitignore(tmp_path: Path):
    settings = parse_args([str(tmp_path)])

    assert settings == Settings(root_folder=tmp_path, use_git_ignore=True)


def test_parse_args_default_path():
    settings = parse_args([])

    assert settings == Settings(root_folder=Path("."), use_git_ignore=True)

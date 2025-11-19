from pathlib import Path

import pytest
from gitignore_parser import parse_gitignore

from navl.cli import parse_args
from navl.file_tree_viewer import FileTreeViewer, Settings, TreeNode


@pytest.fixture
def test_path(tmp_path: Path):
    (tmp_path / "src" / "docs").mkdir(exist_ok=True, parents=True)
    (tmp_path / "src" / "my_lib").mkdir(exist_ok=True, parents=True)
    (tmp_path / "src" / "main.py").touch()
    return tmp_path


def test_collect_visibile_nodes_expanded(test_path: Path):
    viewer = FileTreeViewer(test_path)

    viewer._update_display()

    viewer.visible_nodes[1].toggle_expanded()  # expanding the src folder
    viewer._update_display()

    assert [node.path for node in viewer.visible_nodes] == [
        test_path,
        test_path / "src",
        test_path / "src" / "docs",
        test_path / "src" / "main.py",
        test_path / "src" / "my_lib",
    ]


def test_collect_expanded_paths(test_path: Path):
    """Test the _collect_expanded_paths method."""
    root_node = TreeNode(test_path / "src", gitignore_parser=None, parent=None)
    root_node.load_children()
    root_node.children[0].expanded = True  # expanding one path here.

    expanded = tuple(FileTreeViewer._collect_expanded_paths(root_node))

    assert expanded == (test_path / "src" / "docs",)


def test_collect_expanded_paths_no_expanded_nodes(test_path: Path):
    """Test _collect_expanded_paths when no nodes are expanded."""
    root_node = TreeNode(test_path / "src", gitignore_parser=None, parent=None)
    root_node.load_children()

    expanded = tuple(FileTreeViewer._collect_expanded_paths(root_node))

    assert len(expanded) == 0


def test_collect_visible_nodes(test_path: Path):
    """Test the _collect_visible_nodes method."""
    viewer = FileTreeViewer(test_path)
    viewer._update_display()

    assert [node.path for node in viewer.visible_nodes] == [
        test_path,
        test_path / "src",
    ]


def test_gitignore_same_level(test_path: Path):
    # file to ignore is on the same level as the gitignore file.

    git_ignore_file = test_path / "src" / ".gitignore"
    git_ignore_file.write_text("**/main.py")

    node = TreeNode(
        test_path / "src",
        gitignore_parser=parse_gitignore(git_ignore_file),
        parent=None,
    )
    node.load_children()

    assert set([child.path for child in node.children]) == {
        test_path / "src" / ".gitignore",
        test_path / "src" / "docs",
        test_path / "src" / "my_lib",
    }


def test_gitignore_higher_level(test_path: Path):
    # file to ignore is on a level lower than the gitignore file.

    git_ignore_file = test_path / ".gitignore"
    git_ignore_file.write_text("**/main.py")

    node = TreeNode(
        test_path / "src",
        gitignore_parser=parse_gitignore(git_ignore_file),
        parent=None,
    )
    node.load_children()

    assert set([child.path for child in node.children]) == {
        test_path / "src" / "docs",
        test_path / "src" / "my_lib",
    }


def test_no_use_gitignore(test_path: Path):
    git_ignore_file = test_path / "src" / ".gitignore"
    git_ignore_file.write_text("**/main.py")

    node = TreeNode(
        test_path / "src",
        gitignore_parser=None,
        parent=None,
    )
    node.load_children()

    assert set([child.path for child in node.children]) == {
        test_path / "src" / ".gitignore",
        test_path / "src" / "docs",
        test_path / "src" / "my_lib",
        test_path / "src" / "main.py",  # ignoring the gitignore
    }


def test_parse_args(tmp_path: Path):
    settings = parse_args([str(tmp_path), "--no-gitignore"])

    assert settings == Settings(root_folder=tmp_path, use_git_ignore=False)

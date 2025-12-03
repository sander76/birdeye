from pathlib import Path

import pygit2
import pytest

from navl.cli import parse_args
from navl.file_tree_viewer import FileTreeViewer, Settings, TreeNode


@pytest.fixture
def test_path(tmp_path: Path):
    (tmp_path / "src" / "docs").mkdir(exist_ok=True, parents=True)
    (tmp_path / "src" / "main.py").touch()
    (tmp_path / "src" / "my_lib").mkdir(exist_ok=True, parents=True)

    (tmp_path / ".gitignore").touch()
    (tmp_path / ".gitignore").write_text("**/main.py")

    # Initialize git repo and add files
    repo = pygit2.init_repository(tmp_path)

    # Add files to the repo
    repo.index.add_all()
    repo.index.write()

    # Create initial commit
    signature = pygit2.Signature("Test User", "test@example.com")
    tree = repo.index.write_tree()
    repo.create_commit("HEAD", signature, signature, "Initial commit", tree, [])

    return tmp_path


@pytest.fixture
def root_node(test_path) -> TreeNode:
    treenode = TreeNode(test_path, parent=None, level=0, git_repo=None)
    return treenode


def test_down_no_focus_no_idx(root_node, test_path):
    # our root node is not expanded so
    # selecting next will always give this
    # one node back.
    first = root_node.focus(direction=1)
    assert first.path == test_path

    second = first.focus(direction=1)

    # assert first is root_node
    # assert first.focussed is True

    # second = first.focus(direction=1)

    # only one node in the complete
    # tree. Same node is returned again.
    assert second is first
    assert second.path == test_path


def test_expand(root_node, test_path):
    first = root_node.focus(direction=1)
    first.toggle_expanded()
    second = first.focus(direction=1)
    assert second.path == test_path / "src"


def test_down_on_expanded(root_node, test_path):
    root_node.toggle_expanded()

    first = root_node.focus(direction=1)
    assert first is root_node
    second = first.focus(direction=1)
    assert second.focussed is True
    assert first.focussed is False


# def test_collect_visibile_nodes_expanded(test_path: Path):
#     viewer = FileTreeViewer(Settings(root_folder=test_path, use_git_ignore=False))

#     viewer._update_display()

#     viewer.visible_nodes[1].toggle_expanded()  # expanding the src folder
#     viewer._update_display()

#     assert [node.path for node in viewer.visible_nodes] == [
#         test_path,
#         test_path / "src",
#         test_path / "src" / "docs",
#         test_path / "src" / "main.py",
#         test_path / "src" / "my_lib",
#     ]


# def test_collect_expanded_paths(test_path: Path):
#     """Test the _collect_expanded_paths method."""
#     root_node = TreeNode(test_path / "src", gitignore_parser=None, parent=None)
#     root_node.load_children()
#     root_node.children[0].expanded = True  # expanding one path here.

#     expanded = tuple(FileTreeViewer._collect_expanded_paths(root_node))

#     assert expanded == (test_path / "src" / "docs",)


# def test_collect_expanded_paths_no_expanded_nodes(test_path: Path):
#     """Test _collect_expanded_paths when no nodes are expanded."""
#     root_node = TreeNode(test_path / "src", gitignore_parser=None, parent=None)
#     root_node.load_children()

#     expanded = tuple(FileTreeViewer._collect_expanded_paths(root_node))

#     assert len(expanded) == 0


# def test_collect_visible_nodes(test_path: Path):
#     """Test the _collect_visible_nodes method."""
#     viewer = FileTreeViewer(test_path)
#     viewer._update_display()

#     assert [node.path for node in viewer.visible_nodes] == [
#         test_path,
#         test_path / "src",
#     ]


# def test_gitignore_root_level(test_path: Path):
#     # file to ignore is on the same level as the gitignore file.

#     node = TreeNode(
#         test_path,
#         parent=None,
#         use_gitignore=True,
#         git_repo=pygit2.Repository(test_path),
#     )
#     node.load_children()

#     assert set([child.path for child in node.children]) == {
#         test_path / ".gitignore",
#         test_path / "src",
#     }


# def test_gitignore_higher_level(test_path: Path):
#     # file to ignore is on a level lower than the gitignore file.

#     node = TreeNode(
#         test_path / "src",
#         parent=None,
#         use_gitignore=True,
#         git_repo=pygit2.Repository(test_path),
#     )
#     node.load_children()

#     assert set([child.path for child in node.children]) == {
#         test_path / "src" / "docs",
#         test_path / "src" / "my_lib",
#     }


# def test_no_use_gitignore(test_path: Path):
#     git_ignore_file = test_path / "src" / ".gitignore"
#     git_ignore_file.write_text("**/main.py")

#     node = TreeNode(
#         test_path / "src",
#         parent=None,
#         use_gitignore=False,
#         git_repo=pygit2.Repository(test_path),
#     )
#     node.load_children()

#     assert set([child.path for child in node.children]) == {
#         test_path / "src" / ".gitignore",
#         test_path / "src" / "docs",
#         test_path / "src" / "my_lib",
#         test_path / "src" / "main.py",  # ignoring the gitignore
#     }


# def test_parse_args(tmp_path: Path):
#     settings = parse_args([str(tmp_path), "--no-gitignore"])

#     assert settings == Settings(root_folder=tmp_path, use_git_ignore=False)

from pathlib import Path

import pygit2
import pytest

from birdeye.file_tree_viewer import TreeNode


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
def test_path_no_git(tmp_path: Path):
    # ..root
    # ├── pyproject.toml
    # ├── src
    # │   ├── main.py
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "src").mkdir(exist_ok=True, parents=True)
    (tmp_path / "src" / "main.py").touch()
    (tmp_path / "src" / "my_lib").mkdir(exist_ok=True, parents=True)
    (tmp_path / "src" / "my_lib" / "base.py").touch()
    (tmp_path / "tests").mkdir(exist_ok=True, parents=True)
    (tmp_path / "tests" / "test_main.py").touch()
    return tmp_path


@pytest.fixture
def root_node_no_git(test_path_no_git) -> TreeNode:
    treenode = TreeNode(test_path_no_git, parent=None, level=0, git_repo=None)
    return treenode


def test_single_node_up_down(root_node_no_git: TreeNode):
    # our root node is not expanded so
    # selecting next or previous will always give this
    # one node back.

    # by default a root treenode is always expanded.
    # so for this test we first un-expand it.
    root_node_no_git.set_expanded(False)

    first = root_node_no_git.focus(direction=1)
    assert first.focussed is True

    down_one = first.focus(direction=1)

    assert down_one is first
    assert down_one.focussed is True

    up_one = down_one.focus(direction=-1)
    assert up_one is first
    assert up_one.focussed is True


from dirty_equals import HasAttributes


def test_expanded_up_down(root_node_no_git: TreeNode):
    # ..root
    # ├── pyproject.toml
    # ├── src
    # │   ├── main.py
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py
    root_path = root_node_no_git.path

    first = root_node_no_git

    second = first.focus(direction=1)
    assert second == HasAttributes(focussed=True, path=root_path / "pyproject.toml")

    third = second.focus(direction=1)
    assert third == HasAttributes(focussed=True, path=root_path / "src")
    assert second.focussed is False

    up = third.focus(direction=-1)
    assert up is second
    assert up.focussed is True
    assert third.focussed is False


def test_down_beyond_list(root_node_no_git: TreeNode):
    # ..root
    # ├── pyproject.toml
    # ├── src
    # │   ├── main.py
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py

    # goto src folder and expand.
    # go down until my_lib.
    # one more down must focus tests
    src_node = root_node_no_git.focus(1).focus(1)
    assert src_node.name == "src"

    src_node.set_expanded(True)
    my_lib_node = src_node.focus(1).focus(1)
    assert my_lib_node.name == "my_lib"

    tests_node = my_lib_node.focus(1)
    assert tests_node.name == "tests"


def test_up_into_list(root_node_no_git: TreeNode):
    # ..root
    # ├── pyproject.toml
    # ├── src
    # │   ├── main.py
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py

    # goto src folder, expand
    # scroll down till test is reached

    # scroll up and expect to highlight my_lib.

    src_node = root_node_no_git.focus(1).focus(1)
    assert src_node.name == "src"

    src_node.set_expanded(True)
    my_lib_node = src_node.focus(1).focus(1)
    assert my_lib_node.name == "my_lib"

    tests_node = my_lib_node.focus(1)
    assert tests_node.name == "tests"

    my_lib = tests_node.focus(-1)
    assert my_lib.name == "my_lib"


def test_up_after_twice_into_list(root_node_no_git: TreeNode):
    # ..root
    # ├── pyproject.toml
    # ├── src
    # │   ├── main.py
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py

    # goto src folder, expand, goto my_lib folder, expand
    # scroll down till test is reached

    # scroll up and expect to highlight base.py

    src_node = root_node_no_git.focus(1).focus(1)
    assert src_node.name == "src"

    src_node.set_expanded(True)
    my_lib_node = src_node.focus(1).focus(1)
    assert my_lib_node.name == "my_lib"
    my_lib_node.set_expanded(True)
    base_py = my_lib_node.focus(1)
    assert base_py.name == "base.py"

    tests_node = base_py.focus(1)
    assert tests_node.name == "tests"

    my_lib = tests_node.focus(-1)
    assert my_lib.name == "base.py"


def test_expand_true_on_node(root_node_no_git: TreeNode):
    # ..root
    # ├── pyproject.toml
    # ├── src
    # │   ├── main.py
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py

    # when we call expand=True on a node (so a single file) we do nothing.
    pyproject_file_node = root_node_no_git.focus(direction=1)

    assert pyproject_file_node.name == "pyproject.toml"

    pyproject_file_node.expanded = True
    assert pyproject_file_node.focussed is True


def test_expand_false_on_node(root_node_no_git: TreeNode):
    # ..root
    # ├── pyproject.toml
    # ├── src
    # │   ├── main.py
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py

    # when we call expand=False on a node we do not collapse, but focus parent.
    pyproject_file_node = root_node_no_git.focus(direction=1)

    assert pyproject_file_node.name == "pyproject.toml"

    pyproject_file_node.set_expanded(False)
    assert pyproject_file_node.focussed is False
    assert root_node_no_git.focussed is True


def test_expand_false_on_tree_node(root_node_no_git: TreeNode):
    # ..root
    # ├── pyproject.toml
    # ├── src
    # │   ├── main.py
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py

    # when we call expand=False on a node we do not collapse, but focus parent.
    pyproject_file_node = root_node_no_git.focus(direction=1).focus(direction=1)

    assert pyproject_file_node.name == "src"

    pyproject_file_node.set_expanded(False)
    assert pyproject_file_node.focussed is False


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

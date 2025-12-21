from pathlib import Path

import pygit2
import pytest
from dirty_equals import HasAttributes

from birdeye.file_tree_viewer import FileTreeViewer, Settings, TreeNode


@pytest.fixture
def test_path_with_git(tmp_path: Path):
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


@pytest.fixture
def settings_no_git(test_path_no_git) -> Settings:
    settings = Settings(root_folder=test_path_no_git, use_git_ignore=False)
    return settings


def test_single_node_up_down(settings_no_git: Settings):
    # our root node is not expanded so
    # selecting next or previous will always give the
    # same node back.

    # by default a root treenode is always expanded.
    # so for this test we first un-expand it.
    tree_viewer = FileTreeViewer(settings_no_git)

    root_node = tree_viewer._selected_node
    root_node.path == settings_no_git.root_folder

    tree_viewer._selected_node.set_expanded(False)
    # root_node_no_git.set_expanded(False)

    tree_viewer._selected_node.focus(direction=1)
    assert tree_viewer._selected_node == root_node
    assert root_node.focussed is True

    tree_viewer._selected_node.focus(direction=-1)
    assert tree_viewer._selected_node == root_node
    assert tree_viewer._selected_node.focussed is True


def test_expanded_up_down(settings_no_git: Settings):
    # ..root
    # ├── pyproject.toml
    # ├── src
    # │   ├── main.py
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py

    tree_viewer = FileTreeViewer(settings_no_git)

    root_node = tree_viewer._selected_node
    # root_path = root_node_no_git.path

    # first = root_node_no_git

    tree_viewer._selected_node.focus(direction=1)
    down_1 = tree_viewer._selected_node
    down_1.name == "pyproject.toml"
    down_1.focussed is True

    tree_viewer._selected_node.focus(direction=1)
    down_2 = tree_viewer._selected_node
    down_2.focussed is True
    down_2.name == "src"
    down_1.focussed is False

    tree_viewer._selected_node.focus(direction=-1)
    assert tree_viewer._selected_node is down_1
    assert tree_viewer._selected_node.focussed is True


def test_down_beyond_list(settings_no_git: Settings):
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
    tree_viewer = FileTreeViewer(settings_no_git)

    tree_viewer._selected_node.focus(1)
    tree_viewer._selected_node.focus(1)

    src_node = tree_viewer._selected_node
    assert src_node.name == "src"

    src_node.set_expanded(True)

    tree_viewer._selected_node.focus(1)
    tree_viewer._selected_node.focus(1)
    my_lib_node = tree_viewer._selected_node
    assert my_lib_node.name == "my_lib"

    tree_viewer._selected_node.focus(1)
    tests_node = tree_viewer._selected_node
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


def test_gitignore_root_level(test_path_with_git: Path):
    # file to ignore is on the same level as the gitignore file.

    node = TreeNode(
        test_path_with_git,
        parent=None,
        level=0,
        use_gitignore=True,
        git_repo=pygit2.Repository(test_path_with_git),
    )
    _all = tuple(node.full_tree())

    assert set([node.path for node in _all]) == {
        test_path_with_git,
        test_path_with_git / ".gitignore",
        test_path_with_git / "src",
    }


def test_gitignore_higher_level(test_path_with_git: Path):
    # file to ignore is on a level lower than the gitignore file.

    node = TreeNode(
        test_path_with_git / "src",
        parent=None,
        level=1,
        use_gitignore=True,
        git_repo=pygit2.Repository(test_path_with_git),
    )
    _all = tuple(node.full_tree())

    assert set([node.path for node in _all]) == {
        test_path_with_git / "src",
        test_path_with_git / "src" / "docs",
        test_path_with_git / "src" / "my_lib",
    }


def test_no_use_gitignore(test_path_with_git: Path):
    git_ignore_file = test_path_with_git / "src" / ".gitignore"
    git_ignore_file.write_text("**/main.py")

    node = TreeNode(
        test_path_with_git / "src",
        parent=None,
        level=0,
        use_gitignore=False,
        git_repo=pygit2.Repository(test_path_with_git),
    )
    node.load_children()

    _all = tuple(node.full_tree())

    assert set([node.path for node in _all]) == {
        test_path_with_git / "src",
        test_path_with_git / "src" / ".gitignore",
        test_path_with_git / "src" / "docs",
        test_path_with_git / "src" / "my_lib",
        test_path_with_git / "src" / "main.py",  # ignoring the gitignore
    }

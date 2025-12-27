import dataclasses
from pathlib import Path
from unittest.mock import Mock

import pygit2
import pytest
from dirty_equals import HasAttributes

from birdeye._nodes import BaseNode
from birdeye.file_tree_viewer import FileTreeViewer, Node, Settings, TreeNode


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
def test_path_with_git(test_path_no_git: Path):
    with open(test_path_no_git / ".gitignore", "w") as fl:
        fl.write("**/main.py\n")
        fl.write("pyproject.toml\n")

    # Initialize git repo and add files
    repo = pygit2.init_repository(test_path_no_git)
    repo.index.add(".gitignore")
    # Add files to the repo
    repo.index.add_all()
    repo.index.write()

    # Create initial commit
    signature = pygit2.Signature("Test User", "test@example.com")
    tree = repo.index.write_tree()
    repo.create_commit("HEAD", signature, signature, "Initial commit", tree, [])

    return test_path_no_git


@pytest.fixture
def root_node_no_git(test_path_no_git) -> TreeNode:
    treenode = TreeNode(test_path_no_git, parent=None, level=0, git_repo=None)
    return treenode


@pytest.fixture
def settings_no_git(test_path_no_git) -> Settings:
    settings = Settings(root_folder=test_path_no_git, use_git_ignore=False)
    return settings


@pytest.fixture
def settings_with_git(test_path_with_git) -> Settings:
    settings = Settings(root_folder=test_path_with_git, use_git_ignore=True)
    return settings


def test_single_node_up_down(settings_no_git: Settings):
    # our root node is not expanded so
    # selecting next or previous will always give the
    # same node back.

    # by default a root treenode is always expanded.
    # so for this test we first un-expand it.
    tree_viewer = FileTreeViewer(settings_no_git)

    root_node = tree_viewer._focussed_node
    root_node.path == settings_no_git.root_folder

    tree_viewer._focussed_node.exit()
    # root_node_no_git.exit()

    tree_viewer._focussed_node.focus(direction=1)
    assert tree_viewer._focussed_node == root_node
    assert root_node.focussed is True

    tree_viewer._focussed_node.focus(direction=-1)
    assert tree_viewer._focussed_node == root_node
    assert tree_viewer._focussed_node.focussed is True


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

    tree_viewer._focussed_node.focus(direction=1)
    down_1 = tree_viewer._focussed_node
    down_1.name == "pyproject.toml"
    down_1.focussed is True

    tree_viewer._focussed_node.focus(direction=1)
    down_2 = tree_viewer._focussed_node
    down_2.focussed is True
    down_2.name == "src"
    down_1.focussed is False

    tree_viewer._focussed_node.focus(direction=-1)
    assert tree_viewer._focussed_node is down_1
    assert tree_viewer._focussed_node.focussed is True


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

    tree_viewer._focussed_node.focus(1)
    tree_viewer._focussed_node.focus(1)

    src_node = tree_viewer._focussed_node
    assert src_node.name == "src"

    src_node.enter()

    tree_viewer._focussed_node.focus(1)
    tree_viewer._focussed_node.focus(1)
    my_lib_node = tree_viewer._focussed_node
    assert my_lib_node.name == "my_lib"

    tree_viewer._focussed_node.focus(1)
    tests_node = tree_viewer._focussed_node
    assert tests_node.name == "tests"


def test_up_into_list(settings_no_git: Settings):
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
    tv = FileTreeViewer(settings_no_git)

    tv._focussed_node.focus(1)
    tv._focussed_node.focus(1)
    src_node = tv._focussed_node
    assert src_node.name == "src"

    src_node.enter()

    tv._focussed_node.focus(1)
    tv._focussed_node.focus(1)
    my_lib_node = tv._focussed_node
    assert my_lib_node.name == "my_lib"

    tv._focussed_node.focus(1)
    assert tv._focussed_node.name == "tests"

    tv._focussed_node.focus(-1)
    assert tv._focussed_node.name == "my_lib"


def test_up_after_twice_into_list(settings_no_git: Settings):
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

    tv = FileTreeViewer(settings_no_git)
    tv._focussed_node.focus(1)
    tv._focussed_node.focus(1)

    tv._focussed_node.name == "src"
    tv._focussed_node.enter()

    tv._focussed_node.focus(1)
    tv._focussed_node.focus(1)
    tv._focussed_node.name == "my_lib"
    tv._focussed_node.enter()

    tv._focussed_node.focus(1)
    tv._focussed_node.name == "base.py"

    tv._focussed_node.focus(1)
    tv._focussed_node.name = "tests"

    tv._focussed_node.focus(-1)
    tv._focussed_node.name = "base.py"


def test_enter_on_node(settings_no_git: Settings):
    # ..root
    # ├── pyproject.toml
    # ├── src
    # │   ├── main.py
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py
    # when we call expand=True on a node (so a single file) we do nothing.

    ft = FileTreeViewer(settings_no_git)
    ft._focussed_node.focus(1)

    assert ft._focussed_node.name == "pyproject.toml"

    ft._focussed_node.enter()
    assert ft._focussed_node.focussed is True


def test_exit_on_node(settings_no_git: Settings):
    # ..root
    # ├── pyproject.toml
    # ├── src
    # │   ├── main.py
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py

    # when we call expand=False on a node we do not collapse, but focus parent.

    # navigating to the my_lib node
    ft = FileTreeViewer(settings_no_git)
    ft._focussed_node.focus(1)
    ft._focussed_node.focus(1)
    ft._focussed_node.enter()
    ft._focussed_node.focus(1)
    ft._focussed_node.focus(1)

    assert ft._focussed_node.name == "my_lib"

    ft._focussed_node.exit()
    assert ft._focussed_node.name == "src"


def test_empty_folder(tmp_path: Path):
    """Handle empty folder correctly."""
    (tmp_path / "src").mkdir()

    ft = FileTreeViewer(Settings(tmp_path, use_git_ignore=False))

    ft._focussed_node.focus(1)
    assert ft._focussed_node.name == "src"

    ft._focussed_node.enter()
    assert tuple(nd.name for nd in ft._root_node.full_tree()) == (tmp_path.name, "src")


def test_gitignore_root_level(settings_with_git: Settings):
    # ..root
    # ├── .gitignore
    # ├── pyproject.toml  # git ignored.
    # ├── src
    # │   ├── main.py  # git ignored.
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py
    # file to ignore is on the same level as the gitignore file.
    ft = FileTreeViewer(settings_with_git)

    _all = tuple(ft._focussed_node.full_tree())

    assert set([node.path for node in _all]) == {
        settings_with_git.root_folder,
        settings_with_git.root_folder / ".gitignore",
        settings_with_git.root_folder / "src",
        settings_with_git.root_folder / "tests",
    }


def test_gitignore_higher_level(settings_with_git: Settings):
    # ..root
    # ├── .gitignore
    # ├── pyproject.toml  # git ignored.
    # ├── src
    # │   ├── main.py  # git ignored.
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py

    # file to ignore is on a level lower than the gitignore file.
    ft = FileTreeViewer(settings_with_git)
    root_node = ft._focussed_node
    ft._focussed_node.focus(1)
    ft._focussed_node.focus(1)
    ft._focussed_node.enter()

    _all = tuple(root_node.full_tree())

    assert set([node.path for node in _all]) == {
        settings_with_git.root_folder,
        settings_with_git.root_folder / ".gitignore",
        settings_with_git.root_folder / "src",
        settings_with_git.root_folder / "src" / "my_lib",
        settings_with_git.root_folder / "tests",
    }


def test_no_use_gitignore(settings_with_git: Settings):
    # ..root
    # ├── .gitignore
    # ├── pyproject.toml  # git ignored.
    # ├── src
    # │   ├── main.py  # git ignored.
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py
    new_settings = dataclasses.replace(settings_with_git, use_git_ignore=False)

    ft = FileTreeViewer(new_settings)

    _all = tuple(ft._focussed_node.full_tree())

    assert set([node.path for node in _all]) == {
        settings_with_git.root_folder,
        settings_with_git.root_folder / ".git",
        settings_with_git.root_folder / "pyproject.toml",  # normally in gitignored.
        settings_with_git.root_folder / ".gitignore",
        settings_with_git.root_folder / "src",
        settings_with_git.root_folder / "tests",
    }


def test_allnodes(settings_no_git: Settings):
    # ..root
    # ├── pyproject.toml
    # ├── src
    # │   ├── main.py
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py
    ft = FileTreeViewer(settings_no_git)

    all_nodes = list(nd.name for nd in ft._focussed_node.all_nodes())
    assert all_nodes == [
        settings_no_git.root_folder.name,
        "pyproject.toml",
        "src",
        "main.py",
        "my_lib",
        "base.py",
        "tests",
        "test_main.py",
    ]


def test_find_single_result_is_expanded(settings_no_git: Settings):
    # ..root
    # ├── pyproject.toml
    # ├── src
    # │   ├── main.py
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py
    ft = FileTreeViewer(settings_no_git)

    ft.find("base")

    _all = tuple(ft._focussed_node.full_tree())
    assert tuple(nd.name for nd in _all) == (
        settings_no_git.root_folder.name,
        "pyproject.toml",
        "src",
        "main.py",
        "my_lib",
        "base.py",
        "tests",
    )


def test_find_multiple_results_is_expanded(settings_no_git: Settings):
    # ..root
    # ├── pyproject.toml
    # ├── src
    # │   ├── main.py
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py
    ft = FileTreeViewer(settings_no_git)

    ft.find("main")

    _all = tuple(ft._focussed_node.full_tree())
    assert tuple(nd.name for nd in _all) == (
        settings_no_git.root_folder.name,
        "pyproject.toml",
        "src",
        "main.py",
        "my_lib",
        "tests",
        "test_main.py",
    )


class TestRender:
    @pytest.fixture
    def node(self) -> BaseNode:
        dummy_tree_node = Mock(spec=TreeNode)
        nd = BaseNode(
            Path("some/path/test_node"),
            parent=dummy_tree_node,
            level=1,
        )
        return nd

    # todo: test 't_no' and 'node'
    def test_find_test(self, node):
        node.find("test")
        result = node.render()

        assert result == (
            ("", " "),  # level indent
            ("", "📄"),  # icon
            ("class:node_find_match", "test"),
            ("", "_node"),
            ("", "\n"),
        )

    def test_find_t_no(self, node):
        node.find("t_no")
        result = node.render()

        assert result == (
            ("", " "),
            ("", "📄"),  # icon
            ("", "tes"),
            ("class:node_find_match", "t_no"),
            ("", "de"),
            ("", "\n"),
        )

    def test_find_node(self, node):
        node.find("node")
        result = node.render()

        assert result == (
            ("", " "),
            ("", "📄"),
            ("", "test_"),
            ("class:node_find_match", "node"),
            ("", "\n"),
        )

    def test_focussed_and_highlight(self, node):
        node.find("t_no")
        node.focussed = True

        result = node.render()

        assert result == (
            ("", " "),
            ("", "📄"),  # icon
            ("class:node_focussed", "tes"),
            ("class:node_find_match", "t_no"),
            ("class:node_focussed", "de"),
            ("", "\n"),
        )

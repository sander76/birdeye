import dataclasses
from pathlib import Path

import pygit2
import pytest
from textual.style import Style
from textual.widgets import Tree

from birdeye._nodes import NodeMeta
from birdeye.birdeye import BirdeyeApp
from birdeye.file_tree_viewer import BirdeyeTree, FileTreeViewer, Settings


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
def settings_no_git(test_path_no_git) -> Settings:
    settings = Settings(root_folder=test_path_no_git, use_git_ignore=False)
    return settings


@pytest.fixture
def settings_with_git(test_path_with_git) -> Settings:
    settings = Settings(root_folder=test_path_with_git, use_git_ignore=True)
    return settings


def create_app(settings: Settings) -> BirdeyeApp:
    """Helper to create a BirdeyeApp for testing."""
    return BirdeyeApp(settings)


@pytest.mark.asyncio
async def test_tree_shows_children(settings_no_git: Settings):
    """Test that the tree shows children of the root folder."""
    # ..root
    # ├── pyproject.toml
    # ├── src
    # └── tests
    app = create_app(settings_no_git)

    async with app.run_test():
        tree = app.query_one(Tree)

        # Get the names of root's children
        child_names = [node.label.plain for node in tree.root.children]

        # Should have src, tests directories and pyproject.toml file
        assert "src" in child_names
        assert "tests" in child_names
        assert "pyproject.toml" in child_names


@pytest.mark.asyncio
async def test_expand_directory(settings_no_git: Settings):
    """Test that expanding a directory loads its children."""
    # ..root
    # ├── pyproject.toml
    # ├── src
    # │   ├── main.py
    # │   └── my_lib
    # └── tests
    app = create_app(settings_no_git)

    async with app.run_test() as pilot:
        tree = app.query_one(Tree)

        src_node = next(nd for nd in tree.root.children if "src" in nd.label.plain)

        src_node.expand()
        await pilot.pause()

        # Check that src has children now
        child_names = [node.label.plain for node in src_node.children]
        assert "my_lib" in child_names
        assert "main.py" in child_names


@pytest.mark.asyncio
async def test_navigation_down(settings_no_git: Settings):
    """Test navigating down in the tree."""
    app = create_app(settings_no_git)

    async with app.run_test() as pilot:
        tree = app.query_one(Tree)

        # Press down to move to first child
        await pilot.press("down")
        await pilot.pause()

        # The cursor should have moved
        assert tree.cursor_node is not None
        assert tree.cursor_node != tree.root


@pytest.mark.asyncio
async def test_navigation_up(settings_no_git: Settings):
    """Test navigating up in the tree."""
    app = create_app(settings_no_git)

    async with app.run_test() as pilot:
        tree = app.query_one(Tree)

        # Move down first
        await pilot.press("down")
        await pilot.pause()
        first_node = tree.cursor_node

        # Move down again
        await pilot.press("down")
        await pilot.pause()

        # Move back up
        await pilot.press("up")
        await pilot.pause()

        # Should be back at first node
        assert tree.cursor_node == first_node


@pytest.mark.asyncio
async def test_gitignore_filters_files(settings_with_git: Settings):
    """Test that gitignore filtering works."""
    # ..root
    # ├── .gitignore
    # ├── pyproject.toml  # git ignored
    # ├── src
    # │   ├── main.py  # git ignored
    # │   └── my_lib
    # └── tests
    app = create_app(settings_with_git)

    async with app.run_test():
        tree = app.query_one(Tree)

        # Get the names of root's children
        child_names = [node.label.plain for node in tree.root.children]

        # pyproject.toml should be filtered out
        assert "pyproject.toml" not in child_names
        # .gitignore should be present
        assert ".gitignore" in child_names
        # src and tests should be present
        assert "src" in child_names
        assert "tests" in child_names


@pytest.mark.asyncio
async def test_gitignore_filters_nested_files(settings_with_git: Settings):
    """Test that gitignore filtering works for nested files."""
    # ..root
    # ├── .gitignore
    # ├── src
    # │   ├── main.py  # git ignored
    # │   └── my_lib
    app = create_app(settings_with_git)

    async with app.run_test() as pilot:
        tree = app.query_one(Tree)

        # Find and expand src node
        src_node = None
        for node in tree.root.children:
            if "src" in node.label.plain:
                src_node = node
                break

        assert src_node is not None
        src_node.expand()
        await pilot.pause()

        # main.py should be filtered out
        child_names = [node.label.plain for node in src_node.children]
        assert "main.py" not in child_names
        assert "my_lib" in child_names


@pytest.mark.asyncio
async def test_no_gitignore_shows_all_files(settings_with_git: Settings):
    """Test that disabling gitignore shows all files."""
    # Create settings with gitignore disabled
    new_settings = dataclasses.replace(settings_with_git, use_git_ignore=False)
    app = create_app(new_settings)

    async with app.run_test():
        tree = app.query_one(Tree)

        # Get the names of root's children
        child_names = [node.label.plain for node in tree.root.children]

        # pyproject.toml should now be visible
        assert "pyproject.toml" in child_names
        # .git folder should also be visible
        assert ".git" in child_names


@pytest.mark.asyncio
async def test_empty_folder(tmp_path: Path):
    """Handle empty folder correctly."""
    (tmp_path / "src").mkdir()

    settings = Settings(tmp_path, use_git_ignore=False)
    app = create_app(settings)

    async with app.run_test() as pilot:
        tree = app.query_one(Tree)

        # Find and expand src node
        src_node = None
        for node in tree.root.children:
            if "src" in node.label.plain:
                src_node = node
                break

        assert src_node is not None
        src_node.expand()
        await pilot.pause()

        # src should have no children
        assert len(src_node.children) == 0


@pytest.mark.asyncio
async def test_search_shows_input(settings_no_git: Settings):
    """Test that search shows the input field."""
    app = create_app(settings_no_git)

    async with app.run_test() as pilot:
        from textual.widgets import Input

        search_input = app.query_one("#search-input", Input)

        # Initially hidden
        assert search_input.display is False

        # Press / to show search
        await pilot.press("slash")

        # Now visible
        assert search_input.display is True


@pytest.mark.asyncio
async def test_search_hides_on_submit(settings_no_git: Settings):
    """Test that search input hides after submitting."""
    app = create_app(settings_no_git)

    async with app.run_test() as pilot:
        search_input = app.query_one("#search-input")

        # Show search
        await pilot.press("slash")
        assert search_input.display is True

        # Type and submit
        await pilot.press(*"test")
        await pilot.press("enter")

        # Should be hidden again
        assert search_input.display is False


def test_render_label():
    tree = BirdeyeTree(label="abc")
    nd = tree.root.add_leaf(label="some_text", data=NodeMeta(find_match=(1, 3)))

    result = tree.render_label(nd, base_style=Style(), style=Style())

    assert result.markup == "s[on yellow]om[/on yellow]e_text"


@pytest.mark.asyncio
async def test_highlight_next(settings_no_git: Settings):
    # ..root
    # ├── pyproject.toml
    # ├── src
    # │   ├── main.py
    # │   └── my_lib
    # │       └── base.py
    # └── tests
    #     └── test_main.py
    app = create_app(settings_no_git)
    async with app.run_test() as pilot:
        await pilot.press("slash")
        await pilot.press(*"main")
        await pilot.press("enter")

        tree_viewer = app.query_one("FileTreeViewer", FileTreeViewer)

        # check the root of the node is selected.
        assert tree_viewer._tree.cursor_node.line == 0

        await pilot.press("n")
        assert tree_viewer._tree.cursor_node.label.plain == "main.py"

        await pilot.press("n")
        assert tree_viewer._tree.cursor_node.label.plain == "test_main.py"

        # end of the list reached.
        await pilot.press("n")
        assert tree_viewer._tree.cursor_node.label.plain == "test_main.py"

        await pilot.press("p")
        assert tree_viewer._tree.cursor_node.label.plain == "main.py"

        # upper end of list reached.
        await pilot.press("p")
        assert tree_viewer._tree.cursor_node.label.plain == "main.py"

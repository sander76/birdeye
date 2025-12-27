import pytest
from textual.widgets import Input

from birdeye import birdeye
from birdeye.file_tree_viewer import Settings


@pytest.fixture
def tmp_path_with_files(tmp_path):
    """Create a temporary directory with some files for testing."""
    (tmp_path / "file1.txt").touch()
    (tmp_path / "file2.txt").touch()
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "file3.txt").touch()
    return tmp_path


@pytest.mark.asyncio
async def test_short_cut_key_search(tmp_path_with_files):
    """Test that pressing / shows the search input."""
    app = birdeye.app(
        settings=Settings(root_folder=tmp_path_with_files, use_git_ignore=False),
    )

    async with app.run_test() as pilot:
        # Search input should be hidden initially
        search_input = app.query_one("#search-input", Input)
        assert search_input.display is False

        # Press / to activate search
        await pilot.press("slash")

        # Search input should now be visible
        assert search_input.display is True

        # Type in the search box
        await pilot.press(*"abc")

        # Check the input has the text
        assert search_input.value == "abc"


@pytest.mark.asyncio
async def test_quit_with_q(tmp_path_with_files):
    """Test that pressing q quits the app."""
    app = birdeye.app(
        settings=Settings(root_folder=tmp_path_with_files, use_git_ignore=False),
    )

    async with app.run_test() as pilot:
        await pilot.press("q")
        # App should have exited
        assert app._exit is True

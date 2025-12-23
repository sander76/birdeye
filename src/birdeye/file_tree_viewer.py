"""
A full screen file tree viewer using prompt_toolkit.
Navigate with arrow keys, expand/collapse with Enter or Space.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Literal

import pygit2
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import ConditionalContainer, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.scrollable_pane import ScrollablePane

from birdeye._nodes import Node, TreeNode

_logger = logging.getLogger(__name__)


@dataclass
class Settings:
    root_folder: Path
    use_git_ignore: bool = True


def use_gitignore(
    repo: pygit2.Repository, root_folder: Path
) -> Generator[Path, None, None]:
    """check whether any child inside the root_folder is being git-ignored."""

    as_path = Path(repo.workdir)

    for child in root_folder.iterdir():
        rel_path = str(child.relative_to(as_path))
        if repo.path_is_ignored(rel_path):
            continue
        yield child


class FileTreeViewer:
    """Main application class for the file tree viewer."""

    _root_node: TreeNode
    _focussed_node: TreeNode | Node

    def __init__(self, settings: Settings):
        self.root_path = settings.root_folder.resolve()
        self._settings = settings
        self._root_node = self._focussed_node = self._init_root_node()

        text_control = FormattedTextControl(
            text=self._update_display,
            focusable=True,
            key_bindings=self._setup_key_bindings(),
        )

        # Create main window with scrollable pane
        main_window = ScrollablePane(Window(content=text_control, wrap_lines=True))
        # Create layout
        self._container = HSplit([main_window])

    def __pt_container__(self):
        return self._container

    def _init_root_node(self) -> TreeNode:
        _logger.debug("init root")
        if (self.root_path / ".git").exists():
            repository = pygit2.Repository(self.root_path)
        else:
            repository = None

        root_node = TreeNode(
            self.root_path,
            parent=self,
            level=0,
            use_gitignore=self._settings.use_git_ignore,
            git_repo=repository,
        )
        return root_node

    def _setup_key_bindings(self) -> KeyBindings:
        """Setup key bindings for navigation."""
        kb = KeyBindings()

        @kb.add("up")
        def move_up(event):
            self._focussed_node.focus(-1)

        @kb.add("down")
        def move_down(event):
            self._focussed_node.focus(1)

        @kb.add("right")
        def enter_node(event):
            self._focussed_node.enter()

        @kb.add("left")
        def exit_node(event):
            self._focussed_node.exit()

        @kb.add("q")
        @kb.add("c-c")
        def quit_app(event):
            event.app.exit()

        @kb.add("/")
        def start_search(event):
            """Show search input widget."""
            # AI! show a text input item in the footer when the / key is pressed.

        # @kb.add("r")
        # def refresh(event):
        #     self._refresh_tree()

        return kb

    def bubble(self, event: str, event_data: object) -> None:
        if event == "focus_changed":
            if event_data is None:
                return
            self._focussed_node.focussed = False
            self._focussed_node = event_data
            self._focussed_node.focussed = True

    def _update_display(self) -> FormattedText:
        """Update the display buffer with current tree state."""

        # nodes = list((node.render() for node in self._root_node.full_tree()))

        def render() -> Generator[tuple[str, str], None, None]:
            for node in self._root_node.full_tree():
                if node.focussed:
                    yield ("[SetCursorPosition]", "")
                yield node.render()

        nodes = (node for node in render())

        _logger.debug(nodes)

        return FormattedText(nodes)

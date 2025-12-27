"""
A full screen file tree viewer using prompt_toolkit.
Navigate with arrow keys, expand/collapse with Enter or Space.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Generator, Literal

import pygit2
from prompt_toolkit.application import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion.base import ThreadedCompleter
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Container,
    HSplit,
    Window,
)
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.processors import BeforeInput, Processor
from prompt_toolkit.layout.scrollable_pane import ScrollablePane
from prompt_toolkit.styles.style import Style
from prompt_toolkit.widgets import TextArea

from birdeye._nodes import Node, TreeNode

_logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class Settings:
    root_folder: Path
    use_git_ignore: bool = True
    style_node_focussed: str = "bg:#ffffff fg:#000000"
    style_node_find_match: str = "bg:#ffff00 fg:#000000"

    def to_style_dict(self) -> dict[str, str]:
        return {
            "node_focussed": self.style_node_focussed,
            "node_find_match": self.style_node_find_match,
        }


class Search:
    def __init__(self, on_start_search: Callable[[str], None]):
        self.buffer = Buffer()
        self.control = BufferControl(
            buffer=self.buffer,
            input_processors=[BeforeInput("search: ")],
            focusable=True,
            key_bindings=self._get_key_bindings(),
        )
        self._on_start_search = on_start_search

        self.window = Window(height=1, content=self.control)

    def _get_key_bindings(self) -> KeyBindings:
        kb = KeyBindings()

        # @kb.add("escape", eager=True)
        # def _(event) -> None:
        #     self.window
        #     get_app().layout.focus_previous()

        #     _logger.debug("escaped")

        @kb.add("enter")
        def _(event) -> None:
            self._on_start_search(self.buffer.text)

        return kb

    def __pt_container__(self) -> Container:
        return self.window


ThreadedCompleter


class FileTreeViewer:
    """Main application class for the file tree viewer."""

    _root_node: TreeNode
    _focussed_node: TreeNode | Node

    def __init__(self, settings: Settings):
        self.root_path = settings.root_folder.resolve()
        self._settings = settings
        self._root_node = self._focussed_node = self._init_root_node()
        self._search_visible = False

        self._search_input = Search(self.find)

        text_control = FormattedTextControl(
            text=self._update_display,
            focusable=True,
            # key_bindings=self._setup_key_bindings(),
        )

        main_window = ScrollablePane(Window(content=text_control, wrap_lines=True))

        # Create search footer
        search_footer = ConditionalContainer(
            content=self._search_input,
            filter=Condition(lambda: self._search_visible),
        )

        self._container = HSplit(
            [main_window, search_footer], key_bindings=self._setup_key_bindings()
        )

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

        @kb.add("up", filter=Condition(lambda: not self._search_visible))
        def move_up(event):
            self._focussed_node.focus(-1)

        @kb.add("down", filter=Condition(lambda: not self._search_visible))
        def move_down(event):
            self._focussed_node.focus(1)

        @kb.add("right", filter=Condition(lambda: not self._search_visible))
        def enter_node(event):
            self._focussed_node.enter()

        @kb.add("left", filter=Condition(lambda: not self._search_visible))
        def exit_node(event):
            self._focussed_node.exit()

        @kb.add("q", filter=Condition(lambda: not self._search_visible))
        @kb.add("c-c")
        def quit_app(event):
            event.app.exit()

        @kb.add("/", filter=Condition(lambda: not self._search_visible))
        def start_search(event):
            """Show search input widget."""
            self._search_visible = True
            get_app().layout.focus(self._search_input)

        @kb.add(
            "escape",
            filter=Condition(lambda: self._search_visible),
            eager=True,
        )
        def cancel_search(event):
            """Hide search input widget."""
            _logger.debug("escaped")
            self._search_visible = False
            get_app().layout.focus_previous()

        #     self._refresh_tree()

        return kb

    def bubble(self, event: str, event_data: object) -> None:
        if event == "focus_changed":
            if event_data is None:
                return
            self._focussed_node.focussed = False
            self._focussed_node = event_data
            self._focussed_node.focussed = True

    def find(self, str_to_find: str) -> None:
        for nd in self._root_node.all_nodes():
            nd.find(str_to_find)

    def _update_display(self) -> FormattedText:
        """Update the display buffer with current tree state."""

        # nodes = list((node.render() for node in self._root_node.full_tree()))

        def render() -> Generator[tuple[str, str], None, None]:
            for node in self._root_node.full_tree():
                if node.focussed:
                    yield ("[SetCursorPosition]", "")
                yield from node.render()

        nodes = (node for node in render())

        _logger.debug(nodes)

        return FormattedText(nodes)

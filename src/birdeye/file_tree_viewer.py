"""
A full screen file tree viewer using Textual.
Navigate with arrow keys, expand/collapse with Enter or Space.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import pygit2
from rich.style import Style
from rich.text import Text
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Input, Tree
from textual.widgets._tree import TOGGLE_STYLE
from textual.widgets.tree import TreeNode

from birdeye._nodes import NodeMeta, populate_tree_node

_logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class Settings:
    root_folder: Path
    use_git_ignore: bool = True


class BirdeyeTree(Tree[NodeMeta]):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("left", "collapse_or_parent", "Exit", show=False),
        Binding("right", "enter", "Select", show=False),
        Binding("up", "cursor_up", "Cursor Up", show=False),
        Binding("down", "cursor_down", "Cursor Down", show=False),
    ]

    def action_collapse_or_parent(self) -> None:
        node = self.get_node_at_line(self.cursor_line)
        if node is None:
            return
        if node.allow_expand and node.is_expanded:
            node.collapse()
        else:
            self.move_cursor(node.parent)

    def action_enter(self) -> None:
        node = self.get_node_at_line(self.cursor_line)
        if node is None:
            return

        if node.allow_expand:
            if node.is_collapsed:
                node.expand()

    def render_label(
        self, node: TreeNode[NodeMeta], base_style: Style, style: Style
    ) -> Text:
        def _markup_name() -> Text:
            """Generate a styled representation of the name property.

            includes highlight, find-match etc.
            """

            node_label = node._label.copy()

            if find_match := node.data["find_match"]:
                node_label.stylize(style)
                node_label.stylize(
                    Style(bgcolor="yellow"),
                    start=find_match[0],
                    end=find_match[1],
                )
                return node_label
            else:
                node_label.stylize(style)
                return node_label

        if node._allow_expand:
            prefix = (
                self.ICON_NODE_EXPANDED if node.is_expanded else self.ICON_NODE,
                base_style + TOGGLE_STYLE,
            )
        else:
            prefix = ("", base_style)

        text = Text.assemble(prefix, _markup_name())
        return text

    def move_to_next_highlight(self) -> None:
        for nd in self._tree_lines[self.cursor_line + 1 :]:
            if nd.node.data["find_match"]:
                self.move_cursor(nd.node)
                break

    def move_to_previous_highlight(self) -> None:
        for nd in reversed(self._tree_lines[: self.cursor_line]):
            if nd.node.data["find_match"]:
                self.move_cursor(nd.node)
                break


class FileTreeViewer(Vertical):
    """Main widget for the file tree viewer."""

    BINDINGS = [
        ("slash", "start_search", "Search"),
        ("n", "next_highlight", "Next highlight"),
        ("p", "previous_highlight", "Previous highlight"),
    ]

    # reactive attribute to control visibility of the highlight commands.
    found_matches = reactive(False, bindings=True)

    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings
        self.root_path = settings.root_folder.resolve()

        # Determine git repo if available
        if (self.root_path / ".git").exists():
            self._git_repo = pygit2.Repository(self.root_path)
        else:
            self._git_repo = None

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Check whether certain actions should be visible."""
        if action == "next_highlight" and not self.found_matches:
            return False

        if action == "previous_highlight" and not self.found_matches:
            return False

        return True

    def compose(self):
        self._tree = BirdeyeTree(
            str(self.root_path), data=NodeMeta(find_match=None, path=self.root_path)
        )
        self._tree.root.expand()

        # Populate the root node
        populate_tree_node(
            self._tree.root,
            self.root_path,
            use_gitignore=self._settings.use_git_ignore,
            git_repo=self._git_repo,
        )

        yield self._tree
        yield Input(placeholder="Search...", id="search-input")
        yield Footer()

    def on_mount(self) -> None:
        self._tree.focus()
        self.query_one("#search-input", Input).display = False

    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """Handle tree node expansion - lazy load children."""
        node: TreeNode[NodeMeta] = event.node
        path = node.data["path"]

        if path and path.is_dir() and not node.children:
            populate_tree_node(
                node,
                path,
                use_gitignore=self._settings.use_git_ignore,
                git_repo=self._git_repo,
            )

    def action_start_search(self) -> None:
        """Show and focus the search input."""
        search_input = self.query_one("#search-input", Input)
        search_input.display = True
        search_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search submission."""
        search_term = event.value
        if search_term:
            self._find_in_tree(search_term)

        event.input.display = False
        self._tree.focus()

    def _find_in_tree(self, search_term: str) -> None:
        """Find and highlight nodes matching the search term."""
        self.found_matches = False

        def load_children(node: TreeNode[NodeMeta]) -> None:
            if node.data["path"].is_dir() and not node.children:
                populate_tree_node(
                    node,
                    node.data["path"],
                    use_gitignore=self._settings.use_git_ignore,
                    git_repo=self._git_repo,
                )
            for child in node.children:
                load_children(child)

        def search_node(node: TreeNode[NodeMeta]) -> None:
            """Recursively search and expand nodes. Returns True if match found in subtree."""

            lbl = node.label.plain

            if (match_idx := lbl.find(search_term)) >= 0:
                self.found_matches = True
                node.data["find_match"] = (match_idx, match_idx + len(search_term))
                if node.allow_expand:
                    node.expand()

                prnt = node.parent
                while prnt:
                    prnt.expand()
                    prnt = prnt.parent
            else:
                node.data["find_match"] = None

            for child in node.children:
                search_node(child)

        load_children(self._tree.root)
        search_node(self._tree.root)

    def action_next_highlight(self) -> None:
        self._tree.move_to_next_highlight()

    def action_previous_highlight(self) -> None:
        self._tree.move_to_previous_highlight()

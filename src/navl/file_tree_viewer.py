"""
A full screen file tree viewer using prompt_toolkit.
Navigate with arrow keys, expand/collapse with Enter or Space.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Iterable, Optional, Tuple

import pygit2
from prompt_toolkit.data_structures import Point
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style


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


_INDENT = 4


class Node:
    _ICON = "📄"

    def __init__(self, path: Path, *, parent: TreeNode) -> None:
        self.path = path
        self.name = path.name
        self.parent = parent
        self.selected = False

    def select_next(self, current: Node | TreeNode) -> bool:
        if self.parent.select_next(self):
            self.selected = False
        return True


class TreeNode:
    """Represents a node in the file tree."""

    _ICON = "📂"

    def selected_next(self, current: None | TreeNode) -> bool:
        # todo:need to do this better.
        if current is self:
            # this Tree node is currently selected one. So we now select the first child as selected.
            self.children[0]

    def __init__(
        self,
        path: Path,
        *,
        level: int,
        parent: TreeNode | None,
        expanded: bool = False,
        use_gitignore: bool = True,
        git_repo: pygit2.Repository | None,
    ):
        self._level = level
        self.path = path
        self.name = path.name
        self.parent = parent
        self.expanded = expanded
        self.use_gitignore = use_gitignore
        self._git_repo = git_repo

        self._children: tuple[TreeNode | Node, ...] | None = None

        # todo: use this
        self.active = False
        # True when a child of this items is selected.

        self.selected = False
        # True when this item has focus / is selected.

    @property
    def children(self) -> tuple[TreeNode | Node, ...]:
        """Load child nodes if this is a directory."""
        if self._children is None:
            if self._git_repo and self.use_gitignore:
                children = use_gitignore(self._git_repo, self.path)
            else:
                children = self.path.iterdir()

            def get_children() -> Generator[TreeNode | Node, None, None]:
                for child in children:
                    if child.is_dir():
                        yield TreeNode(
                            child,
                            parent=self,
                            expanded=False,
                            use_gitignore=self.use_gitignore,
                            git_repo=self._git_repo,
                        )
                    else:
                        yield Node(child.name)

            self._children = tuple(get_children())
        return self._children

    def toggle_expanded(self):
        """Toggle the expanded state of this node."""
        if not self.expanded:
            self.load_children()
        self.expanded = not self.expanded


class FileTreeViewer:
    """Main application class for the file tree viewer."""

    visible_nodes: tuple[TreeNode, ...]

    def __init__(self, settings: Settings):
        self.root_path = settings.root_folder.resolve()
        self._settings = settings
        self._selected_index = 0

        self.style = Style.from_dict(
            {
                "selected": "bg:#ffffff fg:#000000",  # White background, black text
                "header": "bold",
                "separator": "fg:#888888",
                "footer": "fg:#888888",
            }
        )

        self.root_node = self._init_root_node()
        text_control = FormattedTextControl(
            text=self._update_display,
            focusable=True,
            key_bindings=self._setup_key_bindings(),
            get_cursor_position=self._get_cursor_position,
        )

        self._window = Window(content=text_control, wrap_lines=False)

    def _get_cursor_position(self) -> Point:
        pt = Point(0, self.selected_index)
        return pt

    def __pt_container__(self) -> Window:
        return self._window

    @property
    def selected_index(self) -> int:
        return self._selected_index

    @selected_index.setter
    def selected_index(self, idx: int) -> None:
        self._selected_index = idx

    def _init_root_node(self) -> TreeNode:
        if (self.root_path / ".git").exists():
            repository = pygit2.Repository(self.root_path)
        else:
            repository = None

        root_node = TreeNode(
            self.root_path,
            parent=None,
            expanded=True,
            use_gitignore=self._settings.use_git_ignore,
            git_repo=repository,
        )
        root_node.load_children()
        return root_node

    def _setup_key_bindings(self) -> KeyBindings:
        """Setup key bindings for navigation."""
        kb = KeyBindings()

        @kb.add("up")
        def move_up(event):
            if self.selected_index > 0:
                self.selected_index -= 1

        @kb.add("down")
        def move_down(event):
            if self.selected_index < len(self.visible_nodes) - 1:
                self.selected_index += 1

        @kb.add("enter")
        def select_and_exit(event):
            if self.visible_nodes:
                node = self.visible_nodes[self.selected_index]
                event.app.exit(str(node.path))

        @kb.add("space")
        def toggle_node(event):
            if self.visible_nodes:
                node = self.visible_nodes[self.selected_index]
                node.toggle_expanded()

        @kb.add("right")
        def expand_node(event):
            if self.visible_nodes:
                node = self.visible_nodes[self.selected_index]
                # todo: this should not be here
                if node.is_directory and not node.expanded:
                    node.toggle_expanded()

        @kb.add("left")
        def collapse_node(event):
            if self.selected_index < len(self.visible_nodes):
                node = self.visible_nodes[self.selected_index]
                if node.is_directory and node.expanded:
                    node.toggle_expanded()
                elif node.parent:
                    # Move to parent
                    parent_index = self.visible_nodes.index(node.parent)
                    self.selected_index = parent_index

        @kb.add("q")
        @kb.add("c-c")
        def quit_app(event):
            event.app.exit()

        @kb.add("r")
        def refresh(event):
            self._refresh_tree()

        return kb

    def _refresh_tree(self):
        """Refresh the entire tree."""

        expanded_paths = set(FileTreeViewer._collect_expanded_paths(self.root_node))

        self.root_node = self._init_root_node()

        self._restore_expanded_state(self.root_node, expanded_paths)

        self.selected_index = 0

    @staticmethod
    def _collect_expanded_paths(node: TreeNode) -> Iterable[Path]:
        """Collect all expanded paths for restoration after refresh."""
        if node.expanded:
            yield node.path
        for child in node.children:
            yield from FileTreeViewer._collect_expanded_paths(child)

    def _restore_expanded_state(self, node: TreeNode, expanded_paths: set[Path]):
        """Restore expanded state after refresh."""
        if node.path in expanded_paths:
            node.expanded = True
            node.load_children()
            for child in node.children:
                self._restore_expanded_state(child, expanded_paths)

    def _collect_visible_nodes(
        self, node: TreeNode, depth: int = 0
    ) -> Generator[TreeNode, None, None]:
        """Collect all visible nodes for display."""

        yield node

        if node.expanded:
            for child in node.children:
                yield from self._collect_visible_nodes(child, depth + 1)

    def _get_node_depth(self, node: TreeNode) -> int:
        """Get the depth of a node in the tree."""
        depth = 0
        current = node.parent
        while current:
            depth += 1
            current = current.parent
        return depth

    def _format_node(self, node: TreeNode, is_selected: bool) -> Tuple[str, str]:
        """Format a node for display, returning (text, style)."""
        depth = self._get_node_depth(node)
        indent = "  " * depth

        name = node.get_name()
        line = f"{indent}{icon}{name}"

        if is_selected:
            line = f"> {line}"
            return (line, "selected")
        else:
            line = f"  {line}"
            return (line, "")

    def _update_display(self) -> FormattedText:
        """Update the display buffer with current tree state."""
        self.visible_nodes = tuple(self._collect_visible_nodes(self.root_node))

        # Ensure selected index is valid
        if self.selected_index >= len(self.visible_nodes):
            self.selected_index = len(self.visible_nodes) - 1
        if self.selected_index < 0:
            self.selected_index = 0

        formatted_content = []

        for i, node in enumerate(self.visible_nodes):
            is_selected = i == self.selected_index
            text, style_class = self._format_node(node, is_selected)
            if style_class:
                formatted_content.append((f"class:{style_class}", text))
            else:
                formatted_content.append(("", text))
            formatted_content.append(("", "\n"))

        return FormattedText(formatted_content)

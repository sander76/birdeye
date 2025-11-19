"""
A full screen file tree viewer using prompt_toolkit.
Navigate with arrow keys, expand/collapse with Enter or Space.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Generator, Iterable, List, Optional, Tuple

from gitignore_parser import parse_gitignore
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


class TreeNode:
    """Represents a node in the file tree."""

    def __init__(
        self,
        path: Path,
        *,
        gitignore_parser: Callable[[Path], bool] | None,
        parent: Optional["TreeNode"],
        expanded: bool = False,
    ):
        self.path = path
        self.gitignore_parser = gitignore_parser
        self.parent = parent
        self.children: List["TreeNode"] = []
        self.expanded = expanded
        self.is_directory = path.is_dir()

    def get_name(self) -> str:
        """Get the display name for this node."""
        return self.path.name if self.path.name else str(self.path)

    def load_children(self):
        """Load child nodes if this is a directory."""
        if not self.is_directory or self.children:
            return

        children = self.path.iterdir()
        if self.gitignore_parser:
            children = (child for child in children if not self.gitignore_parser(child))

        self.children = tuple(
            (
                TreeNode(child, gitignore_parser=self.gitignore_parser, parent=self)
                for child in sorted(children)
            )
        )

    def toggle_expanded(self):
        """Toggle the expanded state of this node."""
        if self.is_directory:
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
        if self._settings.use_git_ignore:
            gitignore_file = self.root_path / ".gitignore"
            gitignore_parser = (
                parse_gitignore(gitignore_file) if gitignore_file.exists() else None
            )
        else:
            gitignore_parser = None

        root_node = TreeNode(
            self.root_path,
            gitignore_parser=gitignore_parser,
            expanded=True,
            parent=None,
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

        if node.is_directory:
            if node.expanded:
                icon = "📂 "
            else:
                icon = "📁 "
        else:
            icon = "📄 "

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

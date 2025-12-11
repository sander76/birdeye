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
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.scrollable_pane import ScrollablePane

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


class BaseNode:
    """Base class for all node types with common comparison functionality."""

    _same_level_down: TreeNode | Node | None = None
    _same_level_up: TreeNode | Node | None = None
    _child_down: TreeNode | Node | None = None

    def __init__(
        self,
        path: Path,
        level: int,
    ):
        self.path = path
        self.name = path.name
        self.focussed: bool = False
        self._level = level

    def __lt__(self, other) -> bool:
        """Enable sorting by name property."""
        return self.name < other.name

    def __le__(self, other) -> bool:
        """Enable less than or equal comparison."""
        return self.name <= other.name

    def __gt__(self, other) -> bool:
        """Enable greater than comparison."""
        return self.name > other.name

    def __ge__(self, other) -> bool:
        """Enable greater than or equal comparison."""
        return self.name >= other.name

    def __ne__(self, other) -> bool:
        """Enable not equal comparison."""
        return not self.name == other.name

    def _get_style(self) -> str:
        if self.focussed:
            return "bg:#ffffff fg:#000000"
        return ""

    def set_expanded(self, value: bool) -> None:
        raise NotImplementedError

    def render(self) -> tuple[str, str]:
        res = self._get_style(), f"{' ' * self._level} {self._ICON} {self.name}\n"
        # _logger.debug(f"Render a node: {res}")

        return res

    def focus(self, direction: Literal[-1, 1]) -> Node | TreeNode:
        new_focussed = self.up if direction == -1 else self.down

        if new_focussed is None:
            return self
        else:
            self.focussed = False
            new_focussed.focussed = True
            return new_focussed


class Node(BaseNode):
    _ICON = "📄"

    def __init__(
        self,
        path: Path,
        *,
        parent: TreeNode,
        level: int,
    ) -> None:
        super().__init__(path, level=level)
        self.parent = parent

    @property
    def down(self) -> Node | TreeNode | None:
        # self.focussed = False
        new_focussed = self._same_level_down
        return new_focussed

    @property
    def up(self) -> Node | TreeNode | None:
        # self.focussed = False
        new_focussed = self._same_level_up
        return new_focussed

    def full_tree(self) -> Generator[Node, None, None]:
        yield self

    def set_expanded(self, value: bool):
        pass


class TreeNode(BaseNode):
    """Represents a node in the file tree."""

    _ICON = "📂"
    _children: tuple[TreeNode | Node, ...] | None = None
    last_child: TreeNode | Node | None = None

    def __init__(
        self,
        path: Path,
        *,
        parent: TreeNode | None,
        level: int,
        # expanded: bool = False,
        use_gitignore: bool = True,
        git_repo: pygit2.Repository | None,
    ):
        super().__init__(path, level=level)
        self._level = level
        self.parent = parent
        if parent is None:
            self._same_level_down = None

        self.use_gitignore = use_gitignore

        self._git_repo = git_repo
        self.set_expanded(True if parent is None else False)

    def set_expanded(self, value: bool):
        if value:
            self.load_children()
            if self._same_level_down:
                self._same_level_down._same_level_up = self.last_child
        else:
            if self._same_level_down:
                self._same_level_down._same_level_up = self

        self._expanded = value

    @property
    def down(self) -> Node | TreeNode | None:
        """The Node or TreeNode below this node."""
        if self._expanded:
            new_focussed = self._child_down
        else:
            new_focussed = self._same_level_down

        return new_focussed

    @property
    def up(self) -> Node | TreeNode | None:
        """The Node or TreeNode above this node."""
        new_focussed = self._same_level_up

        return new_focussed

    # def render(self) -> tuple[str, str]:
    #     _logger.debug("Render a treenode")
    #     return self._get_style(), f"{self._ICON} {self.name}\n"

    def load_children(self) -> None:
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
                            level=self._level + 1,
                            use_gitignore=self.use_gitignore,
                            git_repo=self._git_repo,
                        )

                    else:
                        yield Node(child, parent=self, level=self._level + 1)

            up = self
            for idx, child in enumerate(sorted(get_children())):
                if idx == 0:
                    up._child_down = child
                else:
                    up._same_level_down = child
                child._same_level_up = up
                up = child
            child._same_level_down = self._same_level_down
            self.last_child = child
            self._children = True

    def full_tree(self) -> Generator[Node | TreeNode, None, None]:
        """All visible nodes/treenodes."""
        new = self
        yield new

        while new := new.down:
            yield new


class FileTreeViewer:
    """Main application class for the file tree viewer."""

    _root_node: TreeNode
    _selected_node: TreeNode | Node

    def __init__(self, settings: Settings):
        self.root_path = settings.root_folder.resolve()
        self._settings = settings
        self._root_node = self._selected_node = self._init_root_node()

        text_control = FormattedTextControl(
            text=self._update_display,
            focusable=True,
            key_bindings=self._setup_key_bindings(),
        )

        # self._window = Window(content=text_control, wrap_lines=False)
        self._window = ScrollablePane(Window(content=text_control, wrap_lines=True))

    def __pt_container__(self) -> Window:
        return self._window

    def _init_root_node(self) -> TreeNode:
        _logger.debug("init root")
        if (self.root_path / ".git").exists():
            repository = pygit2.Repository(self.root_path)
        else:
            repository = None

        root_node = TreeNode(
            self.root_path,
            parent=None,
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
            self._selected_node = self._selected_node.focus(-1)

        @kb.add("down")
        def move_down(event):
            self._selected_node = self._selected_node.focus(1)

        @kb.add("right")
        def expand_node(event):
            self._selected_node.set_expanded(value=True)

        @kb.add("left")
        def collapse_node(event):
            self._selected_node.set_expanded(value=False)

        @kb.add("q")
        @kb.add("c-c")
        def quit_app(event):
            event.app.exit()

        # @kb.add("r")
        # def refresh(event):
        #     self._refresh_tree()

        return kb

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

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Generator, Literal

import pygit2
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.scrollable_pane import ScrollablePane

if TYPE_CHECKING:
    from birdeye.file_tree_viewer import FileTreeViewer
_logger = logging.getLogger(__name__)


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
    """Next node on the same level as this node.
    
    .
    ├── this-node
    │   ├── child_node
    │   └── other_child_node
    └── other_node    <------------same_level_down of "this-node"
    """

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

    def enter(self) -> None:
        raise NotImplementedError

    def exit(self) -> None:
        raise NotImplementedError

    def render(self) -> tuple[str, str]:
        res = self._get_style(), f"{' ' * self._level} {self._ICON} {self.name}\n"
        # _logger.debug(f"Render a node: {res}")

        return res

    # def focus(self, direction: Literal[-1, 1]) -> Node | TreeNode:
    #     new_focussed = self.up if direction == -1 else self.down

    #     if new_focussed is None:
    #         return self
    #     else:
    #         self.focussed = False
    #         new_focussed.focussed = True
    #         return new_focussed


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

    def enter(self) -> None:
        return

    def exit(self) -> None:
        self.parent.bubble(event="focus_changed", event_data=self.parent)

    def focus(self, direction: Literal[-1, 1]) -> None:
        new_focussed = self.up if direction == -1 else self.down

        self.parent.bubble(event="focus_changed", event_data=new_focussed)

    def all_nodes(self) -> Generator[Node | TreeNode, None, None]:
        yield self
        if self.down:
            yield from self.down.all_nodes()


class TreeNode(BaseNode):
    """Represents a node in the file tree."""

    _ICON = "📂"
    _children: tuple[TreeNode | Node, ...] | None = None
    last_child: TreeNode | Node | None = None
    _expanded = False

    def __init__(
        self,
        path: Path,
        *,
        parent: TreeNode | FileTreeViewer,
        level: int,
        # expanded: bool = False,
        use_gitignore: bool = True,
        git_repo: pygit2.Repository | None,
    ):
        super().__init__(path, level=level)
        self._level = level
        self.parent = parent

        self.use_gitignore = use_gitignore

        self._git_repo = git_repo
        if level == 0:
            # dealing with the root node here.
            self._same_level_down = None
            self.focussed = True
            self.enter()

    def bubble(self, event: str, event_data: object) -> None:
        if event == "match_found":
            self._expanded = True
        self.parent.bubble(event, event_data)

    def match(self, str_to_match: str) -> None:
        if self.name.find(str_to_match) >= 0:
            # todo: highlight the match
            self.parent.bubble(event="match_found", event_data=self)

    def focus(self, direction: Literal[-1, 1]) -> None:
        new_focussed = self.up if direction == -1 else self.down

        self.parent.bubble(event="focus_changed", event_data=new_focussed)

    def enter(self) -> None:
        self.load_children()
        if self._same_level_down:
            self._same_level_down._same_level_up = self.last_child
        self._expanded = True

    def exit(self):
        # exiting a treenode can mean two things.
        # 1. this node is expanded, so we collapse it.
        # 2. this node is not expanded, so we'll treat it as
        #    a plain node (no folder) and we'll jump to the parent

        if self._expanded:
            if self._same_level_down:
                self._same_level_down._same_level_up = self
            self._expanded = False
        else:
            self.bubble("focus_changed", self.parent)

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

    def all_nodes(self) -> Generator[Node | TreeNode, None, None]:
        """All nodes, regardless of visibility."""
        self.load_children()

        yield self

        if self._child_down:
            yield from self._child_down.all_nodes()

        elif self._same_level_down:
            yield from self._same_level_down.all_nodes()

    def full_tree(self) -> Generator[Node | TreeNode, None, None]:
        """All visible nodes/treenodes."""
        new = self
        yield new

        while new := new.down:
            yield new

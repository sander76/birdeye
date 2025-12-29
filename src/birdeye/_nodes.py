from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Generator, Literal

import pygit2

from birdeye._events import FOCUS_CHANGED, MATCH_FOUND

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

    _ICON = "📄"

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

    def __init__(self, path: Path, level: int, parent: FileTreeViewer | TreeNode):
        self.path = path
        self.name = path.name
        self.parent = parent

        self._level = level

        self.focussed: bool = False
        # If this node matches a search string this defines start/stop indices
        # of the search string.
        self.match_find: tuple[int, int] | None = None

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

    def enter(self) -> None:
        raise NotImplementedError

    def exit(self) -> None:
        raise NotImplementedError

    def render(self) -> tuple[tuple[str, str], ...]:
        def _markup_name() -> Generator[tuple[str, str], None, None]:
            """Generate a styled representation of the name property.

            includes highlight, find-match etc.
            """

            # style for non-highlighted text.
            default_style = "class:node_focussed" if self.focussed else ""

            if self.match_find:
                # this node matches a find string.
                if self.match_find[0] > 0:
                    yield (
                        default_style,  # no match. use default.
                        self.name[0 : self.match_find[0]],
                    )
                yield (
                    "class:node_find_match",  # the style for the match.
                    self.name[self.match_find[0] : self.match_find[1]],
                )
                if len(self.name) > self.match_find[1]:
                    yield (
                        default_style,
                        self.name[self.match_find[1] :],
                    )
            else:
                yield (default_style, self.name)

        return (
            ("", f"{' ' * self._level}"),
            ("", self._ICON),
            *_markup_name(),
            ("", "\n"),
        )

    def find(self, str_to_match: str) -> None:
        if (match_idx := self.name.find(str_to_match)) >= 0:
            self.match_find = (match_idx, match_idx + len(str_to_match))
            self.parent.bubble(event=MATCH_FOUND, event_data=self)
        else:
            self.match_find = None


class Node(BaseNode):
    _ICON = "📄"

    def __init__(self, path: Path, *, parent: TreeNode, level: int) -> None:
        super().__init__(path, level=level, parent=parent)

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
        self.parent.bubble(event=FOCUS_CHANGED, event_data=self.parent)

    def focus(self, direction: Literal[-1, 1]) -> None:
        new_focussed = self.up if direction == -1 else self.down

        self.parent.bubble(event=FOCUS_CHANGED, event_data=new_focussed)

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
        use_gitignore: bool = True,
        git_repo: pygit2.Repository | None = None,
    ):
        super().__init__(path, level=level, parent=parent)
        self._level = level

        self.use_gitignore = use_gitignore

        self._git_repo = git_repo
        if level == 0:
            # dealing with the root node here.
            self._same_level_down = None
            self.focussed = True
            self.enter()

    def bubble(self, event: str, event_data: object) -> None:
        if event == MATCH_FOUND:
            self._expanded = True
        self.parent.bubble(event, event_data)

    def focus(self, direction: Literal[-1, 1]) -> None:
        new_focussed = self.up if direction == -1 else self.down

        self.parent.bubble(event=FOCUS_CHANGED, event_data=new_focussed)

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
            self.bubble(FOCUS_CHANGED, self.parent)

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

            up: Node | TreeNode = self

            child: TreeNode | Node | None = None

            for idx, child in enumerate(sorted(get_children())):
                if idx == 0:
                    up._child_down = child
                else:
                    up._same_level_down = child
                child._same_level_up = up
                up = child
            if child is not None:
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

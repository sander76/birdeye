from __future__ import annotations

import logging
from pathlib import Path
from typing import Generator, TypedDict

import pygit2
from textual.widgets.tree import TreeNode

_logger = logging.getLogger(__name__)


def use_gitignore(
    repo: pygit2.Repository, root_folder: Path
) -> Generator[Path, None, None]:
    """Check whether any child inside the root_folder is being git-ignored."""
    as_path = Path(repo.workdir)

    for child in root_folder.iterdir():
        rel_path = str(child.relative_to(as_path))
        if repo.path_is_ignored(rel_path):
            continue
        yield child


class NodeMeta(TypedDict):
    find_match: tuple[int, int] | None
    path: Path


def populate_tree_node(
    node: TreeNode[NodeMeta],
    path: Path,
    *,
    use_gitignore: bool = True,
    git_repo: pygit2.Repository | None = None,
) -> None:
    """Populate a Textual TreeNode with children from the filesystem."""
    if not path.is_dir():
        return

    # Get children, respecting gitignore if applicable
    if git_repo and use_gitignore:
        from birdeye._nodes import use_gitignore as get_gitignore_children

        children = list(get_gitignore_children(git_repo, path))
    else:
        children = list(path.iterdir())

    # Sort: directories first, then files, both alphabetically
    dirs = sorted([c for c in children if c.is_dir()], key=lambda p: p.name.lower())
    files = sorted([c for c in children if c.is_file()], key=lambda p: p.name.lower())

    for child_path in dirs:
        child_node = node.add(
            child_path.name, data=NodeMeta(find_match=None, path=child_path)
        )
        child_node.allow_expand = True

    for child_path in files:
        node.add_leaf(child_path.name, data=NodeMeta(find_match=None, path=child_path))

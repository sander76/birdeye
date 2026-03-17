# AGENTS.md - Coding Agent Instructions for birdeye

## Project Overview

birdeye is a Python terminal-based file tree navigator built with Textual (TUI framework).
It provides interactive directory navigation with expand/collapse, search, and gitignore filtering.

## Technology Stack

- **Language**: Python 3.13+
- **Package Manager**: uv
- **TUI Framework**: Textual (>=0.79)
- **Git Integration**: pygit2 (>=1.19)
- **Task Runner**: Nox
- **Linting/Formatting**: Ruff
- **Type Checking**: mypy
- **Testing**: pytest, pytest-asyncio

## Build/Lint/Test Commands

```bash
# Install and run
uv sync
uv run birdeye [path]

# Testing
nox -s tests                              # Run all tests with coverage
uv run pytest tests/test_cli.py                  # Run specific test file
uv run pytest tests/test_cli.py::test_parse_args # Run single test by name
uv run pytest -k "gitignore"                     # Run tests matching pattern

# Linting and formatting
nox -s quality                            # Run all quality checks
uv run ruff check src tests --fix                # Lint and auto-fix
uv run ruff format src tests                     # Format code
uv run mypy src                                  # Type checking

# All checks
nox                                       # Run both tests and quality
```

## Project Structure

```
src/birdeye/
├── _events.py            # Event name constants
├── _nodes.py             # Tree node utilities, gitignore filtering
├── birdeye.py            # Main BirdeyeApp (Textual App)
├── cli.py                # CLI entry point, argument parsing
└── file_tree_viewer.py   # Core FileTreeViewer widget

tests/
├── test_birdeye.py           # App-level tests
├── test_cli.py               # CLI argument parsing tests
└── test_file_tree_viewer.py  # Widget/component tests
```

## Code Style Guidelines

### Import Organization

let ruff handle this.

### Type Hints

- Always use `from __future__ import annotations` at module top
- Use modern union syntax: `str | None` (not `Optional[str]`)
- Use TypedDict for structured dictionaries
- Annotate all function parameters and return types

```python
from __future__ import annotations
from typing import ClassVar, TypedDict

class NodeMeta(TypedDict):
    path: Path
    is_dir: bool

def get_node(path: Path) -> NodeMeta | None: ...
```

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Files | snake_case | `file_tree_viewer.py` |
| Private modules | underscore prefix | `_nodes.py` |
| Classes | PascalCase | `FileTreeViewer` |
| Functions/Methods | snake_case | `populate_tree_node` |
| Constants | UPPER_CASE | `MATCH_FOUND` |
| Private attributes | underscore prefix | `_settings` |

### Data Classes

Use `slots=True` and `frozen=True` for immutable structures:

```python
@dataclass(slots=True, frozen=True)
class Settings:
    root_folder: Path
    use_git_ignore: bool = True
```

### Logging

```python
_logger = logging.getLogger(__name__)
```

### Error Handling

- Prefer early returns for guard clauses
- Use `type: ignore[error-code]` sparingly with specific codes

```python
def process_node(node: TreeNode | None) -> None:
    if node is None:
        return
    # proceed with node...
```

### Textual-Specific Patterns

```python
class MyWidget(Widget):
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("enter", "select", "Select"),
    ]
    found_matches = reactive(False, bindings=True)

    def compose(self) -> ComposeResult:
        yield Tree("root")

    def action_select(self) -> None:  # prefix with action_
        ...
```

## Testing Patterns

### Async Tests with Textual

```python
@pytest.mark.asyncio
async def test_navigation(settings_no_git: Settings):
    app = create_app(settings_no_git)
    async with app.run_test() as pilot:
        await pilot.press("down")
        await pilot.pause()
        # assertions here
```

### Fixtures and Mocking

```python
@pytest.fixture
def tmp_path_with_files(tmp_path):
    (tmp_path / "file1.txt").touch()
    return tmp_path

def test_with_mock(monkeypatch):
    monkeypatch.setattr(file_tree_viewer.subprocess, "run", Mock())
```

### Debugging Tests

```bash
uv run pytest -s tests/test_file.py  # Show print output
uv run pytest --tb=long              # Full traceback
uv run pytest -x                     # Stop on first failure
```

## Pre-commit Hooks

Uses ruff-check (with --fix) and ruff-format. Install with: `pre-commit install`

## CI/CD

GitHub Actions (`release.yml`) builds and publishes to PyPI on push to main.

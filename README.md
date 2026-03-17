# birdeye

A terminal-based file tree navigator.

## Overview

birdeye is an interactive file tree viewer that allows you to navigate directory structures directly from your terminal.

## Features

- **Interactive Navigation**: Use arrow keys to move through the file tree
- **Expand/Collapse**: Toggle directories to show or hide their contents
- **Search**: press '/' to enter a search term and have matches auto expand and highlighted. 

## Installation

`pip install birdeye`

or better use `pipx` or `uv tool` and you'll have a birdeye command available in your prompt.

## Configuration

birdeye looks for configuration files in your system's config directory:

- **Linux**: `~/.config/birdeye/`
- **macOS**: `~/Library/Application Support/birdeye/`
- **Windows**: `%APPDATA%\birdeye\`

### File Openers

Create `opener.json` to customize which program opens each file type when you press Enter:

```json
{
  ".py": "code",
  ".toml": "code",
  ".md": "typora"
}
```

If the file doesn't exist, birdeye defaults to opening `.py` and `.toml` files with `code`, and all other files with `open`.


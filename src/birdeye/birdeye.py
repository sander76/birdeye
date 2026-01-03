from textual.app import App, ComposeResult

from birdeye.file_tree_viewer import FileTreeViewer, Settings


class BirdeyeApp(App):
    """A Textual app for browsing file trees."""

    CSS = """
    FileTreeViewer {
        height: 1fr;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings

    def compose(self) -> ComposeResult:
        yield FileTreeViewer(self._settings)


def app(settings: Settings) -> BirdeyeApp:
    return BirdeyeApp(settings)


def main(settings: Settings):
    """Main entry point."""
    _app = app(settings)
    _app.run()

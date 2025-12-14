# import traceback
import traceback
from dataclasses import dataclass
from pathlib import Path

from prompt_toolkit import Application
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.output.vt100 import Vt100_Output

from birdeye.file_tree_viewer import FileTreeViewer, Settings


def main(settings: Settings):
    """Main entry point."""
    import sys

    footer = (
        "Use ↑↓→← to navigate, Enter to select and exit, 'r' to refresh, 'q' to quit"
    )
    try:
        layout = Layout(
            HSplit(
                [
                    FileTreeViewer(settings),
                    Window(FormattedTextControl(text=footer)),
                ]
            )
        )
        app = Application[str](
            layout=layout,
            full_screen=True,
            # mouse_support=True,
            output=Vt100_Output.from_pty(sys.stderr),
        )

        res = app.run()
        if res:
            print(res)
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(e)
        traceback.print_exc()
        sys.exit(1)

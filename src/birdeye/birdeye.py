# import traceback
import asyncio
import traceback
from dataclasses import dataclass
from pathlib import Path

from prompt_toolkit import Application
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.output.vt100 import Vt100_Output

from birdeye.file_tree_viewer import FileTreeViewer, Settings

# import asyncio
# from prompt_toolkit.application import get_app

# class FileTreeViewer:
#     async def search_files_async(self, search_term):
#         """Run file search in background thread."""
#         result = await asyncio.to_thread(self._blocking_search, search_term)
#         # Update UI with results
#         self._update_search_results(result)

#     def _blocking_search(self, search_term):
#         """Blocking file search operation."""
#         import time
#         time.sleep(1)  # Simulate slow file system operation
#         # Your actual search logic here
#         return [f"result_{i}" for i in range(10)]

#     def start_search(self):
#         search_text = self.buffer.text
#         # Schedule the async search
#         asyncio.create_task(self.search_files_async(search_text))


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

        # https://github.com/prompt-toolkit/python-prompt-toolkit/issues/1901#issuecomment-2259116988
        app.timeoutlen = 0
        app.ttimeoutlen = 0

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

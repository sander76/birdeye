import asyncio

import pytest
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.output.base import DummyOutput

from birdeye import birdeye
from birdeye.file_tree_viewer import Settings


def birdeye_app(tmp_path, input_):
    app = birdeye.app(
        settings=Settings(root_folder=tmp_path, use_git_ignore=False),
        input_=input_,
        output=DummyOutput(),
    )

    return app


@pytest.mark.asyncio
async def test_short_cut_key_search(tmp_path):
    with create_pipe_input() as pipe_input:
        app = birdeye_app(tmp_path, pipe_input)

        pipe_input.send_text("/")
        pipe_input.send_text("abc")

        asyncio.create_task(app.run_async())
        # make sure the async app task has started.
        await asyncio.sleep(0.01)

        current = app.layout.current_window
        assert current.content.buffer.text == "abc"

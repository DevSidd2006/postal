from __future__ import annotations

import asyncio
import signal

from contextlib import contextmanager

from prompt_toolkit.input import create_input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from ui.tui import TUI

EXPAND_KEY = "c-o"


def build_key_bindings(tui: TUI) -> KeyBindings:

    bindings = KeyBindings()

    @bindings.add(EXPAND_KEY)
    def _(event) -> None:
        tui.toggle_expansion()

        app = event.app
        app.renderer.erase()
        app.renderer.reset()
        app._request_absolute_cursor_position()
        app._redraw()

    return bindings


@contextmanager
def turn_keys(tui: TUI, task: asyncio.Task):
    """Read keys for the length of a turn, falling back to SIGINT with no tty."""

    try:
        device = create_input()
    except Exception:
        loop = asyncio.get_running_loop()
        try:
            loop.add_signal_handler(signal.SIGINT, task.cancel)
        except (NotImplementedError, RuntimeError):
            pass
        try:
            yield
        finally:
            try:
                loop.remove_signal_handler(signal.SIGINT)
            except (NotImplementedError, RuntimeError):
                pass
        return

    def on_keys() -> None:
        for key_press in device.read_keys():
            if tui.feed_confirmation_key(key_press):
                continue
            if key_press.key == Keys.ControlO:
                tui.toggle_expansion()
            elif key_press.key == Keys.ControlC:
                task.cancel()

    tui.external_keys = True
    try:
        with device.raw_mode(), device.attach(on_keys):
            yield
    finally:
        tui.external_keys = False

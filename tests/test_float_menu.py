"""Tests for wrapping the prompt layout so the completions menu can float.

Wrapping the session's root container in a FloatContainer is what lets the
slash-command menu render over the prompt instead of being clipped.
"""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from prompt_toolkit import PromptSession
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import DummyInput
from prompt_toolkit.layout.containers import Float, FloatContainer
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.output import DummyOutput

from ui.repl.commands import SlashCommands
from ui.repl.completer import SlashCompleter


class FloatingMenuTests(unittest.TestCase):
    def setUp(self) -> None:
        # A dummy input/output keeps the session off the real terminal, so the
        # tests run the same under pytest, CI, or a plain shell.
        app_session = create_app_session(input=DummyInput(), output=DummyOutput())
        app_session.__enter__()
        self.addCleanup(app_session.__exit__, None, None, None)

        self.session: PromptSession[str] = PromptSession(
            completer=SlashCompleter(SlashCommands(Mock(), Mock())),
            complete_while_typing=True,
        )
        root = self.session.app.layout.container
        self.session.app.layout.container = FloatContainer(
            content=root,
            floats=[
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=8, scroll_offset=1),
                )
            ],
        )

    def test_root_becomes_a_float_container(self) -> None:
        self.assertIsInstance(self.session.app.layout.container, FloatContainer)

    def test_the_menu_float_tracks_the_cursor(self) -> None:
        (menu,) = self.session.app.layout.container.floats
        self.assertTrue(menu.xcursor)
        self.assertTrue(menu.ycursor)

    def test_the_original_layout_is_kept_as_content(self) -> None:
        container = self.session.app.layout.container
        self.assertNotIsInstance(container.content, FloatContainer)
        buffer_name = self.session.default_buffer.name
        self.assertIsNotNone(self.session.app.layout.get_buffer_by_name(buffer_name))


if __name__ == "__main__":
    unittest.main()

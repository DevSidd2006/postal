"""Tests for the layout a bare PromptSession gives us.

The completion menu only renders when the root container can hold floats, so
these lock in what prompt_toolkit builds by default -- see
tests/test_float_menu.py for the wrapping that makes the menu appear.
"""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from prompt_toolkit import PromptSession
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import DummyInput
from prompt_toolkit.layout.containers import FloatContainer
from prompt_toolkit.output import DummyOutput

from ui.repl.commands import SlashCommands
from ui.repl.completer import SlashCompleter


class DefaultLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        # A dummy input/output keeps the session off the real terminal, so the
        # tests run the same under pytest, CI, or a plain shell.
        app_session = create_app_session(input=DummyInput(), output=DummyOutput())
        app_session.__enter__()
        self.addCleanup(app_session.__exit__, None, None, None)

    def _session(self) -> PromptSession[str]:
        return PromptSession(
            completer=SlashCompleter(SlashCommands(Mock(), Mock())),
            complete_while_typing=True,
            # reserve_space_for_menu is deliberately left at its default.
        )

    def test_root_container_holds_no_floats(self) -> None:
        container = self._session().app.layout.container
        self.assertNotIsInstance(container, FloatContainer)

    def test_completer_is_attached_to_the_session(self) -> None:
        session = self._session()
        self.assertIsInstance(session.completer, SlashCompleter)
        self.assertTrue(session.complete_while_typing)


if __name__ == "__main__":
    unittest.main()

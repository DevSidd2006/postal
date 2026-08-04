from __future__ import annotations

from typing import Callable

from rich.console import Console
from rich.text import Text

from agent.agent import Agent
from config.config import Config
from ui.repl.commands.base import CommandGroup
from ui.repl.commands.help import HelpCommands
from ui.repl.commands.inspect import InspectCommands
from ui.repl.commands.sessions import SessionCommands
from ui.repl.commands.settings import SettingsCommands

Handler = Callable[[Agent, list[str]], None]

EXIT_NAMES = {"exit", "quit"}


class SlashCommands(HelpCommands, SettingsCommands, SessionCommands, InspectCommands):
    """Everything typed after a `/`, routed to the group that handles it."""

    def __init__(self, config: Config, console: Console) -> None:
        CommandGroup.__init__(self, config, console)

        self._handlers: dict[str, Handler] = {
            "help": self.show_help,
            "clear": self.clear_history,
            "config": self.show_config,
            "model": self.set_model,
            "approval": self.set_approval,
            "thinking": self.set_thinking,
            "reasoning": self.set_thinking,
            "stats": self.show_stats,
            "tools": self.show_tools,
            "mcp": self.show_mcp,
            "sessions": self.list_sessions,
            "resume": self.resume_session,
            "checkpoint": self.save_checkpoint,
            "save": self.save_checkpoint,
            "checkpoints": self.list_checkpoints,
            "rewind": self.rewind,
        }

    def is_command(self, message: str) -> bool:
        return message.startswith("/")

    async def execute(self, agent: Agent, message: str) -> bool:
        """Run one command. Returns False when the REPL should stop."""

        parts = message.split()
        name = parts[0].lstrip("/").lower()
        args = parts[1:]

        if name in EXIT_NAMES:
            return False

        handler = self._handlers.get(name)
        if handler is None:
            self.console.print(f"[error]Unknown command: /{name}[/error]")
            self.console.print(Text("Type /help to see available commands.", style="muted"))
            return True

        handler(agent, args)
        return True

from prompt_toolkit import PromptSession
from prompt_toolkit.layout.containers import FloatContainer, Float
from prompt_toolkit.layout.menus import CompletionsMenu
from ui.repl.completer import SlashCompleter
from ui.repl.commands import SlashCommands
from rich.console import Console
from config.config import Config

session = PromptSession(
    completer=SlashCompleter(SlashCommands(Config(), Console())),
    complete_while_typing=True,
)

root = session.app.layout.container
session.app.layout.container = FloatContainer(
    content=root,
    floats=[
        Float(
            xcursor=True,
            ycursor=True,
            content=CompletionsMenu(max_height=8, scroll_offset=1),
        )
    ],
)

print("New root container:", type(session.app.layout.container))
print("Floats:", session.app.layout.container.floats)

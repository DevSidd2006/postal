import inspect
from prompt_toolkit import PromptSession
from prompt_toolkit.layout.containers import FloatContainer, Float
from ui.repl.completer import SlashCompleter
from ui.repl.commands import SlashCommands
from rich.console import Console
from config.config import Config

session = PromptSession(
    completer=SlashCompleter(SlashCommands(Config(), Console())),
    complete_while_typing=True,
    # reserve_space_for_menu is NOT set
)

container = session.app.layout.container
print("Top container type:", type(container))
if isinstance(container, FloatContainer):
    print("Floats count:", len(container.floats))
    for f in container.floats:
        print("  Float:", f, "content:", type(f.content))

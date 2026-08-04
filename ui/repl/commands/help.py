from __future__ import annotations

from rich.markdown import Markdown

from agent.agent import Agent
from ui.repl.commands.base import CommandGroup

HELP_TEXT = """\
## Commands

- `/help` - Show this help
- `/exit` or `/quit` - Exit the agent
- `/clear` - Clear conversation history
- `/config` - Show current configuration
- `/model <name>` - Change the model
- `/approval <mode>` - Change approval mode
- `/thinking [on|off|low|medium|high]` - Show or configure model reasoning
- `/stats` - Show session statistics
- `/tools` - List available tools
- `/mcp` - Show MCP server status

## Sessions

- `/sessions [all]` - List saved sessions, newest first
- `/sessions rm <n|id>` - Delete a saved session
- `/resume <n|id>` - Load a saved session into this one
- `/checkpoint [label]` - Save a checkpoint now, with an optional name
- `/checkpoints` - List checkpoints in this session
- `/rewind <n|id>` - Roll the conversation back to a checkpoint

## Tips

- Just type your message to chat with the agent
- Type `/` to see every command and keep typing to filter them; `↑`/`↓` to pick, `Enter` to run, `Tab` to fill in
- The agent can read, write, and execute code
- Some operations require approval (can be configured)
- Sessions are saved after every turn; `postal --resume` picks the last one up
"""


class HelpCommands(CommandGroup):

    def show_help(self, agent: Agent, args: list[str]) -> None:
        self.console.print(Markdown(HELP_TEXT))

from __future__ import annotations

from datetime import datetime

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text

from agent.agent import Agent
from client.response import TokenUsage
from config.config import ApprovalPolicy, Config
from context.loop_detector import LoopDetector
from tools.mcp.client import MCPServerStatus

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

## Tips

- Just type your message to chat with the agent
- The agent can read, write, and execute code
- Some operations require approval (can be configured)
"""

MCP_STATUS_STYLES = {
    MCPServerStatus.CONNECTED: "success",
    MCPServerStatus.CONNECTING: "warning",
    MCPServerStatus.DISCONNECTED: "muted",
    MCPServerStatus.ERROR: "error",
}


def _format_elapsed(start: datetime) -> str:
    seconds = int((datetime.now() - start).total_seconds())
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


class SlashCommands:

    def __init__(self, config: Config, console: Console) -> None:
        self.config = config
        self.console = console

    def is_command(self, message: str) -> bool:
        return message.startswith("/")

    async def execute(self, agent: Agent, message: str) -> bool:
        parts = message.split()
        name = parts[0].lstrip("/").lower()
        args = parts[1:]

        if name in {"exit", "quit"}:
            return False

        if name == "help":
            self._help()
        elif name == "clear":
            self._clear(agent)
        elif name == "config":
            self._config()
        elif name == "model":
            self._model(args)
        elif name == "approval":
            self._approval(agent, args)
        elif name in {"thinking", "reasoning"}:
            self._thinking(args)
        elif name == "stats":
            self._stats(agent)
        elif name == "tools":
            self._tools(agent)
        elif name == "mcp":
            self._mcp(agent)
        else:
            self.console.print(f"[error]Unknown command: /{name}[/error]")
            self.console.print(Text("Type /help to see available commands.", style="muted"))

        return True

    def _help(self) -> None:
        self.console.print(Markdown(HELP_TEXT))

    def _clear(self, agent: Agent) -> None:
        session = agent.session
        session.context_manager.clear()
        session.context_manager.set_latest_usage(TokenUsage())
        session.loop_detector = LoopDetector()
        self.console.clear()
        self.console.print(Text("Conversation history cleared.", style="muted"))

    def _config(self) -> None:
        table = Table.grid(padding=(0, 1))
        table.add_column(style="muted")
        table.add_column(style="subtitle")

        policy = self.config.approval
        rows = [
            ("Model", self.config.model_name),
            ("Temperature", str(self.config.temperature)),
            ("Context window", f"{self.config.model.context_window:,}"),
            ("Directory", str(self.config.cwd)),
            ("Approval", f"{policy.label} - {policy.summary}"),
            ("Thinking", self._thinking_summary()),
            ("Max turns", str(self.config.max_turns)),
            ("Max tool output tokens", f"{self.config.max_tool_output_tokens:,}"),
            ("Hooks enabled", str(self.config.hooks_enabled)),
            ("MCP servers", str(len(self.config.mcp_servers))),
            ("Debug", str(self.config.debug)),
        ]
        for label, value in rows:
            table.add_row(f"{label}:", value)

        self.console.print(Text("Configuration", style="highlight"))
        self.console.print(table)

    def _model(self, args: list[str]) -> None:
        if not args:
            self.console.print(
                Text.assemble(("Current model: ", "muted"), (self.config.model_name, "subtitle"))
            )
            self.console.print(Text("Usage: /model <name>", style="muted"))
            return

        self.config.model_name = args[0]
        self.console.print(f"[success]Model set to {args[0]}[/success]")

    def _approval(self, agent: Agent, args: list[str]) -> None:
        if not args:
            self._approval_modes()
            return

        try:
            policy = ApprovalPolicy(args[0].lower())
        except ValueError:
            self.console.print(f"[error]Unknown approval mode: {args[0]}[/error]")
            self._approval_modes()
            return

        self.config.approval = policy
        agent.session.approval_manager.approval_policy = policy
        self.console.print(f"[success]Approval mode set to {policy.label}[/success]")

    def _thinking_summary(self) -> str:
        reasoning = self.config.reasoning
        if not reasoning.enabled:
            return "off"

        detail = (
            f"{reasoning.max_tokens:,} tokens"
            if reasoning.max_tokens is not None
            else reasoning.effort or "default"
        )
        return f"{'shown' if reasoning.visible else 'hidden'} - {detail}"

    def _thinking(self, args: list[str]) -> None:
        reasoning = self.config.reasoning

        if not args:
            self._thinking_state()
            self.console.print(
                Text("Usage: /thinking <on|off|low|medium|high|minimal>", style="muted")
            )
            return

        choice = args[0].lower()

        if choice in {"on", "show"}:
            reasoning.enabled = True
            reasoning.visible = True
        elif choice in {"off", "hide"}:
            # The model keeps reasoning, we just stop printing it.
            reasoning.visible = False
        elif choice in {"minimal", "low", "medium", "high"}:
            reasoning.enabled = True
            reasoning.visible = True
            reasoning.effort = choice
            reasoning.max_tokens = None
        elif choice == "none":
            reasoning.enabled = False
            reasoning.visible = False
        else:
            self.console.print(f"[error]Unknown thinking option: {args[0]}[/error]")
            self.console.print(
                Text("Usage: /thinking <on|off|low|medium|high|minimal|none>", style="muted")
            )
            return

        self._thinking_state()

    def _thinking_state(self) -> None:
        reasoning = self.config.reasoning

        if not reasoning.enabled:
            self.console.print(Text("Thinking is off - no reasoning requested.", style="muted"))
            return

        if reasoning.max_tokens is not None:
            budget = f"{reasoning.max_tokens:,} token budget"
        elif reasoning.effort is not None:
            budget = f"{reasoning.effort} effort"
        else:
            budget = "provider default"

        line = Text.assemble(
            ("thinking ", "muted"),
            ("shown" if reasoning.visible else "hidden", "success" if reasoning.visible else "subtitle"),
            (f" — {budget}", "muted"),
        )
        self.console.print(line)
        self.console.print(
            Text("Models without reasoning support simply ignore this.", style="dim")
        )

    def _approval_modes(self) -> None:
        table = Table.grid(padding=(0, 2))
        table.add_column(style="subtitle")
        table.add_column(style="muted")
        for policy in ApprovalPolicy:
            marker = " (current)" if policy is self.config.approval else ""
            table.add_row(policy.value, f"{policy.summary}{marker}")

        self.console.print(Text("Approval modes:", style="highlight"))
        self.console.print(table)
        self.console.print(Text("Usage: /approval <mode>", style="muted"))

    def _stats(self, agent: Agent) -> None:
        session = agent.session
        usage = session.context_manager.total_usage

        table = Table.grid(padding=(0, 1))
        table.add_column(style="muted")
        table.add_column(style="subtitle")
        rows = [
            ("Session", session.session_id),
            ("Turns", str(session.turns)),
            ("Duration", _format_elapsed(session.created_at)),
            ("Prompt tokens", f"{usage.prompt_tokens:,}"),
            ("Completion tokens", f"{usage.completion_tokens:,}"),
            ("Cached tokens", f"{usage.cached_tokens:,}"),
            ("Total tokens", f"{usage.total_tokens:,}"),
        ]
        for label, value in rows:
            table.add_row(f"{label}:", value)

        self.console.print(Text("Session statistics", style="highlight"))
        self.console.print(table)

    def _tools(self, agent: Agent) -> None:
        tools = agent.session.tool_registry.get_tools()
        if not tools:
            self.console.print(Text("No tools available.", style="muted"))
            return

        table = Table.grid(padding=(0, 2))
        table.add_column(style="subtitle")
        table.add_column(style="muted")
        for tool in sorted(tools, key=lambda t: t.name):
            description = tool.description.strip().splitlines()[0] if tool.description else ""
            table.add_row(tool.name, description)

        self.console.print(Text(f"Available tools ({len(tools)})", style="highlight"))
        self.console.print(table)

    def _mcp(self, agent: Agent) -> None:
        clients = agent.session.mcp_manager.clients
        if not clients:
            self.console.print(Text("No MCP servers configured.", style="muted"))
            return

        table = Table.grid(padding=(0, 2))
        table.add_column(style="subtitle")
        table.add_column()
        table.add_column(style="muted")
        for client in clients:
            status_style = MCP_STATUS_STYLES.get(client.status, "muted")
            table.add_row(
                client.name,
                Text(client.status.value, style=status_style),
                f"{len(client.tools)} tools",
            )

        self.console.print(Text(f"MCP servers ({len(clients)})", style="highlight"))
        self.console.print(table)

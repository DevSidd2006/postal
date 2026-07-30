from __future__ import annotations

from datetime import datetime
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text

from agent.agent import Agent
from agent.store import Checkpoint, SessionMeta
from client.response import TokenUsage
from config.config import ApprovalPolicy, Config
from config.loader import save_model_name
from tools.mcp.client import MCPServerStatus
from ui.renderer import render_transcript

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
- The agent can read, write, and execute code
- Some operations require approval (can be configured)
- Sessions are saved after every turn; `postal --resume` picks the last one up
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


def format_ago(moment: datetime) -> str:
    seconds = int((datetime.now() - moment).total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86_400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86_400}d ago"


def pick(items: list, token: str, identity) -> Any | None:
    """Resolve a `1`-based list position or an id prefix to one item."""

    token = token.strip()
    if not token:
        return None

    if token.isdigit():
        index = int(token) - 1
        return items[index] if 0 <= index < len(items) else None

    return next((item for item in items if identity(item).startswith(token)), None)


class SlashCommands:

    def __init__(self, config: Config, console: Console) -> None:
        self.config = config
        self.console = console

        # Whatever the last /sessions and /checkpoints printed, so the numbers
        # in those listings can be used as arguments.
        self._listed_sessions: list[SessionMeta] = []
        self._listed_checkpoints: list[Checkpoint] = []

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
        elif name == "sessions":
            self._sessions(agent, args)
        elif name == "resume":
            self._resume(agent, args)
        elif name in {"checkpoint", "save"}:
            self._checkpoint(agent, args)
        elif name == "checkpoints":
            self._checkpoints(agent)
        elif name == "rewind":
            self._rewind(agent, args)
        else:
            self.console.print(f"[error]Unknown command: /{name}[/error]")
            self.console.print(Text("Type /help to see available commands.", style="muted"))

        return True

    def _help(self) -> None:
        self.console.print(Markdown(HELP_TEXT))

    def _clear(self, agent: Agent) -> None:
        session = agent.session

        # The conversation being cleared stays on disk under its own id, so
        # clearing is recoverable with /resume.
        if session.turns:
            session.save_checkpoint()

        saved = session.store.exists(session.session_id)
        previous = session.short_id

        session.reset()
        session.context_manager.set_latest_usage(TokenUsage())
        self._listed_checkpoints = []

        self.console.clear()
        self.console.print(Text("Conversation history cleared.", style="muted"))
        if saved:
            self.console.print(
                Text(f"The previous conversation is saved as {previous}.", style="muted")
            )

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
        try:
            save_model_name(args[0], cwd=self.config.cwd)
        except Exception as exc:
            self.console.print(f"[warning]Model changed for this session, but could not be saved: {exc}[/warning]")
            return
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
            ("Messages", str(session.context_manager.message_count)),
            ("Checkpoints", str(len(session.checkpoints()))),
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

    def _sessions(self, agent: Agent, args: list[str]) -> None:
        session = agent.session

        if args and args[0].lower() in {"rm", "delete", "remove"}:
            self._session_delete(agent, args[1:])
            return

        # Sessions are scoped to the directory they ran in; `all` widens that.
        every = bool(args) and args[0].lower() == "all"
        sessions = session.store.list(None if every else self.config.cwd)

        if not sessions:
            scope = "" if every else " for this directory"
            self.console.print(Text(f"No saved sessions{scope}.", style="muted"))
            if not every:
                self.console.print(
                    Text("Try /sessions all to look in every directory.", style="muted")
                )
            return

        self._listed_sessions = sessions

        table = Table.grid(padding=(0, 2))
        table.add_column(style="muted", justify="right")
        table.add_column(style="subtitle")
        table.add_column(style="muted")
        table.add_column(style="muted", justify="right")
        table.add_column()

        for index, meta in enumerate(sessions, start=1):
            current = meta.session_id == session.session_id
            table.add_row(
                str(index),
                meta.short_id,
                format_ago(meta.updated_at),
                f"{meta.turns} turn{'s' if meta.turns != 1 else ''}",
                Text(
                    meta.title + (" (current)" if current else ""),
                    style="highlight" if current else "text",
                ),
            )

        header = "Saved sessions" if every else "Saved sessions here"
        self.console.print(Text(f"{header} ({len(sessions)})", style="highlight"))
        self.console.print(table)
        self.console.print(Text("Usage: /resume <number|id>", style="muted"))

    def _session_delete(self, agent: Agent, args: list[str]) -> None:
        if not args:
            self.console.print(Text("Usage: /sessions rm <number|id>", style="muted"))
            return

        session = agent.session
        candidates = self._listed_sessions or session.store.list(self.config.cwd)
        target = pick(candidates, args[0], lambda meta: meta.session_id)

        if target is None:
            self.console.print(f"[error]No such session: {args[0]}[/error]")
            return

        if target.session_id == session.session_id:
            self.console.print(
                "[error]That is the session you are in, it cannot be deleted.[/error]"
            )
            return

        if session.store.delete(target.session_id):
            self._listed_sessions = []
            self.console.print(
                f"[success]Deleted session {target.short_id}[/success] - {target.title}"
            )
        else:
            self.console.print(f"[error]Could not delete {target.short_id}[/error]")

    def _resume(self, agent: Agent, args: list[str]) -> None:
        session = agent.session

        if not args:
            self._sessions(agent, [])
            return

        candidates = self._listed_sessions or session.store.list(self.config.cwd)
        target = pick(candidates, args[0], lambda meta: meta.session_id)

        if target is None:
            # Not in the listing: it may still be an id from another directory.
            resolved = session.store.resolve(args[0], self.config.cwd)
            target = session.store.read_meta(resolved) if resolved else None

        if target is None:
            self.console.print(f"[error]No such session: {args[0]}[/error]")
            self.console.print(Text("Type /sessions to see what is saved.", style="muted"))
            return

        if target.session_id == session.session_id:
            self.console.print(Text("Already in that session.", style="muted"))
            return

        # Do not strand the conversation that is being replaced. A session
        # that never took a turn has nothing worth keeping.
        if session.turns:
            session.save_checkpoint()

        record = session.resume(target.session_id)
        if record is None:
            self.console.print(f"[error]Could not read session {target.short_id}[/error]")
            return

        self._listed_checkpoints = []
        self.announce_resume(agent)

    def announce_resume(self, agent: Agent) -> None:
        session = agent.session
        meta = session.resumed_from.meta if session.resumed_from else session.meta()

        line = Text.assemble(
            ("Resumed ", "success"),
            (meta.short_id, "subtitle"),
            (f" - {meta.title}", "muted"),
        )
        self.console.print()
        self.console.print(line)
        turns = session.turns
        self.console.print(
            Text(
                f"{session.context_manager.message_count} messages · "
                f"{turns} turn{'s' if turns != 1 else ''} · "
                f"saved {format_ago(meta.updated_at)}",
                style="muted",
            )
        )

        if meta.model and meta.model != self.config.model_name:
            self.console.print(
                Text(
                    f"Saved with {meta.model}, continuing with {self.config.model_name}.",
                    style="warning",
                )
            )

        render_transcript(self.console, session.context_manager.history)

    def _checkpoint(self, agent: Agent, args: list[str]) -> None:
        session = agent.session

        if not self.config.session.enabled:
            self.console.print(
                "[error]Session saving is disabled in your config.[/error]"
            )
            return

        if session.context_manager.message_count == 0:
            self.console.print(Text("Nothing to save yet.", style="muted"))
            return

        label = " ".join(args).strip() or None
        checkpoint = session.save_checkpoint(label=label, auto=False)

        if checkpoint is None:
            self.console.print("[error]Could not write the checkpoint.[/error]")
            return

        self._listed_checkpoints = []
        self.console.print(
            Text.assemble(
                ("Saved ", "success"),
                (checkpoint.label, "subtitle"),
                (f" · {checkpoint.message_count} messages · session ", "muted"),
                (session.short_id, "subtitle"),
            )
        )

    def _checkpoints(self, agent: Agent) -> None:
        session = agent.session
        checkpoints = session.checkpoints()

        if not checkpoints:
            self.console.print(Text("No checkpoints in this session yet.", style="muted"))
            self.console.print(Text("Use /checkpoint to save one now.", style="muted"))
            return

        self._listed_checkpoints = checkpoints

        table = Table.grid(padding=(0, 2))
        table.add_column(style="muted", justify="right")
        table.add_column(style="subtitle")
        table.add_column(style="muted")
        table.add_column(style="muted", justify="right")
        table.add_column(style="muted")

        for index, checkpoint in enumerate(checkpoints, start=1):
            table.add_row(
                str(index),
                checkpoint.id,
                checkpoint.label,
                f"{checkpoint.message_count} msgs",
                format_ago(checkpoint.created_at),
            )

        self.console.print(
            Text(f"Checkpoints in {session.short_id} ({len(checkpoints)})", style="highlight")
        )
        self.console.print(table)
        self.console.print(Text("Usage: /rewind <number|id>", style="muted"))

    def _rewind(self, agent: Agent, args: list[str]) -> None:
        session = agent.session

        if not args:
            self._checkpoints(agent)
            return

        checkpoints = self._listed_checkpoints or session.checkpoints()
        target = pick(checkpoints, args[0], lambda checkpoint: checkpoint.id)

        if target is None:
            self.console.print(f"[error]No such checkpoint: {args[0]}[/error]")
            self.console.print(Text("Type /checkpoints to see them.", style="muted"))
            return

        record = session.store.load(session.session_id, target.id)
        if record is None:
            self.console.print(f"[error]Could not read checkpoint {target.id}[/error]")
            return

        session.restore(record)

        # Rewinding moves the session head, otherwise the next resume would
        # come back to the state we just rolled away from.
        session.save_checkpoint(label=f"rewound to {target.label}", auto=False)

        self._listed_checkpoints = []

        detail = (
            f" · {session.context_manager.message_count} messages"
            f" · turn {session.turns}"
        )

        self.console.print()
        self.console.print(
            Text.assemble(
                ("Rewound to ", "success"),
                (target.label, "subtitle"),
                (detail, "muted"),
            )
        )
        render_transcript(self.console, session.context_manager.history)

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

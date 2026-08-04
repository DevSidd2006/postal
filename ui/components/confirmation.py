from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.box import ROUNDED
from rich.console import Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from tools.base import ToolConfirmation
from ui.components.args_table import render_args_table
from ui.theme import POSTAL_SYNTAX

MAX_CONFIRM_DIFF_LINES = 20

APPROVE_KEYS = {"y", "a"}
REJECT_KEYS = {"n", "d", "q"}


def confirmation_body(confirmation: ToolConfirmation) -> Group:
    blocks: list[Any] = []

    if confirmation.command:
        blocks.append(Text(f"$ {confirmation.command}", style="code"))

    if confirmation.diff is not None:
        # The file header is redundant here: the path is already in the title.
        lines = [
            line
            for line in confirmation.diff.create_diff().splitlines()
            if not line.startswith(("--- ", "+++ "))
        ]
        if len(lines) > MAX_CONFIRM_DIFF_LINES:
            hidden = len(lines) - MAX_CONFIRM_DIFF_LINES
            lines = lines[:MAX_CONFIRM_DIFF_LINES] + [f"… {hidden} more lines"]
        diff = "\n".join(lines).strip()
        if diff:
            blocks.append(
                Syntax(
                    diff,
                    "diff",
                    theme=POSTAL_SYNTAX,
                    word_wrap=True,
                    background_color="default",
                )
            )

    if not blocks:
        blocks.append(render_args_table(confirmation.tool_name, confirmation.params))

    return Group(*blocks)


def confirmation_request(
    confirmation: ToolConfirmation, cwd: Path | str | None = None
) -> list[Any]:
    """Title, description and body, ready to print in order."""

    border = "error" if confirmation.is_dangerous else "warning"

    title = Text.assemble(
        ("⏵ ", border),
        (confirmation.tool_name, "highlight"),
        ("  needs your approval", "subtitle"),
    )
    if confirmation.is_dangerous:
        title.append("  (dangerous)", style="error")

    description = confirmation.description
    if cwd:
        description = description.replace(f"{cwd}/", "")

    return [
        title,
        Text(description, style="muted"),
        Panel(
            confirmation_body(confirmation),
            box=ROUNDED,
            border_style=border,
            padding=(0, 1),
        ),
    ]


def confirmation_choices(badge: str) -> Text:
    choices = Text()
    choices.append("y", style="success")
    choices.append(" accept", style="muted")
    choices.append("  ·  ", style="dim")
    choices.append("n", style="error")
    choices.append(" reject", style="muted")
    choices.append("  ·  ", style="dim")
    choices.append("esc", style="subtitle")
    choices.append(" reject", style="muted")
    choices.append("   ", style="dim")
    choices.append(badge, style="muted")
    return choices

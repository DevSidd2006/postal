from rich.theme import Theme

from ui.theme.palette import PALETTE, TOOL_COLOURS

AGENT_THEME = Theme(
    {
        "info": PALETTE["accent"],
        "warning": PALETTE["amber"],
        "error": f"bold {PALETTE['red']}",
        "success": PALETTE["green"],
        "dim": "dim",
        "muted": PALETTE["graphite"],
        "subtitle": PALETTE["silver"],
        "border": PALETTE["slate"],
        "highlight": f"bold {PALETTE['bright']}",

        "user": f"bold {PALETTE['bright']}",
        "assistant": PALETTE["silver"],

        "reasoning": f"italic {PALETTE['graphite']}",
        "reasoning.mark": PALETTE["violet"],

        "tool": f"bold {PALETTE['accent']}",
        **{f"tool.{kind}": colour for kind, colour in TOOL_COLOURS.items()},

        "code": PALETTE["silver"],

        "diff.plus": PALETTE["green"],
        "diff.minus": PALETTE["red"],

        "md.h1": f"bold {PALETTE['bright']}",
        "md.h2": f"bold {PALETTE['bright']}",
        "md.h3": f"bold {PALETTE['silver']}",
        "md.bold": f"bold {PALETTE['bright']}",
        "md.bolditalic": f"bold italic {PALETTE['bright']}",
        "md.italic": f"italic {PALETTE['silver']}",
        "md.strike": f"strike {PALETTE['graphite']}",
        "md.code": PALETTE["amber"],
        "md.link": f"underline {PALETTE['accent']}",
        "md.bullet": PALETTE["accent"],
        "md.quote": f"italic {PALETTE['graphite']}",
        "md.rule": PALETTE["slate"],
    }
)

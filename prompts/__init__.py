"""Prompt text used by the agent, one module per section.

The system prompt is assembled in `prompts.system`; each section it stitches
together lives in its own module so the text is easy to find and edit:

- `identity`         : who the agent is
- `agents_md`        : AGENTS.md specification
- `security`         : security guidelines
- `environment`      : date, OS, cwd, shell
- `tool_guidelines`  : available tools and best practices
- `instructions`     : project / user instructions and remembered context
- `operational`      : tone, workflows, tool usage, coding guidelines

Standalone prompts live alongside them: `compaction` and `loop_breaker`.
"""

from prompts.agents_md import get_agents_md_section
from prompts.compaction import get_compaction_prompt
from prompts.environment import get_environment_section
from prompts.identity import get_identity_section
from prompts.instructions import (
    get_developer_instructions_section,
    get_memory_section,
    get_user_instructions_section,
)
from prompts.loop_breaker import create_loop_breaker_prompt
from prompts.operational import get_operational_section
from prompts.security import get_security_section
from prompts.system import get_system_prompt
from prompts.tool_guidelines import get_tool_guidelines_section

__all__ = [
    "create_loop_breaker_prompt",
    "get_agents_md_section",
    "get_compaction_prompt",
    "get_developer_instructions_section",
    "get_environment_section",
    "get_identity_section",
    "get_memory_section",
    "get_operational_section",
    "get_security_section",
    "get_system_prompt",
    "get_tool_guidelines_section",
    "get_user_instructions_section",
]

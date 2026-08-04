# Architecture

Postal is built as an object-oriented codebase. The agent loop, the tools, the safety layer and the terminal UI are all classes with one responsibility each, wired together at startup instead of reaching for each other through globals. That is what keeps the project hackable: adding a tool or a sub-agent means writing one class and registering it, not threading a new branch through the loop.

## Packages

| Package | What lives there |
| --- | --- |
| `agent/` | `Agent` (the loop), `Session` (everything one conversation owns), `AgentEvent`, `SessionStore` |
| `tools/` | The `Tool` base class, `ToolRegistry`, and every concrete tool: core, network, memory, MCP, sub-agents |
| `client/` | `LLMClient` and the streaming response types |
| `context/` | `ContextManager`, `ChatCompactor`, `LoopDetector` |
| `safety/` | `ApprovalManager` and the approval policy types |
| `config/` | Pydantic config models and the TOML loader |
| `hooks/` | `HookSystem`, which runs lifecycle hooks |
| `ui/` | `TUI`, `Repl`, the slash command groups, and the render components |

## One abstract base class, every tool

Everything the model can call is a subclass of `Tool` (`tools/base.py`), an `abc.ABC` that declares `execute` abstract and gives everything else a working default. A tool is a class attribute block plus one method:

```python
class GlobTool(Tool):
    name = "glob"
    description = "Find files matching a glob pattern"
    kind = ToolKind.READ
    schema = GlobParams          # a pydantic BaseModel

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        ...
```

The base class handles the rest for every subclass: `validate_params` runs the Pydantic model, `to_openai_schema` turns the same model into the JSON Schema sent to the API, `is_mutating` decides from `kind` whether the approval layer gets involved, and `get_confirmation` builds the prompt the user sees.

Subclasses override only where their behaviour genuinely differs, which is the point of the base being concrete:

- `EditTool` and `WriteFileTool` override `get_confirmation` to attach a `FileDiff`, so the confirmation shows the exact patch instead of a generic "run edit".
- `MCPTool` overrides `is_mutating` to always return `True`, because a third-party server's side effects are unknowable.
- `SubAgentTool` turns `name` and `description` into properties, since both come from the `SubagentDefinition` handed to `__init__` — one class backs all five sub-agents.
- `ApplyPatchTool` keeps its multi-file staging in a private `_WorkingTree` helper class, so an all-or-nothing patch either commits every operation or none.

Because the loop only ever sees the base type, it never branches on which tool it is holding. `ToolRegistry` stores tools behind private `_tools` and `_mcp_tools` dicts and hands out `Tool` instances; the agent calls `execute` and lets dispatch do the work.

## Composition over deep hierarchies

Inheritance is one level deep almost everywhere. The structure comes from objects owning other objects:

- **`Session` is the composition root.** It constructs and owns the `LLMClient`, `ToolRegistry`, `ContextManager`, `ApprovalManager`, `HookSystem`, `MCPManager`, `ChatCompactor`, `LoopDetector` and `SessionStore` for one conversation.
- **`Agent` holds a `Session`** and drives it. The agent loop reads as orchestration — prune, compact, stream, dispatch, checkpoint — because each of those verbs belongs to a collaborator.
- **Sub-agents fall out of the same structure.** `SubAgentTool.execute` builds a narrowed `Config` (fewer tools, its own turn cap, checkpointing off) and constructs a full `Agent` with it. Nesting is free: it is the same class, composed again.

The slash commands are the one deliberate use of multiple inheritance. `HelpCommands`, `SettingsCommands`, `SessionCommands` and `InspectCommands` each extend a shared `CommandGroup`, and `SlashCommands` mixes all four together so every group sees the same console, config, and last-printed listings — which is what lets `/rewind 1` refer to the number `/checkpoints` just printed.

## Value objects, named constructors, closed sets

Data that moves between layers is a dataclass, not a dict:

| Type | Role |
| --- | --- |
| `ToolResult` | Every tool returns one. Built through the `success_result` / `error_result` classmethod factories, and renders itself for the model via `to_model_output`. |
| `FileDiff` | Old and new content for one path, with `create_diff()` next to the data it formats. |
| `ToolConfirmation` | What the approval layer needs to ask the user, including the diff and affected paths. |
| `AgentEvent` | One classmethod per event type (`AgentEvent.agent_start`, `.reasoning_delta`, …), so the loop never assembles event payloads by hand. |
| `Checkpoint`, `SessionMeta`, `SessionRecord` | The on-disk session format, serialized by `SessionStore`. |

Anything with a fixed set of values is a `str`-backed `Enum` — `ToolKind`, `ApprovalDecision`, `AgentEventType`, `StreamEventType`, `PatchAction`, `MCPServerStatus` — so it is exhaustive at the type level and still readable in JSON.

Configuration is a tree of Pydantic models (`ModelConfig`, `ReasoningConfig`, `SessionConfig`, `ShellEnvironmentConfig`, `MCPServerConfig`, `HookConfig`) with validation on the fields and behaviour on the class: `ReasoningConfig.to_request_payload()` knows the effort-or-budget rule that OpenRouter enforces, so no caller has to.

Errors follow one hierarchy rooted at `AgentError`, which carries a message, structured `details`, and the underlying `cause`, and serializes through `to_dict()`. `ConfigError` extends it with the offending key and file.

## The UI splits state from rendering

`ui/components/` holds one module per visual element — spinner, gutter, markdown, tool calls, confirmations, plans, thinking, usage, transcript — and the split inside them is deliberate. Anything that carries state across frames is a class: `Spinner` owns its frame counter, `MarkdownStream` owns the partial-line buffer that lets markdown render while it is still arriving, `Gutter` wraps a renderable so it can be drawn indented under a bar. Everything else is a pure function from a value object to a Rich renderable, which is why `tool_call.py` can dispatch on tool kind (`_read`, `_shell`, `_patch`, …) over a single `ToolOutcome` dataclass instead of subclassing a renderer per tool.

`Gutter` implements Rich's rendering protocol directly — `__rich_console__` yields the bar and the indented body segment by segment — so it nests inside any other renderable exactly like a built-in Rich object.

## Adding a tool

The shape of the codebase makes this a two-step change:

1. Write a `BaseModel` for the parameters and a `Tool` subclass with `name`, `description`, `kind`, `schema` and `execute`.
2. Register it in `tools/registry.py`.

The schema the model sees, the argument validation, and the approval behaviour all follow from what you declared. [CONTRIBUTING.md](../CONTRIBUTING.md) has the rest of the workflow.

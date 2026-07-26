<h1 align='center'>
  Relay
</h1>

<p align="center">
  <a href="https://github.com/andrefetch/relay/stargazers"><img src="https://img.shields.io/github/stars/andrefetch/relay?style=for-the-badge&logo=github&logoColor=white&color=181717" alt="GitHub stars" /></a>
  <a href="https://github.com/andrefetch/relay/network/members"><img src="https://img.shields.io/github/forks/andrefetch/relay?style=for-the-badge&logo=github&logoColor=white&color=181717" alt="GitHub forks" /></a>
  <a href="https://github.com/andrefetch/relay/issues"><img src="https://img.shields.io/github/issues/andrefetch/relay?style=for-the-badge&logo=github&logoColor=white&color=181717" alt="GitHub issues" /></a>

<p align="center">
  <img src="https://img.shields.io/badge/PYTHON-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/OPENROUTER-1a1a1a?style=for-the-badge&logoColor=white" alt="OpenRouter" />
  <img src="https://img.shields.io/badge/OPENAI%20SDK-412991?style=for-the-badge&logo=openai&logoColor=white" alt="OpenAI SDK" />
  <img src="https://img.shields.io/badge/MCP-000000?style=for-the-badge&logo=modelcontextprotocol&logoColor=white" alt="Model Context Protocol" />
  <img src="https://img.shields.io/badge/PYDANTIC-E92063?style=for-the-badge&logo=pydantic&logoColor=white" alt="Pydantic" />
  <br />
  <img src="https://img.shields.io/badge/RICH-2b2b2b?style=for-the-badge&logoColor=white" alt="Rich" />
  <img src="https://img.shields.io/badge/PROMPT%20TOOLKIT-4b8bbe?style=for-the-badge&logoColor=white" alt="prompt_toolkit" />
  <img src="https://img.shields.io/badge/CLICK-d1d1d1?style=for-the-badge&logoColor=black" alt="Click" />
  <img src="https://img.shields.io/badge/DUCKDUCKGO-DE5833?style=for-the-badge&logo=duckduckgo&logoColor=white" alt="DuckDuckGo" />
  <img src="https://img.shields.io/badge/DOCKER-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
</p>

Relay is an open-source AI coding agent that runs in your terminal. It connects to LLMs through OpenRouter, reads and edits your code with a built-in tool set, runs shell commands, and streams everything through a full-screen TUI.

<p align="center">
  <img src="assets/demo_smooth.gif" alt="Relay planning and executing a multi-step task in the terminal" width="100%" />
</p>

> [!WARNING]
> **Work in progress.** The agent loop, tool calling, terminal UI, and approval flow work end to end. The [approval policy](#approvals) is set in config (`approval = "on_request"` by default), there is **no way to switch it mid-session yet**. Sub-agents still auto-approve their own tool calls, so use Relay in a directory you don't mind it touching

## Functionality

### Interface
| | |
| --- | --- |
| **Interactive TUI** | Full-screen terminal interface built on Rich, with streaming responses, live tool call output, and token usage tracking. |
| **Single-shot mode** | Pass a prompt as an argument for non-interactive runs, suitable for scripting. |

### Tools
| | |
| --- | --- |
| **Files** | `read`, `write`, `edit`, `grep`, `glob`, and `list_directories` for working with a codebase. |
| **Shell** | The `shell` tool executes commands in the working directory. |
| **Planning** | A `plan` tool tracks steps (a todo list) across the agent loop. |
| **Network** | Web search via DuckDuckGo and URL fetching. |
| **Memory** | Key-value storage that survives across sessions. |
| **MCP** | Connects to external MCP servers for additional tools and data sources. |

### Agent
| | |
| --- | --- |
| **Approvals** | Mutating tool calls are gated by an approval policy, from confirming every write to running unattended. See [Approvals](#approvals). |
| **Sub-agents** | Specialized agents the main agent can delegate to: `codebase_investigator`, `code_reviewer`, `software_architect`, `test_writer`, `debugger`. |
| **`AGENTS.md`** | Project instructions are picked up automatically and followed while working. |
| **Context pruning** | Old tool outputs are cleared once they pile up past the recent working set, reclaiming tokens without touching the conversation itself. |
| **Compaction** | When the context window fills up, history is summarized into a continuation brief and the session resumes from it instead of erroring out. |
| **OpenRouter backend** | Authenticate once with `relay login` (browser OAuth) or paste an API key. Model, temperature, and context window are configurable in `~/.config/relay/config.toml`, with per-project overrides in `.relay/config.toml`. |

## Getting started

```bash
# 1. Install Relay
pip install relay-code

# 2. Log in (opens your browser to authorize with OpenRouter)
relay login
relay login --paste   # or paste an API key directly

# 3. Run it
relay                 # interactive mode
relay "your prompt"   # single-shot mode
relay --cwd /path     # run against a different working directory

# Remove the saved API key
relay logout
```

## Approvals

Before Relay runs anything that changes state, the approval policy decides whether it goes ahead, asks you, or is refused outright. Read-only tools (`read`, `grep`, `glob`, `list_directories`, `plan`) never prompt, so a policy only affects writes, shell commands, network calls, memory writes, MCP tools, and sub-agent runs.

Set it with the `approval` key in your config file:

```toml
# ~/.config/relay/config.toml (user-wide), or .relay/config.toml (per project)
approval = "on_request"
```

| Value | Badge | Behaviour |
| --- | --- | --- |
| `on_request` *(default)* | `ask` | Confirm every mutating tool call. Commands matched as known-safe (`ls`, `git status`, `grep`, …) run without asking. |
| `auto_edit` | `auto-edit` | File edits and writes inside the working directory go through unprompted; shell commands still need confirmation unless known-safe. |
| `auto` | `auto` | Everything runs except dangerous commands, which are rejected. |
| `on_fail` | `on fail` | Currently identical to `auto`. Reserved for prompting after a failed tool call, which is not implemented yet. |
| `never` | `read-only` | Rejects anything that isn't a known-safe command. Nothing gets written, and you are never prompted. |
| `yolo` | `yolo` | Approves everything, including commands matched as dangerous. Only use this in a sandbox or container. |

Two rules apply on top of the policy, and no policy except `yolo` overrides them:

- **Dangerous commands are rejected.** `rm -rf /`, `dd if=`, `mkfs`, `shutdown`, `curl … | bash`, fork bombs, and similar patterns are refused before the shell ever sees them (the full list is `DANGEROUS_PATTERNS` in `safety/approval.py`).
- **Anything touching a path outside the working directory is confirmed**, however permissive the policy is (`never` rejects it instead).

The active policy is printed at startup and shown in the prompt badge, colour-coded by risk: normal for `ask`, `auto-edit` and `read-only`, amber for `auto` and `on fail`, red for `yolo`.

### Answering a prompt

When confirmation is needed, Relay pauses the stream and shows the tool, its arguments, the command it wants to run, and a diff for file edits:

```text
⏵ edit  needs your approval
Edit relay/config/config.py
╭─────────────────────────────────────────╮
│ - approval: ApprovalPolicy = ON_REQUEST │
│ + approval: ApprovalPolicy = AUTO_EDIT  │
╰─────────────────────────────────────────╯
y accept  ·  n reject  ·  esc reject   approval: ask - confirm every mutating tool
```

`y`, `a` or `enter` approves; `n`, `d`, `q`, `esc` or `ctrl+c` rejects. A rejection is fed back to the agent as a failed tool call, so it can pick a different approach rather than stopping.

> [!NOTE]
> Two gaps to be aware of: the policy is fixed for the session (a `/approval` command is on the [roadmap](#roadmap)), and sub-agents run with their own auto-approving manager, so tool calls they make are not routed to you.

## Project instructions (`AGENTS.md`)

Drop an `AGENTS.md` at the root of your repo and Relay loads it as developer instructions at startup, use it for build and test commands, code style, or anything else the agent should know before touching your code

Relay walks up from the working directory to the repository root, so running `relay` inside a subdirectory still picks up the root file. Every `AGENTS.md` found along the way is included, ordered outermost first.

```markdown
# AGENTS.md

## Commands
- Test: `pytest`
- Lint: `ruff check .`

## Style
- Type hints on all public functions.
```

The scope of an `AGENTS.md` file is the directory tree it sits in, and the more deeply nested file wins on conflicts. Files below the working directory are read on demand as the agent works in those subdirectories. Instructions you give directly in a prompt always take precedence over `AGENTS.md`.

## Roadmap

Currently being worked on:

- **Session management**: saving, resuming, and switching between sessions.
- **Slash commands**: in-session commands (e.g. `/approval` to switch approval mode) instead of only config-file settings.
- **Approval flow**: prompting before file edits and shell commands is in place; still to come is switching the mode mid-session and extending confirmations to sub-agents.

## License

[GNU GENERAL PUBLIC LICENSE v3.0](LICENSE)

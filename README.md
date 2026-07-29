<h1 align='center'>
  Postal
</h1>

<p align="center">
  <a href="https://github.com/andrefetch/postal/stargazers"><img src="https://img.shields.io/github/stars/andrefetch/postal?style=for-the-badge&logo=github&logoColor=white&color=181717" alt="GitHub stars" /></a>
  <a href="https://github.com/andrefetch/postal/network/members"><img src="https://img.shields.io/github/forks/andrefetch/postal?style=for-the-badge&logo=github&logoColor=white&color=181717" alt="GitHub forks" /></a>
  <a href="https://github.com/andrefetch/postal/issues"><img src="https://img.shields.io/github/issues/andrefetch/postal?style=for-the-badge&logo=github&logoColor=white&color=181717" alt="GitHub issues" /></a>

<p align="center">
  <img src="https://img.shields.io/badge/PYTHON-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/OPENROUTER-1a1a1a?style=for-the-badge&logoColor=white" alt="OpenRouter" />
  <img src="https://img.shields.io/badge/OPENAI%20SDK-412991?style=for-the-badge&logo=openai&logoColor=white" alt="OpenAI SDK" />
  <img src="https://img.shields.io/badge/MCP-000000?style=for-the-badge&logo=modelcontextprotocol&logoColor=white" alt="Model Context Protocol" />
  <img src="https://img.shields.io/badge/PYDANTIC-E92063?style=for-the-badge&logo=pydantic&logoColor=white" alt="Pydantic" />
  <br />
  <img src="https://img.shields.io/badge/RICH-2b2b2b?style=for-the-badge&logoColor=white" alt="Rich" />
  <img src="https://img.shields.io/badge/CLICK-d1d1d1?style=for-the-badge&logoColor=black" alt="Click" />
  <img src="https://img.shields.io/badge/DOCKER-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
</p>

Postal, an open-source AI coding agent that runs in your terminal. It connects to LLMs through OpenRouter, reads and edits your code with a built-in tool set, runs shell commands, and streams everything through a full-screen TUI.

<p align="center">
  <img src="assets/postaldemo.gif" alt="Postal planning and executing a multi-step task in the terminal" width="100%" />
</p>

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
| **OpenRouter backend** | Authenticate once with `postal login` (browser OAuth) or paste an API key. Model, temperature, and context window are configurable in `~/.config/postal/config.toml`, with per-project overrides in `.postal/config.toml`. |

## Getting started

```bash
# 1. Install Postal
pip install postalcli

# 2. Log in (opens your browser to authorize with OpenRouter)
postal login
postal login --paste   # or paste an API key directly

# 3. Run it
postal                 # interactive mode
postal "your prompt"   # single-shot mode
postal --cwd /path     # run against a different working directory

# Remove the saved API key
postal logout
```

## Project instructions (`AGENTS.md`)

Drop an `AGENTS.md` at the root of your repo and Postal loads it as developer instructions at startup, use it for build and test commands, code style, or anything else the agent should know before touching your code

Postal walks up from the working directory to the repository root, so running `postal` inside a subdirectory still picks up the root file. Every `AGENTS.md` found along the way is included, ordered outermost first.

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
- **Approval flow**: prompting before file edits and shell commands is in place; still to come is switching the mode mid-session and extending confirmations to sub-agents.

## License

[GNU GENERAL PUBLIC LICENSE v3.0](LICENSE)

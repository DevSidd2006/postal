<h1 align='center'>
  Postal
</h1>

<p align="center">
  <b>An open-source AI coding agent that lives in your terminal.</b><br />
  Plans, edits, runs, and reviews code with any model on OpenRouter.
</p>

<p align="center">
  <a href="https://github.com/andrefetch/postal/stargazers"><img src="https://img.shields.io/github/stars/andrefetch/postal?style=for-the-badge&logo=github&logoColor=white&color=181717" alt="GitHub stars" /></a>
  <a href="https://github.com/andrefetch/postal/network/members"><img src="https://img.shields.io/github/forks/andrefetch/postal?style=for-the-badge&logo=github&logoColor=white&color=181717" alt="GitHub forks" /></a>
  <a href="https://github.com/andrefetch/postal/issues"><img src="https://img.shields.io/github/issues/andrefetch/postal?style=for-the-badge&logo=github&logoColor=white&color=181717" alt="GitHub issues" /></a>
</p>

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

<p align="center">
  <img src="assets/postalnewdemo.gif" alt="Postal planning and executing a multi-step task in the terminal" width="100%" />
</p>

Postal connects to LLMs through OpenRouter, reads and edits your code with a built-in tool set, runs shell commands, delegates to specialized sub-agents, and streams everything through a full-screen TUI. Every mutating action goes through an approval policy you control, so it is as autonomous or as careful as you want it to be.

## Quickstart

Two commands and you are talking to an agent in your own repo:

```bash
pip install postalcli
postal login    # opens your browser to authorize with OpenRouter
postal          # start the interactive TUI
```

More ways to run it:

```bash
postal "your prompt"     # single-shot mode, great for scripting
postal --cwd /path       # run against a different working directory
postal --continue        # pick up the last session in this directory
postal --resume 3f2a1c   # resume a specific session by id
postal sessions          # list saved sessions
```

Configuration lives in `~/.config/postal/config.toml`, with per-project overrides in `.postal/config.toml`, and `AGENTS.md` is picked up automatically.

Full [CLI reference](docs/cli.md) · [configuration reference](docs/configuration.md)

## Documentation

| Page | What it covers |
| --- | --- |
| [CLI reference](docs/cli.md) | Installing, logging in, every command and flag |
| [Configuration](docs/configuration.md) | `config.toml`, per-project overrides, `AGENTS.md`, every option |
| [Tools](docs/tools.md) | The built-in tool set, sub-agents, MCP servers |
| [Approvals](docs/approvals.md) | The six approval policies and the rules that override them |
| [Sessions](docs/sessions.md) | Saving, resuming, checkpointing and rewinding conversations |
| [Slash commands](docs/slash-commands.md) | Everything you can type after a `/` inside the TUI |
| [Architecture](docs/architecture.md) | How the codebase is put together, class by class |
| [Technologies](docs/technologies.md) | The libraries Postal is built on and what each one does |

## Why Postal?

- **Bring any model.** OpenRouter as the backend means one login gives you Claude, GPT, Gemini, DeepSeek, open-weight models, and whatever ships next. No vendor lock-in.
- **Safety is a first-class feature.** Six approval policies, dangerous-command rejection, and confirmation for anything outside the working directory. You choose the risk level, not the agent. See [Approvals](docs/approvals.md).
- **It survives long sessions.** Context pruning reclaims tokens from stale tool output, and when the window fills up, Postal compacts history into a continuation brief and keeps going instead of erroring out.
- **Nothing is lost when you close the terminal.** Sessions are checkpointed after every turn, so `postal --continue` puts you back exactly where you were, and `/rewind` walks the conversation back to any earlier checkpoint. See [Sessions](docs/sessions.md).
- **Hackable by design.** A readable, object-oriented Python codebase built on Rich, Click, and Pydantic. Every tool is one class behind a shared abstract base, so adding a tool or a sub-agent is a small, well-marked change. See [Architecture](docs/architecture.md).
- **Component-based UI design.** Postal uses a modular, component-based UI system with separate components for every visual element (spinners, gutters, markdown rendering, tool displays, confirmations, etc.), making it easy to maintain, customize, and extend the interface.

## What it can do

| | |
| --- | --- |
| **Files** | `read`, `write`, `edit`, `apply_patch`, `grep`, `glob`, and `list_directories` for working with a codebase. `apply_patch` batches creates, updates, deletes and renames across several files into one all-or-nothing call. |
| **Shell** | The `shell` tool executes commands in the working directory. |
| **Planning** | A `plan` tool tracks steps (a todo list) across the agent loop. |
| **Network and memory** | Web search via DuckDuckGo, URL fetching, and key-value storage that survives across sessions. |
| **Sub-agents** | Specialized agents the main agent can delegate to: `codebase_investigator`, `code_reviewer`, `software_architect`, `test_writer`, `debugger`. |
| **MCP** | Connects to external MCP servers for additional tools and data sources. |
| **Interactive TUI** | Full-screen terminal interface built on Rich, with streaming responses, live tool call output, visible model reasoning, and token usage tracking. |
| **Single-shot mode** | Pass a prompt as an argument for non-interactive runs, suitable for scripting. |

Details in [Tools](docs/tools.md) and [Slash commands](docs/slash-commands.md).

## Roadmap

Currently being worked on:

- **Skill Integration** - allows users to import skills and use with their favorite model.
- **Git Integration** - allows users to use git commands with postal.
- **More assets** - Logo, banner, etc

Have an idea? [Open an issue](https://github.com/andrefetch/postal/issues), feature discussions are very welcome.

## Contributing

Contributions of every size are appreciated, from typo fixes to new tools and sub-agents. Read [CONTRIBUTING.md](CONTRIBUTING.md) to get started, and check the [open issues](https://github.com/andrefetch/postal/issues) for something to pick up!

If Postal is useful to you, **a star on the repo genuinely helps** the project reach more developers. ⭐

## License

[GNU GENERAL PUBLIC LICENSE v3.0](LICENSE)

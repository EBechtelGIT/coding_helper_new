# Coding Agent

A local coding agent built with Python and LangChain — multi-agent workflow, file ops, shell commands (opt-in), web search, session management, and more. Inspired by OpenCode.

## Features

- **Multi-agent system**: Switch between Build, Plan, and custom agents
- **Subagents**: Spawn specialized agents with `@general` and `@explore`
- **Permission system**: Fine-grained `allow/ask/deny` per tool category
- **Session management**: Persistent sessions, create/load/list/delete
- **Context compaction**: Auto-summarizes long conversations
- **File operations**: Read, write, edit, apply patches
- **File search**: Glob patterns, grep content search, directory listing
- **Shell & Git**: Bash commands, Python execution, git operations (opt-in)
- **Web tools**: DuckDuckGo search, URL content fetching
- **Todo tracking**: Structured task lists for multi-step work
- **Config system**: JSON config + AGENTS.md for project instructions
- **Multi-provider**: Azure OpenAI, OpenAI, Anthropic support
- **Textual TUI**: Rich terminal UI with real-time streaming output

## Install

### From local checkout

```bash
git clone <repo-url> /path/to/coding-agent
pip install -e /path/to/coding-agent
```

### With uv (recommended)

```bash
git clone <repo-url> /path/to/coding-agent
uv tool install /path/to/coding-agent
```

### From GitHub

```bash
pip install git+https://github.com/user/coding-agent.git
```

### Verify

```bash
coding-agent --help
```

## Usage

Run from any project directory:

```bash
cd /path/to/your-project
coding-agent
```

This launches the Textual TUI. For the readline CLI mode:

```bash
coding-agent --cli
```

With mock LLM for testing:

```bash
coding-agent --mock
```

### Command Line Options

| Flag | Description |
|------|-------------|
| `--cli` | Use CLI mode (readline) instead of TUI |
| `--mock` | Use mock LLM for testing |
| `--verbose` | Enable debug logging to stderr |
| `--max-iterations N` | Max tool-call iterations (default: 15) |
| `--no-color` | Disable colored output |
| `--plan` | Start with plan agent |
| `--auto-execute` | Skip plan approval |
| `--agent NAME` | Start with specific agent |
| `--session ID` | Load existing session |
| `--no-compaction` | Disable context compaction |
| `--max-messages N` | Max messages before compaction (default: 50) |
| `--allow-bash` | Enable bash/python/git tools |
| `--theme NAME` | TUI theme (opencode, dark, light) |

### Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/new [agent]` | Create new session |
| `/list` | List all sessions |
| `/load <id>` | Load a session |
| `/delete <id>` | Delete a session |
| `/clear` | Clear current session |
| `/switch <agent>` | Switch agent |
| `/agents` | List available agents |
| `/tools` | List available tools |
| `/permissions` | View/set permissions |
| `/compact` | Compact session context |
| `/session` | Show session info |
| `/exit`, `/quit` | Exit |

### Agents

| Agent | Mode | Description |
|-------|------|-------------|
| `build` | Primary | Default agent with all tools enabled |
| `plan` | Primary | Read-only agent for analysis and planning |
| `general` | Subagent | Full-access agent for multi-step tasks |
| `explore` | Subagent | Read-only agent for codebase exploration |

### Tools

| Tool | Category | Description |
|------|----------|-------------|
| `read_file` | read | Read file contents |
| `write_file` | edit | Write content to a file |
| `edit_file` | edit | Replace text in a file |
| `apply_patch` | edit | Apply a unified diff patch |
| `glob_search` | glob | Find files by glob pattern |
| `grep_search` | grep | Search file contents with regex |
| `list_files` | list | List directory contents |
| `run_bash` | bash | Execute bash commands (opt-in) |
| `run_python` | python | Execute Python code (opt-in) |
| `run_git` | git | Run git commands (opt-in) |
| `web_search` | web | Search the web via DuckDuckGo |
| `web_fetch` | web | Fetch content from a URL |
| `todowrite` | todo | Create/update todo list |
| `todoread` | todo | Read current todo list |

Bash/python/git tools are disabled by default. Enable them with `--allow-bash` or set `"allow_bash": true` in `.coding-agent.json`.

### Planning Mode

```bash
coding-agent --plan
```

1. Agent researches with read-only tools
2. Creates a structured PLAN.md
3. Review: `approve`, `edit`, or `cancel`
4. Agent implements the approved plan

Auto-execute without approval:

```bash
coding-agent --plan --auto-execute
```

## Configuration

### API Key Setup

The agent loads `.env` from the current project directory. Copy the example and edit:

```bash
cp .env.example .env
```

For Azure OpenAI (default provider):

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your_key_here
AZURE_API_VERSION=2025-03-01-preview
```

For other providers see `.env.example` for all supported options.

### Config File

Create `.coding-agent.json` in your project root:

```json
{
  "provider": "azure",
  "model": "gpt-4o",
  "default_agent": "build",
  "allow_bash": false,
  "agent": {
    "build": {
      "model": "gpt-4o",
      "temperature": 0.3,
      "permission": {
        "edit": "allow",
        "bash": "ask"
      }
    },
    "code-reviewer": {
      "description": "Reviews code for quality",
      "mode": "subagent",
      "permission": {
        "edit": "deny",
        "bash": "deny"
      }
    }
  }
}
```

Config is merged from two locations (project overrides global):

| Location | Path | Purpose |
|----------|------|---------|
| Global | `~/.coding-agent/config.json` | User-wide defaults |
| Project | `<project>/.coding-agent.json` | Per-project overrides |

### AGENTS.md

Create `AGENTS.md` in your project root for project-specific instructions. These are appended to every agent's system prompt automatically.

## Session Storage

Sessions are stored in `<project>/.coding-agent/sessions/` as JSON files. History is persisted across restarts.

## Skills

Place `.md` files in `<project>/.opencode/skills/` to define reusable skills that are automatically appended to the system prompt. A default README skill is shipped with the package and auto-copied on first run.

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Development

```bash
git clone <repo-url>
cd coding-agent
pip install -e ".[dev]"
pytest tests/ -v
```

# Coding Agent

A local coding agent built with Python and LangChain, supporting multi-agent workflows, file operations, shell commands, web search, session management, and more. Inspired by OpenCode.

## Features

- **Multi-agent system**: Switch between Build, Plan, and custom agents
- **Subagents**: Spawn specialized agents with `@general` and `@explore`
- **Permission system**: Fine-grained `allow/ask/deny` per tool category
- **Session management**: Persistent sessions, create/load/list/delete
- **Context compaction**: Auto-summarizes long conversations
- **File operations**: Read, write, edit, apply patches
- **File search**: Glob patterns, grep content search, directory listing
- **Shell & Git**: Bash commands, Python execution, git operations
- **Web tools**: DuckDuckGo search, URL content fetching
- **Todo tracking**: Structured task lists for multi-step work
- **Config system**: JSON config + AGENTS.md for project instructions
- **Multi-provider**: Azure OpenAI, OpenAI, Anthropic support
- **Colored output**: ANSI colors with markdown rendering

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended)

## Setup

```bash
cd /Users/etienne/Desktop/helper_old/coding_helper
uv sync --group dev
```

## Usage

```bash
uv run coding-agent
```

Or with the mock LLM:
```bash
uv run coding-agent --mock
```

### Command Line Options

| Flag | Description |
|------|-------------|
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
| `run_bash` | bash | Execute bash commands |
| `run_python` | python | Execute Python code |
| `run_git` | git | Run git commands |
| `web_search` | web | Search the web via DuckDuckGo |
| `web_fetch` | web | Fetch content from a URL |
| `todowrite` | todo | Create/update todo list |
| `todoread` | todo | Read current todo list |

### Planning Mode

```bash
uv run coding-agent --plan
```

1. Agent researches with read-only tools
2. Creates a structured PLAN.md
3. Review: `approve`, `edit`, or `cancel`
4. Agent implements the approved plan

Auto-execute without approval:
```bash
uv run coding-agent --plan --auto-execute
```

## Configuration

### API Key Setup

```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```env
OPENAI_API_KEY=your_api_key_here
# For OpenAI direct:
# OPENAI_API_KEY=sk-...
# For Anthropic:
# ANTHROPIC_API_KEY=sk-ant-...
```

### Config File

Create `.coding-agent.json` in your project:

```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "default_agent": "build",
  "agent": {
    "build": {
      "model": "anthropic/claude-sonnet-4-20250514",
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

### AGENTS.md

Create an `AGENTS.md` file in your project root for project-specific instructions that get appended to every agent's system prompt.

## Session Storage

Sessions are stored in `.coding-agent/sessions/` as JSON files. History is persisted across restarts.

## Running Tests

```bash
uv run pytest tests/ -v
```

## Dependency Management

```bash
uv add <package>          # Add dependency
uv add --group dev <pkg>  # Add dev dependency
uv lock --upgrade         # Update lock file
uv run <command>          # Run in uv environment
```

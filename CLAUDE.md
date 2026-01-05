# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Alice is a ReAct-based intelligent agent framework combining a **Rust TUI** (Terminal User Interface), **Python logic engine**, and **Docker sandbox** for secure task execution. The architecture implements a three-tier isolation pattern: presentation (Rust), control (Python), and execution (containerized sandbox).

## Development Commands

### Python Environment Setup

The host machine requires minimal Python dependencies:
```bash
# Install host-side dependencies (agent.py, tui_bridge.py, config.py)
pip install openai python-dotenv

# Container dependencies (requirements.txt) are auto-installed during Docker build
```

### Building and Running

```bash
# Build and run the application (release mode recommended)
cargo run --release

# Build only (debug mode)
cargo build

# Build release binary
cargo build --release
```

**Note**: The project uses Rust edition 2024 (released February 2025 with Rust 1.85). Ensure your Rust toolchain is up to date (`rustup update`).

**Important constraints**:
- Rust TUI spawns Python subprocess via `subprocess.Popen()` - if bridge crashes, entire system fails (no watchdog)
- `tui_bridge.py` must be executable from current working directory (hardcoded path in `main.rs:165`)
- JSON protocol is **line-buffered** - Python must call `sys.stdout.flush()` after each message
- Subprocess communication is **synchronous** - TUI blocks on Python response

### Docker Management

```bash
# Build the sandbox image manually (auto-built on first run)
docker build -t alice-sandbox:latest -f Dockerfile.sandbox .

# Check container status
docker ps -a --filter name=alice-sandbox-instance

# Stop/remove container if needed
docker stop alice-sandbox-instance
docker rm alice-sandbox-instance

# Rebuild container from scratch
docker rmi alice-sandbox:latest
```

### Testing Skills

```bash
# List available skills
# In the TUI, send: toolkit list

# Refresh skill registry (discovers new skills)
# In the TUI, send: toolkit refresh
```

## Architecture

### Three-Layer Design

1. **TUI Layer (Rust)**: `src/main.rs`
   - Built with Ratatui for terminal rendering
   - Handles user input, message display, thinking process visualization
   - Communicates with Python bridge via stdin/stdout JSON protocol
   - Real-time streaming display with auto-scroll
   - Mouse support: scroll wheel navigation in chat and sidebar areas
   - Keyboard shortcuts:
     - **Enter**: Send message
     - **Esc**: Interrupt current operation (sets `interrupted` flag in agent state)
     - **Ctrl+O**: Toggle thinking sidebar visibility
     - **Ctrl+C**: Quit application
     - **Up/Down**: Manual scroll (disables auto-scroll)

2. **Logic Engine (Python)**: `agent.py` + `tui_bridge.py`
   - `agent.py`: Core state machine, memory management, built-in command interception
   - `tui_bridge.py`: Bridges TUI ↔ Agent, manages streaming, parses thinking vs content
   - `snapshot_manager.py`: Auto-discovers skills, generates context snapshots
   - Implements multi-tier memory system (Working Memory, STM, LTM)

3. **Sandbox (Docker)**: `Dockerfile.sandbox`
   - Ubuntu 24.04 with Python venv, Node.js, Playwright
   - Persistent container (`alice-sandbox-instance`) with volume mounts
   - Only mounts `skills/` and `alice_output/` (isolates prompts, memory, source code)
   - All task execution happens inside this container
   - **Security note**: Container currently runs as root inside (no `USER` directive in Dockerfile)

### Communication Protocol

**Rust ↔ Python**: JSON messages over stdin/stdout
- `{"type": "status", "content": "..."}` - Agent state updates (displayed in status line)
- `{"type": "thinking", "content": "..."}` - Thinking content (routed to sidebar)
- `{"type": "content", "content": "..."}` - Response content (routed to main chat)
- `{"type": "tokens", "total": N, "prompt": M, "completion": K}` - Token usage (displayed in TUI footer)
- `{"type": "error", "content": "..."}` - Error messages

**Python → Agent**: Text streaming with special markers
- Thinking sections: `<thought>...</thought>`, `<reasoning>...</reasoning>`, `<thinking>...</thinking>`, or triple backticks
- Content sections: Normal text outside thinking markers
- Built-in commands: Intercepted before LLM call (see Built-in Commands section)

**Interrupt Mechanism**: When user presses Esc, the TUI sends a thread-safe signal to stop streaming. The agent checks `self.interrupted` flag during tool execution and LLM streaming to gracefully halt operations.

### Memory System

Four-tier memory hierarchy managed by `agent.py`:

1. **Working Memory** (`memory/working_memory.md`): Last 30 rounds of conversation (configurable via `WORKING_MEMORY_MAX_ROUNDS`)
2. **Short-Term Memory (STM)** (`memory/short_term_memory.md`): Recent facts, discoveries, progress notes
3. **Long-Term Memory (LTM)** (`memory/alice_memory.md`): Persistent lessons, user preferences, critical insights
4. **Todo List** (`memory/todo.md`): Active task tracking

Memory is automatically injected into context at each turn. The system auto-prunes Working Memory when it exceeds the round limit.

### Skill System

Skills are auto-discovered from `skills/` directory:
- Each skill is a folder containing `SKILL.md` (YAML frontmatter + Markdown)
- Required YAML fields: `name`, `description`
- Optional: `license`, `allowed-tools`, `metadata`
- `SnapshotManager` scans skills on startup and provides summaries to reduce context

**Important**: Always read `SKILL.md` before invoking a skill, as different LLM models may use tools differently.

## Built-in Commands

These commands are intercepted by `agent.py` and executed on the host (not in the sandbox):

```bash
# Memory management
memory "content to remember"           # Add to STM
memory "critical lesson" --ltm         # Add to LTM

# Task tracking
todo "task description or update"      # Update todo.md

# Prompt modification
update_prompt "new system prompt"      # Update prompts/alice.md

# Skill registry
toolkit list                           # List available skills
toolkit refresh                        # Scan skills/ for new skills
```

## Configuration

Environment variables (`.env` file):
- `API_KEY`: Required - OpenAI-compatible API key
- `API_BASE_URL`: Default: `https://api-inference.modelscope.cn/v1/`
- `MODEL_NAME`: Required - Model identifier (e.g., `qwen-plus`, `gpt-4o`)
- `WORKING_MEMORY_MAX_ROUNDS`: Default: 30 - Conversation rounds to retain before auto-pruning

Paths (`config.py`):
- `DEFAULT_PROMPT_PATH`: `prompts/alice.md`
- `MEMORY_FILE_PATH`: `memory/alice_memory.md`
- `TODO_FILE_PATH`: `memory/todo.md`
- `SHORT_TERM_MEMORY_FILE_PATH`: `memory/short_term_memory.md`
- `WORKING_MEMORY_FILE_PATH`: `memory/working_memory.md`
- `ALICE_OUTPUT_DIR`: `alice_output/`

**Important**: All `.env` values are loaded via `python-dotenv`. Missing required variables will cause startup to fail with clear error messages.

## Key Implementation Details

### Data Flow Architecture

**User Input Flow**:
1. Rust TUI captures keystrokes → builds input string
2. On Enter: writes message to Python subprocess stdin
3. `tui_bridge.py` reads stdin → passes to `agent.py`
4. Agent processes (checks built-in commands → LLM API call → tool execution in Docker)
5. Response streams back through `StreamManager` → JSON messages to stdout
6. Rust TUI reads stdout → parses JSON → updates UI state → renders

**Tool Execution Flow**:
1. Agent receives tool call from LLM (e.g., Python script execution)
2. Writes script to temporary file inside Docker container via `docker exec`
3. Executes via `docker exec alice-sandbox-instance python /tmp/script.py`
4. Captures stdout/stderr, returns to LLM for processing
5. Skills directory (`skills/`) is mounted read-only in container for skill script access

### Stream Processing (`tui_bridge.py`)

The `StreamManager` class handles incremental text streaming with buffer-based lookahead to correctly classify content vs thinking sections. Key features:
- **Buffer Management**: Maintains a 10MB buffer with overflow protection to prevent OOM
- **Smart Prefix Retention**: Holds back partial tag matches at buffer boundaries to avoid mis-splitting
- **Multi-Tag Support**: Recognizes triple backticks and XML-style tags (`<thought>`, `<reasoning>`, `<thinking>`)
- **State Persistence**: Maintains `in_code_block` state across chunk boundaries for accurate parsing

### Container Management (`agent.py`)

The `_ensure_docker_environment()` method:
1. Validates Docker installation
2. Auto-builds sandbox image if missing
3. Starts persistent container with minimal volume mounts
4. Container runs indefinitely (`sleep infinity`) and executes commands via `docker exec`

### Thinking Display Logic

The TUI renders thinking content in a sidebar (toggled with Ctrl+O). Thinking sections are extracted by looking for:
- Triple backticks (```)
- `<thought>...</thought>`
- `<reasoning>...</reasoning>`
- `<thinking>...</thinking>`

Content sections appear in the main chat area.

**Important**: The `StreamManager` uses a **10MB buffer limit** (tui_bridge.py:29-34) to prevent OOM. If responses exceed this, older content is discarded. Consider this when generating large outputs.

### Memory Pruning Strategy

When Working Memory exceeds `WORKING_MEMORY_MAX_ROUNDS`:
1. Extract the oldest 50% of rounds
2. Send to LLM with summarization prompt
3. Append summary to STM
4. Delete processed rounds from Working Memory
5. Log operation to `alice_runtime.log`

## Critical Implementation Patterns

### Command Safety and Validation

The `is_safe_command()` method in `agent.py:431-436` provides **basic** command filtering:
- Currently only blocks `rm` commands
- Does NOT protect against: path traversal, privilege escalation, resource exhaustion, or compound commands
- When modifying security logic, test thoroughly as this is the primary defense layer

**Security Boundary**: Commands execute inside Docker container with `docker exec`, NOT on host. The container should run as non-root user (current Dockerfile lacks `USER` directive).

### Built-in Command Interception Pattern

Commands are intercepted in `execute_command()` (agent.py:438-496) **before** LLM calls:
1. Check `is_safe_command()` first
2. Match against built-in command prefixes (`toolkit`, `update_prompt`, `todo`, `memory`)
3. Extract arguments using regex (`re.search(r'["\'](.?)["\']')`)
4. Execute on host (not in container)
5. Return result immediately without Docker exec

When adding new built-in commands, follow this interception pattern at agent.py:446-496.

### Error Handling Philosophy

The codebase uses **broad exception catching** (`except Exception as e`) in 9+ locations for simplicity. When debugging:
- Check `alice_runtime.log` for detailed tracebacks
- Most errors are logged but don't crash the system (graceful degradation)
- Critical failures (Docker missing, API key invalid) cause immediate exit via `sys.exit(1)`

### Stream Processing State Machine

`StreamManager` (tui_bridge.py:15-124) maintains critical state across chunk boundaries:
- `in_code_block`: Tracks whether currently inside triple backticks
- `current_end_tag`: Dynamically switches between `</thought>`, `</reasoning>`, `</thinking>`, or triple backticks
- **Buffer retention logic** (lines 93-118): Preserves partial tag matches to prevent splitting across boundaries

When modifying stream parsing, test with fragmented responses (partial tags at chunk boundaries).

## Special Workflow Notes

- **Alice Personality**: The system prompt (`prompts/alice.md`) defines a self-improving agent persona that actively uses memory commands and self-reflection
- **Persona Update**: Alice can modify her own system prompt via `update_prompt` command
- **Skill Development**: Follow `agent-skills-spec_cn.md` for skill creation guidelines (YAML frontmatter: `name`, `description` required; `license`, `allowed-tools`, `metadata` optional)
- **Docker Isolation**: Source code, prompts, and memory files are NOT mounted in the container - only skills and output directory
- **AI-Generated Disclaimer**: Per README.md, all code is AI-generated. Users must evaluate security risks and logic defects before deployment

## Common Development Tasks

### Adding a New Skill

1. Create folder in `skills/my-new-skill/`
2. Add `SKILL.md` with proper YAML frontmatter
3. Include scripts/resources as needed
4. Run `toolkit refresh` in TUI to register

### Modifying System Prompt

Either:
- Edit `prompts/alice.md` directly, OR
- Use `update_prompt "content"` command in TUI

### Debugging Stream Processing

Check `alice_runtime.log` for detailed logs from both `AliceAgent` and `TuiBridge` loggers.

### Container Dependencies

If sandbox needs new Python packages:
1. Add to `requirements.txt`
2. Rebuild container: `docker rmi alice-sandbox:latest && cargo run --release`

Container will auto-rebuild with new dependencies on next startup.

### Python Bridge Development

The `tui_bridge.py` module runs as a subprocess spawned by the Rust TUI:
- Handles stdin (user messages) → agent processing → stdout (JSON responses)
- Run manually for debugging: `python tui_bridge.py` (reads from stdin, outputs JSON)
- Check `alice_runtime.log` for Python-side logs from both `AliceAgent` and `TuiBridge` loggers

### Debugging Workflow

**Common debugging scenarios**:

1. **TUI rendering issues**: Check Rust panic messages in terminal, review `src/main.rs` UI layout logic
2. **Stream parsing problems**: Enable verbose logging in `tui_bridge.py`, inspect `StreamManager` buffer state
3. **Docker execution failures**: Verify container is running (`docker ps -a --filter name=alice-sandbox-instance`), check container logs (`docker logs alice-sandbox-instance`)
4. **Memory system issues**: Manually inspect files in `memory/` directory, verify date formats match `## YYYY-MM-DD` pattern
5. **Skill not loading**: Run `toolkit refresh` in TUI, check `alice_runtime.log` for `SnapshotManager` errors

**Log locations**:
- Python logs: `alice_runtime.log` (both `AliceAgent` and `TuiBridge` loggers)
- Container stdout: Captured inline in tool execution responses
- Rust panics: Printed to terminal stderr

### Rust Development

**No testing framework configured**. To add tests:
```bash
# Add tests in src/main.rs or create tests/ directory
cargo test

# Run with clippy for lints (not configured by default)
cargo clippy

# Format code (no .rustfmt.toml configured)
cargo fmt
```

**Key Rust patterns used**:
- `Result<(), Box<dyn Error>>` for error propagation
- `mpsc::channel()` for thread-safe TUI ↔ subprocess communication
- `Mutex<Arc<T>>` for shared interrupt flag (`app.interrupted`)

### Python Development

**No testing framework configured**. To add tests:
```bash
# Install pytest (not in requirements.txt)
pip install pytest

# Create tests/ directory and run
pytest tests/

# Type checking (mypy not configured)
pip install mypy
mypy agent.py tui_bridge.py
```

**Critical Python patterns**:
- `subprocess.Popen()` used in `main.rs:165` to spawn `tui_bridge.py`
- `sys.stdout.flush()` required after each JSON message for TUI to receive immediately
- Context managers (`with open()`) used inconsistently - some file operations use manual `close()`

### Container Environment Inspection

```bash
# Shell into running container
docker exec -it alice-sandbox-instance bash

# Check Python environment
docker exec alice-sandbox-instance python --version

# List installed packages
docker exec alice-sandbox-instance pip list

# Test skill script directly
docker exec alice-sandbox-instance python /workspace/skills/my-skill/script.py
```

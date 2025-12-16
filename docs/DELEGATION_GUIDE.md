# Delegation Guide - Alabama Auction Watcher

## Overview

This project uses Claude (Opus) for orchestration and Gemini for implementation tasks via PAL MCP.

## Delegation Workflow

1. **Claude explores and plans** - Reads files, understands requirements
2. **Claude delegates implementation to Gemini** via `mcp__pal__clink`
3. **Gemini executes the task** - Writes code, creates files
4. **Claude reviews output quality** - Validates changes
5. **Claude commits validated changes** - With descriptive messages

## Using clink for Delegation

```python
mcp__pal__clink(
    cli_name="gemini",
    prompt="Your implementation task here...",
    absolute_file_paths=["c:/auction/path/to/file.py"],
    role="default"  # or "codereviewer", "planner"
)
```

### Available Roles

- **default**: General implementation tasks
- **codereviewer**: Code review and quality analysis
- **planner**: Architecture and planning tasks

## When to Delegate to Gemini

- Writing new test files
- Implementing straightforward features
- Bulk code modifications
- Documentation generation
- Refactoring tasks with clear patterns

## When to Keep in Claude

- Architecture decisions
- Code review gates (final approval)
- Complex debugging requiring deep context
- User communication
- Security-sensitive changes
- Multi-step tasks requiring orchestration

## Project-Specific Delegation Patterns

### Scraping Tasks

```python
mcp__pal__clink(
    cli_name="gemini",
    prompt="Add support for scraping [specific county feature]...",
    absolute_file_paths=[
        "c:/auction/scripts/scraper.py",
        "c:/auction/config/settings.py"
    ]
)
```

### Dashboard Components

```python
mcp__pal__clink(
    cli_name="gemini",
    prompt="Create a new Streamlit component for [feature]...",
    absolute_file_paths=[
        "c:/auction/streamlit_app/app.py",
        "c:/auction/streamlit_app/components/example_component.py"
    ]
)
```

### Test Creation

```python
mcp__pal__clink(
    cli_name="gemini",
    prompt="Write unit tests for [module]...",
    absolute_file_paths=[
        "c:/auction/scripts/[module].py",
        "c:/auction/tests/unit/test_example.py",
        "c:/auction/tests/conftest.py"
    ]
)
```

## Critical Files Reference

| File | Purpose |
|------|---------|
| `scripts/parser.py` | Main CLI orchestrator |
| `scripts/utils.py` | Data processing utilities |
| `scripts/scraper.py` | ADOR web scraper |
| `streamlit_app/app.py` | Main dashboard |
| `tests/conftest.py` | Shared test fixtures |
| `config/settings.py` | Application settings |

## Database Operations

- **Database**: `alabama_auction_watcher.db` (SQLite)
- **Backup convention**: `alabama_auction_watcher.db.backup_YYYYMMDD_HHMMSS`
- Always create backup before bulk operations

## Testing Protocol

1. Run unit tests: `pytest tests/unit/ -v --tb=short`
2. Run integration tests: `pytest tests/integration/ -v`
3. Run E2E tests: `pytest tests/e2e/ -v -m "not network"`
4. Live validation: `python quick_validate.py`

## Commit Message Format

```
type: Brief description

- Bullet point details
- More details

Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

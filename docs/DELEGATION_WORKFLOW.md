# Delegation Workflow - Alabama Auction Watcher

A comprehensive guide to using Claude-Gemini multi-agent delegation for development tasks.

---

## Quick Start (Copy-Paste Ready)

```
Role: Orchestrator
Mode: NEW
Task: [Describe your task here]

Instructions:
1. Claude: Explore codebase, plan, delegate to Gemini
2. Gemini: Execute implementation via PAL clink
3. Claude: Review quality at milestones
4. Present results with continuation_id for future sessions

Priority: Quality over cost
```

---

## For Continuation Sessions

```
Role: Orchestrator
Mode: CONTINUE: [continuation_id]
Task: [Continue previous work]
```

---

## Role Definitions

### Claude (Orchestrator - Sonnet/Opus)
- Explore codebase and understand requirements
- Create task breakdown with cost estimates
- Delegate specific tasks to Gemini via PAL clink
- Review Gemini output at quality gates
- Run tests and validate changes
- Handle commits and user communication

### Gemini (Executor - via PAL MCP)
- Write implementation code
- Create test files
- Perform bulk refactoring
- Generate documentation

---

## Model Selection Guide

| Task Type | Model | Cost | When to Use |
|-----------|-------|------|-------------|
| Simple SQL, single file | gemini-2.5-flash | ~$0.02-0.05 | Config changes, migrations |
| Complex multi-file changes | gemini-2.5-pro | ~$0.05-0.20 | UI features, refactoring |
| Algorithm implementation | gemini-2.5-pro | ~$0.05-0.20 | Scoring, parsing logic |
| Test generation | gemini-2.5-pro | ~$0.05-0.15 | Comprehensive test suites |
| Documentation | gemini-2.5-flash | ~$0.02-0.05 | Comments, READMEs |

---

## Standard Delegation Pattern

### Step 1: Explore (Claude)
Read relevant files, understand current implementation, identify patterns.

### Step 2: Delegate (Claude -> Gemini)

```python
mcp__pal__chat(
    prompt="""
    TASK: [Clear, specific description]

    CONTEXT:
    - Project: Alabama Auction Watcher (c:/auction)
    - Framework: Streamlit + FastAPI + SQLite
    - Python 3.13

    REQUIREMENTS:
    1. [Specific requirement]
    2. [Expected behavior]

    PATTERNS TO FOLLOW:
    - See [reference_file.py] for style
    - Use existing utilities from scripts/utils.py

    OUTPUT:
    - Complete, working code
    - No placeholders
    """,
    absolute_file_paths=[
        "c:/auction/path/to/main/file.py",
        "c:/auction/path/to/reference.py"
    ],
    working_directory_absolute_path="c:/auction",
    model="gemini-2.5-pro"
)
```

Or use `mcp__pal__clink` for CLI-style delegation:

```python
mcp__pal__clink(
    cli_name="gemini",
    prompt="[Your detailed task description]",
    absolute_file_paths=["c:/auction/path/to/files"],
    role="default"
)
```

### Step 3: Validate (Claude)
```bash
python -m pytest tests/unit/ -v --tb=short
# Manual functionality check
```

### Step 4: Quality Gate
- [ ] Code compiles without errors
- [ ] Tests pass
- [ ] Functionality works as expected
- [ ] No regressions

### Step 5: Commit (Claude)
```bash
git add [files]
git commit -m "feat: [description]"
```

---

## Project-Specific Patterns

### Streamlit Dashboard
- Main app: `streamlit_app/app.py`
- Components: `streamlit_app/components/`
- Use `st.cache_data` for expensive operations
- Follow existing filter pattern in `create_sidebar_filters()`

### SQLite/SQLAlchemy
- Models: `backend_api/database/models.py`
- Use session management from `connection.py`
- Always close sessions properly

### Tests
- Unit tests: `tests/unit/`
- Fixtures: `tests/conftest.py`
- Factories: `tests/fixtures/data_factories.py`
- Mark AI tests with `@pytest.mark.ai_test`

### Scoring/Utils
- Core utilities: `scripts/utils.py`
- Water detection: `calculate_water_score()`
- Investment scoring: `calculate_investment_score()`
- Config: `config/settings.py`

---

## Quality Gates Checklist

### Before Delegation
- [ ] Understood the requirement
- [ ] Identified files to modify
- [ ] Found reference patterns to follow

### After Each Task
- [ ] Code imports without errors
- [ ] Tests pass
- [ ] Functionality verified

### Before Commit
- [ ] All quality gates passed
- [ ] Descriptive commit message
- [ ] No secrets in code
- [ ] No debug/test code left

---

## PAL MCP Tool Reference

### Available Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `mcp__pal__chat` | General chat with file context | Simple implementations |
| `mcp__pal__clink` | CLI-style delegation | Complex multi-step tasks |
| `mcp__pal__thinkdeep` | Deep analysis | Architecture decisions |
| `mcp__pal__debug` | Root cause analysis | Bug investigation |
| `mcp__pal__codereview` | Code review | Quality validation |
| `mcp__pal__testgen` | Test generation | Creating test suites |
| `mcp__pal__refactor` | Refactoring analysis | Code smell detection |
| `mcp__pal__analyze` | Code analysis | Understanding patterns |

### Example: Using thinkdeep for Complex Problems

```python
mcp__pal__thinkdeep(
    step="Analyzing the water detection algorithm for potential improvements",
    step_number=1,
    total_steps=2,
    next_step_required=True,
    findings="Initial analysis shows...",
    relevant_files=["c:/auction/scripts/utils.py"],
    model="gemini-2.5-pro"
)
```

---

## Troubleshooting

### Gemini returns incomplete code
- Provide more specific requirements
- Include reference file paths
- Break task into smaller pieces

### Tests fail after changes
- Check test expectations match implementation
- Verify fixtures are up to date
- Run specific test file: `pytest tests/unit/test_file.py -v`

### Database issues
- Backup before changes: `copy alabama_auction_watcher.db alabama_auction_watcher.db.backup`
- Check connection in `backend_api/database/connection.py`
- Verify models match database schema

### Gemini CLI can't access files
- Use `mcp__pal__chat` instead of `mcp__pal__clink`
- Provide file content in prompt if needed
- Use `absolute_file_paths` parameter

---

## Cost Tracking

Track cumulative cost per session:
- Simple session (1-2 tasks): $0.05-0.15
- Medium session (3-5 tasks): $0.15-0.50
- Complex session (5+ tasks): $0.50-1.50

Save `continuation_id` for multi-session workflows.

---

## Example Session Flow

```
1. User: "Add sorting to the dashboard"

2. Claude: Explores app.py, understands filter structure
   - Reads create_sidebar_filters() function
   - Identifies where to add sort dropdown

3. Claude: Delegates to Gemini
   mcp__pal__chat(
     prompt="Add sort dropdown to Streamlit sidebar...",
     absolute_file_paths=["c:/auction/streamlit_app/app.py"],
     model="gemini-2.5-pro"
   )

4. Claude: Reviews Gemini output
   - Applies suggested code changes
   - Runs tests to verify

5. Claude: Reports results
   - Sort functionality added
   - Tests passing
   - continuation_id: abc123def456
```

---

## Critical Files Reference

| File | Purpose |
|------|---------|
| `backend_api/database/models.py` | SQLAlchemy models |
| `streamlit_app/app.py` | Main dashboard UI |
| `scripts/utils.py` | Utility functions (scoring, parsing) |
| `scripts/parser.py` | Data parsing and processing |
| `config/settings.py` | Configuration constants |
| `tests/conftest.py` | Shared test fixtures |

---

## Best Practices

1. **Start small**: Test delegation with simple tasks first
2. **Be specific**: Detailed prompts get better results
3. **Include context**: Always provide reference files
4. **Validate incrementally**: Check after each task, not just at the end
5. **Save continuation_ids**: For resuming multi-session work
6. **Use Flash for simple tasks**: Save Pro for complex work
7. **Review before commit**: Claude should always verify Gemini's output

---

## Session Summary Template

At the end of each session, record:

```markdown
## Session: [Date]

### Tasks Completed
- [Task 1]
- [Task 2]

### Files Modified
- path/to/file1.py
- path/to/file2.py

### Cost
- Gemini Flash: $X.XX
- Gemini Pro: $X.XX
- Total: $X.XX

### Quality Metrics
- Tests: X/Y passing
- No regressions

### continuation_id
[id for resuming]

### Next Steps
- [Remaining work]
```

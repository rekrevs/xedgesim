# Multi-Agent Task Delegation Protocol

This directory facilitates task delegation between two Claude Code instances:
- **Developer Agent** (no Docker) - Implementation and planning
- **Testing Agent** (has Docker/Colima) - Testing and debugging

## Directory Structure

```
claude/
├── tasks/          # Pending tasks for testing agent
│   └── TASK-*.md   # Individual task files
├── results/        # Completed task results
│   └── TASK-*.md   # Test results and documentation
└── README.md       # This file
```

## Workflow

### Developer Agent Creates Task

When developer agent needs Docker testing:

1. **Create task file:** `claude/tasks/TASK-NAME.md`
2. **Commit and push:**
   ```bash
   git add claude/tasks/TASK-NAME.md
   git commit -m "task: Delegate TASK-NAME"
   git push
   ```
3. **STOP** and notify user to switch to testing agent

### User Switches to Testing Agent

User tells testing agent:
```
Do the task in claude/tasks/TASK-NAME.md
```

### Testing Agent Processes Task

1. **Read task file:** `cat claude/tasks/TASK-NAME.md`
2. **Run tests** as specified
3. **Debug issues** if tests fail
4. **Fix code** if needed
5. **Document results:** Create `claude/results/TASK-NAME.md`
6. **Commit and push:**
   ```bash
   git add [any fixes] claude/results/TASK-NAME.md
   git commit -m "fix: [description]" (if code fixed)
   git commit -m "test: Complete TASK-NAME"
   git push
   ```

### User Switches Back to Developer Agent

User tells developer agent:
```
Pull and continue
```

### Developer Agent Resumes

1. **Pull results:** `git pull`
2. **Read results:** `cat claude/results/TASK-NAME.md`
3. **Review status:** ✅ SUCCESS / ❌ FAILED / ⚠️ PARTIAL
4. **Continue work** based on results

## Task File Format

See `tasks/TASK-M2A-docker-tests.md` for example.

Required sections:
- **Status:** PENDING (set by developer agent)
- **Context:** Why this task is needed
- **Your Task:** Clear instructions
- **Expected Results:** Success criteria
- **If Tests Fail:** Debugging guidance
- **Document Results:** Results file template
- **Deliverables:** Commit checklist

## Results File Format

Required sections:
- **Status:** ✅ SUCCESS / ❌ FAILED / ⚠️ PARTIAL
- **Test Results:** Full output
- **Issues Found:** Problems discovered
- **Fixes Applied:** Code changes made
- **Commits Made:** Git log
- **Next Steps:** Guidance for developer agent

## Benefits

- **Parallel work:** Developer continues planning while tests run
- **Clear handoff:** Explicit task files, no ambiguity
- **Documentation:** Results are automatically documented
- **Git-based:** Uses existing VCS, no special tools
- **Debugging:** Testing agent fixes issues immediately

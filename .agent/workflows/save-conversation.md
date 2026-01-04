---
description: Save a conversation summary with session details, dashboard run instructions, and restoration guide
---

# Save Conversation Summary

This workflow saves a summary of the current conversation to `docs/conversation-summaries/`.

## Steps

1. **Create summary file** with the following sections:
   - Session metadata (date, duration, conversation ID if available)
   - User's main objective
   - Key accomplishments (commits, files changed, features added)
   - Decisions made
   - Open items or next steps
   - Dashboard Setup & Run Instructions (always include)
   - How to Restore This Conversation (always include)
   - Pro Tip for Future Sessions (always include)

2. **File naming convention:**
   ```
   docs/conversation-summaries/YYYY-MM-DD_<brief-topic>.md
   ```

3. **Template structure:**

```markdown
# Conversation Summary: [Topic]

**Date:** YYYY-MM-DD
**Conversation ID:** [if available]

## User Objective
[Brief description of what the user wanted to accomplish]

## Key Accomplishments
- [Commit hash] - [Description]
- [Files changed/created]

## Decisions Made
- [Key decisions and rationale]

## Open Items / Next Steps
- [ ] [Remaining tasks]

---

# Dashboard Setup & Run Instructions

[Include full setup instructions]

---

# How to Restore This Conversation in a New Session

## Option 1: Quick Context Load (Recommended)
In your new conversation, paste:

\`\`\`
Please read the conversation summary at:
docs/conversation-summaries/[THIS_FILE_NAME].md

This contains context from our previous session including all commits,
files modified, key decisions, and setup instructions.

After reading, let me know you're ready to continue.
\`\`\`

## Option 2: Specific File Reference
If continuing work on specific features:

\`\`\`
Review these files to understand the current state:
- [List relevant source files from the session]
- [Include test files if applicable]

[Brief context about what was implemented]
\`\`\`

## Option 3: Git History Reference
For code-focused restoration:

\`\`\`
Please review the recent git commits:
git log -10 --oneline

Key commits from this session:
- [commit1] - [description]
- [commit2] - [description]
\`\`\`

## Files That Preserve Context
| File | What It Contains |
|------|------------------|
| `docs/conversation-summaries/[THIS_FILE]` | Full session summary |
| `.agent/workflows/save-conversation.md` | Workflow template |
| `git log` | Commit history |

---

# Pro Tip: Saving Future Sessions

At the **end of each session**, ask the agent to save the conversation:

\`\`\`
Please save a summary of this conversation using the
.agent/workflows/save-conversation.md workflow
\`\`\`

This ensures context is always preserved for future sessions!
```

4. **Commit the summary:**
   ```bash
   git add docs/conversation-summaries/
   git commit -m "docs: add conversation summary for [topic]"
   ```

## Usage

At the end of a session, invoke this workflow to preserve context for future sessions.

## Required Sections Checklist

Every saved conversation MUST include:
- [ ] Session metadata
- [ ] User objective
- [ ] Key accomplishments with commit hashes
- [ ] Decisions made
- [ ] Open items / next steps
- [ ] Dashboard Setup & Run Instructions
- [ ] How to Restore This Conversation (all 3 options)
- [ ] Pro Tip for Future Sessions

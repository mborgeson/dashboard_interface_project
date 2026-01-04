---
description: Save a conversation summary with session details and dashboard run instructions
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

[Include full setup instructions from the standard template]
```

4. **Commit the summary:**
   ```bash
   git add docs/conversation-summaries/
   git commit -m "docs: add conversation summary for [topic]"
   ```

## Usage

At the end of a session, invoke this workflow to preserve context for future sessions.

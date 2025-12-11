# SPARC Agent Swarm Task Template

Use this template when initiating complex multi-agent workflows.

---

## Task Overview
[Provide a clear, concise description of what you want to accomplish]

## Objective
[State the specific end goal or deliverable]

## Context
- **Project**: Dashboard Interface (Real Estate Underwriting)
- **Frontend**: React 19, TypeScript, TailwindCSS, Radix UI
- **Backend**: FastAPI, Python, SQLAlchemy
- **Testing**: Vitest (unit), Playwright (E2E), Pytest (backend)

[Include any additional relevant background information, constraints, or requirements]

## Steps to Complete

1. **Analysis Phase**
   - [ ] Review existing implementation
   - [ ] Identify dependencies and impacts
   - [ ] Document current state

2. **Implementation Phase**
   - [ ] [Specific implementation tasks]
   - [ ] [Additional tasks as needed]

3. **Testing Phase**
   - [ ] Unit tests (Vitest)
   - [ ] Integration tests
   - [ ] E2E tests (Playwright) if applicable

4. **Documentation Phase**
   - [ ] Update relevant documentation
   - [ ] Add inline comments where needed

## Input Materials
- [ ] Relevant source files: [list files]
- [ ] API documentation: [if applicable]
- [ ] Design specs: [if applicable]

## Expected Output Format
- **Code**: TypeScript/Python following project conventions
- **Tests**: Coverage for new functionality
- **Documentation**: Updated as needed

## Success Criteria
- [ ] All tests pass
- [ ] No TypeScript/ESLint errors
- [ ] Code review approved
- [ ] Documentation updated

## Agent Assignments (Auto-Selected)
- **Frontend Tasks** → `frontend` specialist (React, TypeScript)
- **Backend Tasks** → `backend` specialist (FastAPI, Python)
- **Testing Tasks** → `testing` specialist (Vitest, Playwright, Pytest)

## Questions to Address
1. [Key question that needs answering]
2. [Another important question]

---

## Quick Start Commands

```bash
# Initialize swarm with this task
npx claude-flow task orchestrate "[TASK_DESCRIPTION]" --priority [low|medium|high|critical]

# Monitor progress
npx claude-flow swarm status

# View task results
npx claude-flow task results [TASK_ID]
```

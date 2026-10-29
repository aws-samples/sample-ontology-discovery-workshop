---
inclusion: always
---

# OntoForge Final Graph Evaluation

Apply when the user enters `/ontoforge-evaluation`, requests final graph/schema evaluation,
requests schema comparison, or reaches the final workshop post-export step.
The slash phrase is a conversational trigger, not a native Kiro command registration.
For unrelated work, keep this rule as background context only.

This file is only an entry point. Read `.claude/skills/graph-evaluation/SKILL.md` in full and
follow every section. That file is the single source of truth for the procedure, metrics, report
structure, style, and wording. Do not restate or override its rules here; change them there.

Run it LAST in the workshop (after modeling, gates, exports, and deliverable verification), on the
current workshop's final `workshop-model.json` or the explicitly selected models.

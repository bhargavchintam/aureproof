# Aureproof — one-page positioning (for interviews)

**Problem.** Agent-evaluation results are hard to trust and hard to re-check.
Graders and tasks break silently — public audits in 2026 found large shares of
widely used benchmark tasks flawed. Regression calls are made on noise. And for
security agents, false alarms are now a documented cost: maintainers and bug
bounty platforms have changed policies because of low-quality AI-generated reports.

**For whom.** Eval engineers deciding whether a change is a real regression;
security-agent builders who need their false-alarm rate on code they control;
benchmark maintainers who need to know which tasks are broken.

**What it is.** An open-source integrity layer on top of the eval runners teams
already use (Inspect first). It certifies three things:

1. **The instrument** — a task-health record proves each task's grader works
   (it confirms a known defect, rejects the repaired version, and cannot be
   gamed by an empty or "flag everything" submission) before the task counts.
2. **The record** — a signed evidence bundle anyone can verify and re-score
   offline, without calling a model.
3. **The decision** — a pre-registered pass / fail / **inconclusive** gate that
   uses statistics suited to small task suites, so noise is reported as noise.

**How it's different.** Existing tools check tasks once at admission, re-score
logs, or compute error bars — separately. Aureproof combines persistent task
health, signed re-scorable results, and a pre-registered three-way decision in
one tool, and its flagship benchmark scores false alarms, not just hits.

**What it is not.** Not another runner, leaderboard, or proof of real-world
capability — v0.1 uses small synthetic fixtures that measure controlled skills.

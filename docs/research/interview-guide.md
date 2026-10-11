# Practitioner interview guide (M0 demand gate)

Issue #6 (AP-032). Goal: learn whether practitioners would actually use
task-health records, signed re-scorable bundles, or a pass/fail/inconclusive
gate on **their own** evaluation results — before M1 code is written.

## Who to talk to (3–5 people, at least one per row if possible)

| Persona | Signal to look for |
| --- | --- |
| Eval engineer (lab, AI safety institute, platform team) | Has shipped or blocked a model/agent change on eval results |
| Security-agent builder | Ships a tool that reports vulnerabilities; fields false-alarm complaints |
| Benchmark maintainer | Maintains tasks others run; has fixed broken tasks after release |

## Before the call

- Ask permission to take notes; say notes will be anonymized and quotes used only with consent.
- Do not send the positioning page in advance; show it at step 4.

## Script (30 minutes)

1. **Context (5 min).** "Walk me through the last time an eval result changed a decision — what was compared, and who signed off?"
2. **Current practice (8 min).**
   - How do you decide a regression is real and not noise? What do you report when it's unclear?
   - How do you find out a task or grader in your eval is broken? What happened last time?
   - Could someone outside your team re-check a published number? What would they need?
3. **Pain probes (7 min).** For each, ask for the most recent concrete example:
   - A result that turned out to be wrong because the task or grader was broken.
   - A comparison that was called a win but was within noise.
   - (Security) false-positive findings from an automated or AI tool — what did they cost?
4. **Reaction (7 min).** Show `positioning.md` and `mock-report.md` (say clearly it is a mock).
   - "What here would you use next month? What would you ignore?"
   - "Would you run this on your existing logs if it read Inspect/Harbor output directly?"
   - "What would make you distrust this report?"
5. **Close (3 min).** "Who else should I talk to?" and "May I follow up when there's a working version?"

## Avoid

- Pitching. Ask about past behavior, not hypothetical interest ("would you use…" alone is weak evidence).
- Leading questions that name the answer ("Don't you hate noisy evals?").

## Record (use `notes-template.md`, one file per interview)

Persona, team context, the concrete examples given, current workaround, the strongest
pull and strongest objection, and whether they'd try it on their own logs.

## Decision rule (record the result in ROADMAP.md)

- **Go** if at least 2 interviewees describe a recent, costly instance of the problem
  **and** would try the tool on their own logs.
- **Narrow** (to the benchmark + report only) if interest is limited to the fixture benchmark.
- **Rethink** if no one recognizes the problem from their own recent work.

# Team video script (about 80 seconds)

Before recording: make the terminal font large, open Aureproof_Pitch_Deck.pdf
at slide 4 ("Three checks, end to end"), and run demo.sh once as a warm-up.

## 1. Face to camera (about 20 s)

"Hi, I'm Bhargav. I'm building Aureproof, an open-source tool that checks AI
agent evaluations. When a team says their agent got better, there's usually no
way for anyone else to check that. The grader might be broken, the run can't be
re-checked, and a lucky result gets called a win."

## 2. Slide 4 on screen (about 10 s)

"Aureproof adds three checks: it proves each task's grader works, it seals the
run into a signed bundle, and it uses a gate that can say inconclusive."

## 3. Terminal: run ./demo.sh and press Enter after each step (about 40 s)

Step 1, validate. Point at "V5 signature pass" and then "VALID".
"This is a real Claude Code run. Its signature checks out offline, against the
signing workflow on main."

Step 2, score. Point at "re-score: reproduced", then at "known_defect_recall
3/3" and "strict_confirmed_yield 3/12".
"It re-scores to the same numbers with no API key. The agent found all three
planted bugs, but only 3 of its 12 findings were real. Recall alone would call
that perfect."

Step 3, compare. Point at "Outcome: inconclusive".
"This compares two real agent setups. Three runs each is not enough to call a
winner, so the gate says inconclusive instead of guessing."

The first line of step 1 is a note about TUF offline mode. It is normal; skip it.

## 4. Face to camera (about 10 s)

"I've built this solo over the last three weeks. Next I want teams who run
agent evals to try it on their own runs."

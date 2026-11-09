# Pitch deck

The deck and team video for the a16z speedrun application, November 2026.
Every number in the deck was checked against this repository on November 1, 2026:
104 commits on main, 791 tests collected and 90 merged pull requests.
Those counts will drift as work lands; the deck does not update itself.

- `Aureproof_Pitch_Deck.pdf` is the 10-slide version made for the application form.
  It merges the solution and flow slides and leaves out the architecture slide.
- `Aureproof-speedrun-deck.pdf` is the full 12-slide deck, one page per slide in its
  final state.
- `deck/` is the [HyperFrames](https://hyperframes.heygen.com) source. Present it
  with `npx hyperframes present docs/pitch/deck` and press P for speaker notes.
- `diagrams/` holds the [Archify](https://github.com/belinwu/archify) inputs for
  the two diagram slides, the architecture and the end-to-end flow. Each box cites
  the lines of code it stands for, at commit `8c99d4f`. Render one with
  `archify finalize architecture diagrams/architecture.json out.html --repo-root .`
  (or `workflow` for `flow.json`). The PNGs in `deck/assets/` are those renders.
- `diagrams/*.html` are the rendered, interactive versions of those two diagrams.
- `video/Aureproof_Team_Video.mp4` is the 80-second product demo. `video/source/` is
  its HyperFrames project, `video/script.md` is a script for recording it yourself
  and `video/demo.sh` runs the three demo commands from a checkout of this repo.
  The narration is a synthetic voice (Kokoro, run locally), not the founder's. The
  terminal screens are animations of real command output, and the gate screen
  trims its long lines.

The deck says what is not true yet as plainly as what is: there are no users,
design partners or revenue, and no benchmark result on real agents.

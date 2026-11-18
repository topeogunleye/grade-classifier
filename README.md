# Think-First Coach

A terminal coach that teaches you to **think through a problem before you code it**.
It never shows a solution. You climb a step ladder, and each step unlocks only after
you answer it in your own words.

Built for our group project, the **Student Grade Analyzer** (Python, standard library only):
a command-line tool that stores student scores, works out each average and letter grade,
ranks the class, and prints a neat report.

Stage 1 teaches the first building block: **the grade classifier** (and two pieces around it).

## Requirements

- Python 3.8 or newer
- Nothing else to install

Check your version:

```
python --version
```

On Windows you may need `py` instead of `python`. On macOS/Linux you may need `python3`.

## Quick start

```
git clone https://github.com/topeogunleye/grade-classifier
cd grade-classifier

```

You will see your schedule and the list of problems.

## The Stage 1 problems

| Problem id | What you build | Project piece it feeds |
|---|---|---|
| `grade-classifier` | Turn one score into a letter grade (A-F), or `Invalid` | Assign a letter grade |
| `top-of-three` | Print the highest of three numbers | Find the top student |
| `student-report` | Name + 3 scores -> `Ada: 88.3 (B)` | One report line per student |

Do them in that order. Each one reuses ideas from the one before.

## How to work through a problem

Use the problem id in every command. Example with `grade-classifier`:

1. **Climb the ladder.** `python coach.py start grade-classifier`
   Answer 6 prompts in your own words (restate, hand-work 2 examples, edge cases,
   brute-force idea, spot the pattern, plain-English plan). Press Enter on an empty
   line to finish an answer. Type `:q` to stop; your finished steps are saved.
2. **Get your plan reviewed.** `python coach.py show grade-classifier`
   Paste the output to your mentor or a teammate. They should ask questions about
   your plan, not fix it for you.
3. **Unlock coding.** `python coach.py approve grade-classifier`
   Only run this after the review. It is an honor-system gate: the coach cannot check it for you.
4. **Write your code.** `python coach.py code grade-classifier`
   This creates `solutions/grade_classifier.py`. Write your solution there.
5. **Test it.** `python coach.py test grade-classifier`
   You see PASS/FAIL per test, and the expected vs actual output for the first failures.
   Fix one failing case at a time.

Stuck? `python coach.py hint grade-classifier` gives the next of 3 levels
(nudge, then concept, then near-answer). You only get the next level when you ask.
Hints unlock after you finish steps 1-2 of the ladder, so try first.

## All commands

| Command | What it does |
|---|---|
| `python coach.py` | Schedule, progress, and a warning if you are behind |
| `python coach.py concept` | The concept for your current stage |
| `python coach.py start <id>` | Climb the ladder |
| `python coach.py show <id>` | Print your answers (to share for review) |
| `python coach.py approve <id>` | Unlock coding after your plan was reviewed |
| `python coach.py code <id>` | Create your solution file |
| `python coach.py test <id>` | Run the tests on your solution |
| `python coach.py hint <id>` | Next hint level |

## Rules for your solution files

- Use plain `input()` with **nothing inside the brackets**. A prompt such as
  `input("Enter score: ")` is printed too and makes the tests fail.
- Print exactly what the problem asks for, with the same spelling and capitals.
- Tests stop a run after 5 seconds, so an endless loop shows up as a timeout.

## Grade bands we agreed on

| Score | Grade |
|---|---|
| 90-100 | A |
| 80-89 | B |
| 70-79 | C |
| 60-69 | D |
| 0-59 | F |
| below 0 or above 100 | Invalid |

(If our team changes the bands, update `problems.json` and the tests together.)

## Done when (Stage 1)

- All 3 problems pass their tests.
- The ladder is complete for each one.
- You can explain, from memory and without looking, why 90 gives A but 89.9 gives B.

## Pacing

About 1 week for Stage 1 at 6-8 hours per week. Run `python coach.py` to see your due dates.
The coach warns you when you fall behind. Your start date is set the first time you run it.

## What is in this repo

| File | Purpose |
|---|---|
| `coach.py` | The coach itself. Commented so you can read it and learn from it |
| `problems.json` | Problem statements, examples, tests and hints (no solutions) |
| `progress.json` | Your own answers and progress. Created automatically; not committed |
| `solutions/` | Your own solution files. Created automatically; not committed |

`progress.json` and `solutions/` are in `.gitignore` on purpose: each teammate learns
on their own, and nobody spoils the answers for anyone else.

## Please don't

- Share finished solutions in the repo or chat before a teammate has solved it themselves.
- Skip the review step. The review is where most of the learning happens.

## Roadmap

Later stages are added one at a time, after the previous stage's "done when" check passes:
loops, lists and strings, functions (and a test runner), dicts, then stack and recursion.

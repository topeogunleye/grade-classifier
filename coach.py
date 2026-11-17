#!/usr/bin/env python3
"""Think-First Coach (Stage 1) - standard library only.

It walks you up a "step ladder" for each practice problem. You must answer
each step in your own words before the next one unlocks. It NEVER shows a
solution: problems.json holds only statements, tests and text hints.

Commands (run from this folder):
  python coach.py                 overview + schedule
  python coach.py concept         the concept for the current stage
  python coach.py start <id>      climb the ladder (steps 1-6)
  python coach.py show <id>       print your answers (paste to your mentor)
  python coach.py approve <id>    unlock coding after your plan was reviewed
  python coach.py code <id>       create your solution file
  python coach.py test <id>       run the tests on your solution
  python coach.py hint <id>       next hint (3 levels, one at a time)
"""
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROBLEMS_FILE = os.path.join(HERE, "problems.json")
PROGRESS_FILE = os.path.join(HERE, "progress.json")
SOLUTIONS_DIR = os.path.join(HERE, "solutions")

# The step ladder. Steps 1-6 are typed answers; 7 (code) and 8 (test) follow.
LADDER = [
    ("restate", "1. RESTATE", ["Say the problem in your own words. What goes IN? What comes OUT?"]),
    ("examples", "2. HAND-WORK 2 EXAMPLES",
     ["Example 1: pick an input and work out the answer by hand, step by step.",
      "Example 2: pick a DIFFERENT kind of input and do the same."]),
    ("edges", "3. EDGE CASES", ["List the odd or borderline inputs that could break a plan (one per line)."]),
    ("brute", "4. BRUTE FORCE", ["What is the slowest, most obvious way to get the answer? Clumsy is fine."]),
    ("pattern", "5. SPOT THE PATTERN", ["What do your examples share? What rule decides the output?"]),
    ("plan", "6. PLAIN-ENGLISH PLAN", ["Numbered steps a friend could follow without seeing Python. No code."]),
]
MIN_WORDS = 4  # a one-word answer like "idk" is not accepted
HINT_NAMES = ["nudge", "concept", "near-answer"]


# ---------- loading and saving ----------
def load_problems():
    with open(PROBLEMS_FILE, encoding="utf-8") as f:
        return json.load(f)


def today():
    # COACH_TODAY=YYYY-MM-DD lets you test the schedule; normally real today.
    override = os.environ.get("COACH_TODAY")
    if override:
        return datetime.date.fromisoformat(override)
    return datetime.date.today()


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except ValueError:  # damaged file: keep a copy, start fresh
            os.replace(PROGRESS_FILE, PROGRESS_FILE + ".bak")
            print("progress.json was damaged; saved a copy as progress.json.bak")
    return {"started": today().isoformat(), "problems": {}}


def save_progress(prog):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(prog, f, indent=1)


def pstate(prog, pid):
    """Your saved state for one problem (created on first use)."""
    return prog["problems"].setdefault(
        pid, {"answers": {}, "approved": False, "hints_used": 0, "attempts": 0, "passed": False})


def find_problem(data, token):
    for p in data["problems"]:
        if p["id"] == token:
            if not p["ready"]:
                sys.exit("'%s' is planned for Stage %d and is not built yet." % (token, p["stage"]))
            return p
    ids = ", ".join(p["id"] for p in data["problems"] if p["ready"])
    sys.exit("Unknown problem '%s'. Available: %s" % (token, ids))


# ---------- reading your answers ----------
def read_answer(prompt):
    """Read several lines; an empty line ends the answer. Returns None on quit."""
    print("\n" + prompt)
    print("  (type your answer; press Enter on an empty line when done; ':q' to stop)")
    lines = []
    while True:
        try:
            line = input("> ")
        except EOFError:
            return None
        if line.strip() == ":q":
            return None
        if line.strip() == "":
            if lines:
                break
            continue  # ignore blank lines before you start typing
        lines.append(line.rstrip())
    return "\n".join(lines)


def check_answer(text, key, previous):
    """Return a complaint string, or '' if the answer is acceptable."""
    if len(text.split()) < MIN_WORDS:
        return "Too short. Write at least %d words so a reviewer can follow you." % MIN_WORDS
    if text in previous:
        return "That is identical to an earlier answer. Think about THIS step."
    if key == "plan" and any(w in text for w in ("def ", "print(", "input(")):
        return "That looks like code. Say it in plain English first."
    return ""


# ---------- commands ----------
def cmd_start(data, prog, p):
    st = pstate(prog, p["id"])
    print("\n=== %s  (Stage %d) ===\n%s" % (p["title"], p["stage"], p["statement"]))
    for ex in p["examples"]:
        print("  Example input: %s  ->  output: %s" % (ex["input"].replace("\n", " | "), ex["output"]))
    for key, title, prompts in LADDER:
        if key in st["answers"]:
            continue
        print("\n--- STEP %s ---" % title)
        parts = []
        for prompt in prompts:
            while True:
                text = read_answer(prompt)
                if text is None:
                    save_progress(prog)
                    print("\nStopped. Your finished steps are saved. Run 'start %s' to continue." % p["id"])
                    return
                complaint = check_answer(text, key, list(st["answers"].values()) + parts)
                if not complaint:
                    break
                print("  Not accepted: " + complaint)
            parts.append(text)
        st["answers"][key] = "\n".join(parts)
        save_progress(prog)  # saved after every step
        print("  Saved. Step unlocked.")
    print("\nLadder done. NEXT: run 'python coach.py show %s' and paste it to your mentor." % p["id"])
    print("After your plan is reviewed, run 'python coach.py approve %s'." % p["id"])


def cmd_show(prog, p):
    st = pstate(prog, p["id"])
    print("PROBLEM: %s\n%s\n" % (p["title"], p["statement"]))
    for key, title, _ in LADDER:
        print("%s\n%s\n" % (title, st["answers"].get(key, "(not answered yet)")))


def cmd_approve(prog, p):
    st = pstate(prog, p["id"])
    missing = [t for k, t, _ in LADDER if k not in st["answers"]]
    if missing:
        sys.exit("Finish the ladder first. Missing: " + "; ".join(missing))
    st["approved"] = True
    save_progress(prog)
    print("Coding unlocked. Only use this after your mentor reviewed your plan.")
    print("Next: python coach.py code %s" % p["id"])


def solution_path(p):
    return os.path.join(SOLUTIONS_DIR, p["id"].replace("-", "_") + ".py")


def cmd_code(prog, p):
    if not pstate(prog, p["id"])["approved"]:
        sys.exit("Locked. Finish the ladder, get your plan reviewed, then 'approve %s'." % p["id"])
    os.makedirs(SOLUTIONS_DIR, exist_ok=True)
    path = solution_path(p)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("# %s (Stage %d)\n# Use plain input() and print(): no text inside the brackets of input().\n"
                    "# Write your code below this line.\n\n" % (p["title"], p["stage"]))
    print("Write your code in: " + path)
    print("Then run: python coach.py test %s" % p["id"])


def run_one(path, test):
    """Run your file with the test input; return (ok, shown_output)."""
    try:
        r = subprocess.run([sys.executable, path], input=test["input"] + "\n", capture_output=True,
                           text=True, errors="replace", timeout=5, cwd=HERE)
    except subprocess.TimeoutExpired:
        return False, "(timed out after 5 seconds - an endless loop?)"
    got = [ln.rstrip() for ln in r.stdout.strip().splitlines()]
    want = [ln.rstrip() for ln in test["output"].strip().splitlines()]
    if r.returncode != 0:
        last = r.stderr.strip().splitlines()[-1:] or ["error"]
        return False, "(crashed) " + last[0]
    return got == want, "\n".join(got)


def cmd_test(prog, p):
    st = pstate(prog, p["id"])
    if not st["approved"]:
        sys.exit("Locked. Get your plan reviewed, then 'approve %s'." % p["id"])
    path = solution_path(p)
    if not os.path.exists(path):
        sys.exit("No solution file yet. Run 'python coach.py code %s'." % p["id"])
    st["attempts"] += 1
    failures = []
    for t in p["tests"]:
        ok, got = run_one(path, t)
        print("%s  input=%s" % ("PASS" if ok else "FAIL", t["input"].replace("\n", " | ")))
        if not ok:
            failures.append((t, got))
    total = len(p["tests"])
    print("\n%d of %d tests passed." % (total - len(failures), total))
    if failures:
        for t, got in failures[:3]:  # show only the first 3 failures
            print("\n  input   : %s\n  expected: %s\n  you got : %s" % (
                t["input"].replace("\n", " | "), t["output"], got))
            if got.endswith(t["output"]) and got != t["output"]:
                print("  Tip: text inside input('...') is printed too. Use plain input().")
        print("\nRe-read your plan, then fix ONE failing case at a time. Stuck? 'hint %s'." % p["id"])
    else:
        st["passed"] = True
        print("Solved. Explain to your mentor why your border cases work.")
    save_progress(prog)


def cmd_hint(prog, p):
    st = pstate(prog, p["id"])
    if "examples" not in st["answers"]:
        sys.exit("Do steps 1-2 of the ladder first (restate and hand-work). Hints come after an honest try.")
    n = st["hints_used"]
    if n >= len(p["hints"]):
        sys.exit("No more hints. Bring your plan and code to your mentor.")
    print("Hint level %d of %d (%s):\n  %s" % (n + 1, len(p["hints"]), HINT_NAMES[n], p["hints"][n]))
    st["hints_used"] = n + 1
    save_progress(prog)


# ---------- overview, schedule and pacing ----------
def stage_done(data, prog, s):
    ready = [p for p in data["problems"] if p["stage"] == s and p["ready"]]
    return bool(ready) and all(pstate(prog, p["id"])["passed"] for p in ready)


def cmd_concept(data, prog, arg=None):
    s = arg or next((k for k in sorted(data["stages"]) if not stage_done(data, prog, int(k))), "6")
    info = data["stages"][str(s)]
    print("Stage %s: %s" % (s, info["name"]))
    if not info["built"]:
        print("  Not built yet. It arrives after you pass the previous stage.")
    for line in info.get("concept", []):
        print("  - " + line)


def cmd_overview(data, prog):
    print("THINK-FIRST COACH - " + data["project"])
    start = datetime.date.fromisoformat(prog["started"])
    weeks, current = 0.0, None
    print("\nSchedule (started %s):" % start)
    for key in sorted(data["stages"]):
        info = data["stages"][key]
        weeks += info["weeks"]
        due = start + datetime.timedelta(days=round(weeks * 7))
        done = stage_done(data, prog, int(key))
        if current is None and not done:
            current = (key, due)
        print("  Stage %s %-26s due %s %s" % (key, info["name"], due, "[done]" if done else ""))
    review_due = start + datetime.timedelta(days=round((weeks + data["review_weeks"]) * 7))
    print("  Final review (timed, unseen)      due %s" % review_due)
    print("  Spare buffer: %s week(s)" % (data["total_weeks"] - weeks - data["review_weeks"]))
    if current:
        late = (today() - current[1]).days
        if late > 0:
            print("\n  WARNING: Stage %s is %d day(s) behind. Cut something or add hours this week." % (current[0], late))
        else:
            print("\n  On track: Stage %s is due in %d day(s)." % (current[0], -late))
    print("\nProblems:")
    for p in data["problems"]:
        if p["ready"]:
            st = pstate(prog, p["id"])
            steps = sum(1 for k, _, _ in LADDER if k in st["answers"])
            flag = "SOLVED" if st["passed"] else ("coding" if st["approved"] else "ladder %d/6" % steps)
            print("  [S%d] %-18s %-10s hints used: %d" % (p["stage"], p["id"], flag, st["hints_used"]))
    print("\nStart with: python coach.py start <id>   (see the top of coach.py for all commands)")
    save_progress(prog)


def main(argv):
    data, prog = load_problems(), load_progress()
    if len(argv) < 2:
        return cmd_overview(data, prog)
    cmd = argv[1]
    if cmd == "concept":
        return cmd_concept(data, prog, argv[2] if len(argv) > 2 else None)
    handlers = {"start": lambda p: cmd_start(data, prog, p), "show": lambda p: cmd_show(prog, p),
                "approve": lambda p: cmd_approve(prog, p), "code": lambda p: cmd_code(prog, p),
                "test": lambda p: cmd_test(prog, p), "hint": lambda p: cmd_hint(prog, p)}
    if cmd not in handlers or len(argv) < 3:
        sys.exit(__doc__)
    handlers[cmd](find_problem(data, argv[2]))


if __name__ == "__main__":
    main(sys.argv)

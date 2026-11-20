"""Student Grade Analyzer: Levels 1-4, using Python's standard library."""
import csv
import json
import math
import re
import statistics
from pathlib import Path

BASE = Path(__file__).resolve().parent
SUBJECTS = ["Maths", "English", "Science"]
COMPONENTS = ["Coursework", "Exam"]
HEADERS = ["Name"] + [f"{s}_{c}" for s in SUBJECTS for c in COMPONENTS]


def load_settings(path):
    """Read teacher-editable rules and reject invalid settings."""
    with path.open(encoding="utf-8") as file:
        settings = json.load(file)
    weights = settings["weights"]
    for component in COMPONENTS:
        value = weights[component]
        if type(value) not in (int, float) or not 0 <= value <= 1:
            raise ValueError("Each weight must be a number from 0 to 1.")
    if not math.isclose(sum(weights[c] for c in COMPONENTS), 1):
        raise ValueError("Coursework and exam weights must total 1.")
    pass_mark = settings["pass_mark"]
    if type(pass_mark) not in (int, float) or not 0 <= pass_mark <= 100:
        raise ValueError("Pass mark must be a number from 0 to 100.")
    boundaries = settings["grade_boundaries"]
    if not isinstance(boundaries, dict) or not boundaries:
        raise ValueError("Grade boundaries must be a nonempty object.")
    for grade, value in boundaries.items():
        if not isinstance(grade, str) or not grade.strip():
            raise ValueError("Every grade needs a label.")
        if type(value) not in (int, float) or not 0 <= value <= 100:
            raise ValueError("Grade boundaries must be numbers from 0 to 100.")
    if min(boundaries.values()) != 0:
        raise ValueError("The lowest grade must start at zero.")
    if len(set(boundaries.values())) != len(boundaries):
        raise ValueError("Grade boundaries must be different.")
    return settings


def load_students(path):
    """Reject a bad file without changing it; errors identify its CSV row."""
    students = {}
    seen = set()
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file, strict=True)
        try:
            if reader.fieldnames != HEADERS:
                raise ValueError("Row 1: expected headers " + ",".join(HEADERS))
            for row in reader:
                number = reader.line_num
                if None in row:
                    raise ValueError(f"Row {number}: too many cells.")
                name = (row["Name"] or "").strip()
                if not name or name.casefold() in seen:
                    raise ValueError(f"Row {number}: blank or duplicate name.")
                scores = {}
                for subject in SUBJECTS:
                    scores[subject] = {}
                    for component in COMPONENTS:
                        field = f"{subject}_{component}"
                        value = row[field]
                        if value is None or not value.strip():
                            raise ValueError(f"Row {number}: {field} is blank.")
                        try:
                            mark = float(value)
                        except ValueError:
                            raise ValueError(f"Row {number}: {field} is not numeric.")
                        if not 0 <= mark <= 100:
                            raise ValueError(f"Row {number}: {field} must be 0-100.")
                        scores[subject][component] = mark
                students[name] = scores
                seen.add(name.casefold())
        except csv.Error as error:
            raise ValueError(f"CSV row near line {reader.line_num}: {error}")
    return students


def write_csv(path, headers, rows):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)
    temporary.replace(path)


def save_students(path, students):
    rows = []
    for name, scores in students.items():
        rows.append([name] + [scores[s][c] for s in SUBJECTS for c in COMPONENTS])
    write_csv(path, HEADERS, rows)


def get_grade(mark, settings):
    boundaries = settings["grade_boundaries"]
    for grade in sorted(boundaries, key=boundaries.get, reverse=True):
        if mark >= boundaries[grade]:
            return grade


def calculate_results(students, settings):
    results = []
    for name, scores in students.items():
        weighted = {}
        for subject in SUBJECTS:
            weighted[subject] = round(sum(
                scores[subject][c] * settings["weights"][c]
                for c in COMPONENTS
            ), 10)
        average = round(statistics.mean(weighted.values()), 10)
        results.append({"name": name, "scores": weighted,
                        "average": average, "grade": get_grade(average, settings)})
    results.sort(key=lambda r: (-r["average"], r["name"].casefold()))
    previous = None
    rank = 0
    for position, result in enumerate(results, 1):
        if result["average"] != previous:
            rank = position
        result["rank"] = rank
        previous = result["average"]
    return results


def class_statistics(results):
    if not results:
        return None
    averages = [r["average"] for r in results]
    return {
        "average": statistics.mean(averages),
        "median": statistics.median(averages),
        "std_dev": statistics.pstdev(averages),
        "subjects": {s: statistics.mean(r["scores"][s] for r in results)
                     for s in SUBJECTS},
    }


def results_table(results):
    width = max([12] + [len(r["name"]) + 2 for r in results])
    lines = [f"{'Rank':<6}{'Student':<{width}}" +
             "".join(f"{s:>10}" for s in SUBJECTS) +
             f"{'Average':>10}{'Grade':>8}"]
    for r in results:
        lines.append(f"{r['rank']:<6}{r['name']:<{width}}" +
                     "".join(f"{r['scores'][s]:>10.2f}" for s in SUBJECTS) +
                     f"{r['average']:>10.2f}{r['grade']:>8}")
    if not results:
        lines.append("No students found.")
    return "\n".join(lines)


def report_text(results, settings):
    lines = ["STUDENT GRADE ANALYZER", "Weighted subject scores", results_table(results)]
    stats = class_statistics(results)
    if stats is None:
        return "\n".join(lines)
    lines += [f"\nClass average: {stats['average']:.2f}",
              f"Median: {stats['median']:.2f}",
              f"Population standard deviation: {stats['std_dev']:.2f}"]
    for label, value in [("Top", results[0]["average"]),
                         ("Lowest", results[-1]["average"])]:
        names = ", ".join(r["name"] for r in results if r["average"] == value)
        lines.append(f"{label}: {names} ({value:.2f})")
    lines.append("\nSubject averages:")
    for subject, mark in stats["subjects"].items():
        lines.append(f"  {subject}: {mark:.2f}")
    for label, mark in [("Strongest", max(stats["subjects"].values())),
                        ("Weakest", min(stats["subjects"].values()))]:
        names = ", ".join(s for s, m in stats["subjects"].items() if m == mark)
        lines.append(f"{label} subject(s): {names} ({mark:.2f})")
    below = [r["name"] for r in results if r["average"] < settings["pass_mark"]]
    above = [r["name"] for r in results if r["average"] > 80]
    lines += [f"Below pass mark ({settings['pass_mark']:g}): " + (", ".join(below) or "None"),
              "Above 80: " + (", ".join(above) or "None")]
    return "\n".join(lines)


def show_grade_chart(results, settings):
    print("\nGRADE DISTRIBUTION (each # represents one student)")
    boundaries = settings["grade_boundaries"]
    for grade in sorted(boundaries, key=boundaries.get, reverse=True):
        count = sum(r["grade"] == grade for r in results)
        print(f"{grade:>3}: {'#' * count} ({count})")


def export_reports(results, settings, output):
    output.mkdir(parents=True, exist_ok=True)
    (output / "class_report.txt").write_text(report_text(results, settings), encoding="utf-8")
    rows = [[r["rank"], r["name"]] + [f"{r['scores'][s]:.2f}" for s in SUBJECTS]
            + [f"{r['average']:.2f}", r["grade"]] for r in results]
    write_csv(output / "calculated_results.csv",
              ["Rank", "Name"] + SUBJECTS + ["Average", "Grade"], rows)


def create_report_cards(students, results, settings, output):
    output.mkdir(parents=True, exist_ok=True)
    stats = class_statistics(results)
    if stats is None:
        return 0
    for index, r in enumerate(results, 1):
        lines = ["INDIVIDUAL REPORT CARD", f"Student: {r['name']}",
                 f"Rank: {r['rank']} of {len(results)}", f"Grade: {r['grade']}",
                 f"Overall average: {r['average']:.2f}",
                 f"Class average: {stats['average']:.2f}", ""]
        for s in SUBJECTS:
            raw = students[r["name"]][s]
            difference = r["scores"][s] - stats["subjects"][s]
            lines += [s,
                      f"  Coursework: {raw['Coursework']:.2f}; exam: {raw['Exam']:.2f}",
                      f"  Weighted score: {r['scores'][s]:.2f}",
                      f"  Subject class average: {stats['subjects'][s]:.2f}",
                      f"  Difference from subject class average: {difference:+.2f}"]
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", r["name"])[:60]
        (output / f"{index:03}_{safe_name}.txt").write_text("\n".join(lines), encoding="utf-8")
    return len(results)


def compare_terms(first, second, settings):
    before = {r["name"].casefold(): r for r in calculate_results(first, settings)}
    after = {r["name"].casefold(): r for r in calculate_results(second, settings)}
    common = before.keys() & after.keys()
    lines = ["TERM COMPARISON (same current weights applied to both terms)"]
    changes = []
    for key in sorted(common):
        old, new = before[key], after[key]
        change = round(new["average"] - old["average"], 10)
        changes.append((new["name"], change))
        lines.append(f"{new['name']}: {old['average']:.2f} -> {new['average']:.2f} ({change:+.2f})")
    if not common:
        lines.append("No matching student names across the two terms.")
    for label, candidates, extreme in [
        ("Most improved", [(n, d) for n, d in changes if d > 0], max),
        ("Most declined", [(n, d) for n, d in changes if d < 0], min),
    ]:
        if candidates:
            value = extreme(d for _, d in candidates)
            names = ", ".join(n for n, d in candidates if d == value)
            lines.append(f"{label}: {names} ({value:+.2f})")
        else:
            lines.append(f"{label}: None")
    for label, missing in [("Only in term 1", before.keys() - after.keys()),
                            ("Only in term 2", after.keys() - before.keys())]:
        records = before if label.endswith("1") else after
        names = [records[key]["name"] for key in sorted(missing)]
        lines.append(label + ": " + (", ".join(names) or "None"))
    return "\n".join(lines)


def filter_results(results, mode, query="", subject="", low=0, high=100):
    if mode == "name":
        return [r for r in results if query.casefold() in r["name"].casefold()]
    if mode == "grade":
        return [r for r in results if r["grade"].casefold() == query.casefold()]
    if subject not in SUBJECTS or not 0 <= low <= high <= 100:
        raise ValueError("Choose a valid subject and a range from 0 to 100.")
    return [r for r in results if low <= r["scores"][subject] <= high]


def read_score(prompt):
    while True:
        try:
            score = float(input(prompt))
            if 0 <= score <= 100:
                return score
        except ValueError:
            pass
        print("Enter a number from 0 to 100.")


def read_scores():
    return {s: {c: read_score(f"{s} {c} (0-100): ") for c in COMPONENTS}
            for s in SUBJECTS}


def manage_student(students, path, action):
    name = input("Student name: ").strip()
    existing = next((n for n in students if n.casefold() == name.casefold()), None)
    updated = students.copy()
    if action == "add":
        if not name or existing is not None:
            print("Enter a nonempty, unique name.")
            return
        updated[name] = read_scores()
    else:
        if existing is None:
            print("Student not found.")
            return
        if action == "edit":
            updated[existing] = read_scores()
        else:
            del updated[existing]
    save_students(path, updated)
    students.clear()
    students.update(updated)
    print("Change saved to term2.csv.")


def search_menu(results):
    choice = input("Filter: 1 name, 2 grade, 3 subject score: ").strip()
    if choice == "1":
        matches = filter_results(results, "name", input("Name contains: ").strip())
    elif choice == "2":
        matches = filter_results(results, "grade", input("Grade: ").strip())
    elif choice == "3":
        entered = input("Subject (Maths, English, Science): ").strip()
        subject = next((s for s in SUBJECTS if s.casefold() == entered.casefold()), "")
        low = read_score("Minimum weighted score: ")
        high = read_score("Maximum weighted score: ")
        matches = filter_results(results, "subject", subject=subject, low=low, high=high)
    else:
        print("Invalid filter choice.")
        return
    print(results_table(matches))
    print("Ranks remain the positions in the full class.")


def main():
    try:
        settings = load_settings(BASE / "settings.json")
        students = load_students(BASE / "term2.csv")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Cannot start: {error}\nFix the named file or row and restart.")
        return
    print("Student Grade Analyzer - Levels 3 and 4")
    while True:
        print("\n1 Report   2 Grade chart   3 Compare terms   4 Export reports")
        print("5 Individual cards   6 Search/filter   7 Add   8 Edit   9 Remove   0 Exit")
        choice = input("Choice: ").strip()
        results = calculate_results(students, settings)
        try:
            if choice == "1":
                print(report_text(results, settings))
            elif choice == "2":
                show_grade_chart(results, settings)
            elif choice == "3":
                first = load_students(BASE / "term1.csv")
                text = compare_terms(first, students, settings)
                print(text)
                output = BASE / "reports"
                output.mkdir(exist_ok=True)
                (output / "term_comparison.txt").write_text(text, encoding="utf-8")
            elif choice == "4":
                export_reports(results, settings, BASE / "reports")
                print("Saved reports/class_report.txt and calculated_results.csv.")
            elif choice == "5":
                # A fresh folder keeps older report-card batches separate.
                from datetime import datetime
                folder = BASE / "reports" / ("cards_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
                count = create_report_cards(students, results, settings, folder)
                print(f"Saved {count} report cards in {folder}")
            elif choice == "6":
                search_menu(results)
            elif choice in ("7", "8", "9"):
                manage_student(students, BASE / "term2.csv", {"7": "add", "8": "edit", "9": "remove"}[choice])
            elif choice == "0":
                print("Goodbye!")
                break
            else:
                print("Invalid menu choice.")
        except (OSError, ValueError, KeyError, TypeError) as error:
            print(f"Could not complete that action: {error}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")

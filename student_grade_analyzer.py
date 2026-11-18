"""Level 2 Student Grade Analyzer. Run with Python 3."""

import csv
from pathlib import Path

DATA_FILE = Path(__file__).with_name("students.csv")
REPORT_FILE = Path(__file__).with_name("class_report.csv")

SUBJECTS = ["Maths", "English", "Science"]
students = {
    "Ada": {"Maths": 88, "English": 92, "Science": 85},
    "Tunde": {"Maths": 75, "English": 80, "Science": 91},
    "Chioma": {"Maths": 70, "English": 65, "Science": 72},
    "Bola": {"Maths": 95, "English": 90, "Science": 94},
    "Emeka": {"Maths": 50, "English": 55, "Science": 60},
}


def save_students():
    # Replace the file only after the complete CSV has been written.
    temporary = DATA_FILE.with_suffix(".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Name"] + SUBJECTS)
        for name, scores in students.items():
            writer.writerow([name] + [scores[s] for s in SUBJECTS])
    temporary.replace(DATA_FILE)


def load_students():
    global students
    if not DATA_FILE.exists():
        save_students()
        return
    loaded = {}
    names = set()
    with DATA_FILE.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file, strict=True)
        if reader.fieldnames != ["Name"] + SUBJECTS:
            raise ValueError("CSV headers must be Name,Maths,English,Science.")
        for row in reader:
            name = row["Name"].strip()
            if not name or name.casefold() in names or None in row:
                raise ValueError(f"Invalid or duplicate name at row {reader.line_num}.")
            scores = {}
            for subject in SUBJECTS:
                score = float(row[subject])
                if not 0 <= score <= 100:
                    raise ValueError(f"Invalid score at row {reader.line_num}.")
                scores[subject] = score
            loaded[name] = scores
            names.add(name.casefold())
    students = loaded


def export_report():
    ranked = sorted(students, key=lambda n: average(students[n]), reverse=True)
    temporary = REPORT_FILE.with_suffix(".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Rank", "Name"] + SUBJECTS + ["Average", "Grade"])
        for rank, name in enumerate(ranked, 1):
            scores = students[name]
            mark = average(scores)
            writer.writerow([rank, name] + [scores[s] for s in SUBJECTS]
                            + [f"{mark:.1f}", get_grade(mark)])
    temporary.replace(REPORT_FILE)
    print(f"Report exported to {REPORT_FILE}")


def average(scores):
    return sum(scores.values()) / len(scores)


def get_grade(mark):
    if mark >= 90:
        return "A"
    elif mark >= 80:
        return "B"
    elif mark >= 70:
        return "C"
    elif mark >= 60:
        return "D"
    else:
        return "F"


def read_scores():
    scores = {}
    for subject in SUBJECTS:
        while True:
            try:
                score = float(input(f"{subject} score (0-100): "))
                if 0 <= score <= 100:
                    scores[subject] = score
                    break
            except ValueError:
                pass
            print("Enter a number from 0 to 100.")
    return scores


def find_student(name):
    for existing in students:
        if existing.casefold() == name.casefold():
            return existing
    return None


def add_student():
    name = input("New student's name: ").strip()
    if not name:
        print("Name cannot be empty.")
    elif find_student(name) is not None:
        print("That student already exists.")
    else:
        students[name] = read_scores()
        save_students()
        print("Student added and saved.")


def edit_student():
    name = find_student(input("Student to edit: ").strip())
    if name is None:
        print("Student not found.")
    else:
        print(f"Enter new scores for {name}.")
        students[name] = read_scores()
        save_students()
        print("Scores updated and saved.")


def remove_student():
    name = find_student(input("Student to remove: ").strip())
    if name is None:
        print("Student not found.")
    else:
        del students[name]
        save_students()
        print("Student removed and saved.")


def show_report():
    if not students:
        print("No students to report. Add a student first.")
        return

    averages = {}
    for name, scores in students.items():
        averages[name] = average(scores)
    ranked = sorted(averages, key=averages.get, reverse=True)
    width = max(12, max(len(name) for name in students) + 2)
    print(f"\n{'Rank':<6}{'Student':<{width}}{'Maths':>8}"
          f"{'English':>9}{'Science':>9}{'Average':>9}{'Grade':>7}")
    for rank, name in enumerate(ranked, start=1):
        scores = students[name]
        mark = averages[name]
        print(f"{rank:<6}{name:<{width}}{scores['Maths']:>8g}"
              f"{scores['English']:>9g}{scores['Science']:>9g}"
              f"{mark:>9.1f}{get_grade(mark):>7}")

    print("\nSubject averages:")
    for subject in SUBJECTS:
        total = sum(scores[subject] for scores in students.values())
        print(f"  {subject}: {total / len(students):.1f}")
    class_average = sum(averages.values()) / len(averages)
    print(f"Class average: {class_average:.1f}")
    for label, mark in [("Top", max(averages.values())),
                        ("Lowest", min(averages.values()))]:
        names = [name for name in ranked if averages[name] == mark]
        print(f"{label}: {', '.join(names)} ({mark:.1f})")


def main():
    print("Student Grade Analyzer - Level 2")
    try:
        load_students()
    except (OSError, ValueError, TypeError, csv.Error) as error:
        print(f"Cannot load students.csv: {error}")
        print("Fix the file and restart. Existing data has not been overwritten.")
        return
    print(f"Student records load from and save to {DATA_FILE}")
    while True:
        print("\n1. View class report\n2. Add student")
        print("3. Edit scores\n4. Remove student\n5. Exit\n6. Export CSV report")
        choice = input("Choose 1-6: ").strip()
        if choice == "1":
            show_report()
        elif choice == "2":
            add_student()
        elif choice == "3":
            edit_student()
        elif choice == "4":
            remove_student()
        elif choice == "5":
            print("Goodbye!")
            break
        elif choice == "6":
            export_report()
        else:
            print("Invalid choice. Enter 1-6.")


if __name__ == "__main__":
    try:
        main()
    except OSError as error:
        print(f"File operation failed: {error}")
        print("The latest change may not be saved. Check file permissions and retry.")
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")

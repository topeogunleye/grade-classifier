"""Level 2 Student Grade Analyzer. Run with Python 3."""

SUBJECTS = ["Maths", "English", "Science"]
students = {
    "Ada": {"Maths": 88, "English": 92, "Science": 85},
    "Tunde": {"Maths": 75, "English": 80, "Science": 91},
    "Chioma": {"Maths": 70, "English": 65, "Science": 72},
    "Bola": {"Maths": 95, "English": 90, "Science": 94},
    "Emeka": {"Maths": 50, "English": 55, "Science": 60},
}


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
        print("Student added.")


def edit_student():
    name = find_student(input("Student to edit: ").strip())
    if name is None:
        print("Student not found.")
    else:
        print(f"Enter new scores for {name}.")
        students[name] = read_scores()
        print("Scores updated.")


def remove_student():
    name = find_student(input("Student to remove: ").strip())
    if name is None:
        print("Student not found.")
    else:
        del students[name]
        print("Student removed.")


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
    print("Changes last only until you exit.")
    while True:
        print("\n1. View class report\n2. Add student")
        print("3. Edit scores\n4. Remove student\n5. Exit")
        choice = input("Choose 1-5: ").strip()
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
        else:
            print("Invalid choice. Enter 1-5.")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")

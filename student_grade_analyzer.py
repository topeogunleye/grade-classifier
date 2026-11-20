import csv
from pathlib import Path


# Files are stored in the same folder as this program.
DATA_FILE = Path(__file__).with_name("students.csv")
REPORT_FILE = Path(__file__).with_name("class_report.csv")

# A list stores the subjects.
SUBJECTS = ["Maths", "English", "Science"]

# A dictionary stores each student's subject scores.
students = {
    "Ada": {"Maths": 88, "English": 92, "Science": 85},
    "Tunde": {"Maths": 75, "English": 80, "Science": 91},
    "Chioma": {"Maths": 70, "English": 65, "Science": 72},
    "Bola": {"Maths": 95, "English": 90, "Science": 94},
    "Emeka": {"Maths": 50, "English": 55, "Science": 60},
}


# Calculate one student's average.
def average(scores):
    return sum(scores.values()) / len(scores)


# Convert an average into a letter grade.
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


# Save student records to CSV.
def save_students():
    temporary = DATA_FILE.with_suffix(".tmp")

    with temporary.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Name"] + SUBJECTS)

        for name, scores in students.items():
            writer.writerow([
                name,
                scores["Maths"],
                scores["English"],
                scores["Science"],
            ])

    # Replace the previous CSV after writing finishes.
    temporary.replace(DATA_FILE)


# Load saved records when the program starts.
def load_students():
    global students

    # On the first run, create a CSV with the starter students.
    if not DATA_FILE.exists():
        save_students()
        return

    loaded = {}
    used_names = []

    with DATA_FILE.open(
        newline="", encoding="utf-8-sig"
    ) as file:
        reader = csv.DictReader(file, strict=True)

        if reader.fieldnames != ["Name"] + SUBJECTS:
            raise ValueError("The CSV headings are incorrect.")

        for row in reader:
            name = row["Name"].strip()

            if not name or name.lower() in used_names:
                raise ValueError("A student name is empty or duplicated.")

            if None in row:
                raise ValueError("A CSV row contains extra values.")

            scores = {}

            for subject in SUBJECTS:
                score = float(row[subject])

                if not 0 <= score <= 100:
                    raise ValueError("Scores must be from 0 to 100.")

                scores[subject] = score

            loaded[name] = scores
            used_names.append(name.lower())

    # Update the dictionary only after the whole file is valid.
    students = loaded


# Ask for three valid subject scores.
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

            print("Please enter a number from 0 to 100.")

    return scores


# Find a student without worrying about capital letters.
def find_student():
    entered_name = input("Student name: ").strip()

    for name in students:
        if name.lower() == entered_name.lower():
            return name

    return None


# Add a student and save the updated records.
def add_student():
    name = input("New student's name: ").strip()

    if not name:
        print("Name cannot be empty.")
        return

    for existing in students:
        if existing.lower() == name.lower():
            print("That student already exists.")
            return

    students[name] = read_scores()
    save_students()
    print("Student added and saved.")


# Replace a student's three subject scores.
def edit_student():
    name = find_student()

    if name is None:
        print("Student not found.")
        return

    students[name] = read_scores()
    save_students()
    print("Scores updated and saved.")


# Remove a student and save the updated records.
def remove_student():
    name = find_student()

    if name is None:
        print("Student not found.")
        return

    del students[name]
    save_students()
    print("Student removed and saved.")


# Build the ranked report for both display and CSV export.
def get_report():
    averages = {}

    for name, scores in students.items():
        averages[name] = average(scores)

    # Highest average first, then alphabetical order for ties.
    ranked = sorted(
        averages,
        key=lambda name: (-averages[name], name.lower())
    )

    rows = []

    for rank, name in enumerate(ranked, start=1):
        scores = students[name]
        mark = averages[name]

        rows.append([
            rank,
            name,
            scores["Maths"],
            scores["English"],
            scores["Science"],
            round(mark, 1),
            get_grade(mark),
        ])

    return rows, averages


# Display student results and class statistics.
def show_report():
    if not students:
        print("No students available. Add a student first.")
        return

    rows, averages = get_report()
    width = max(12, max(len(name) for name in students) + 2)

    print(
        f"\n{'Rank':<6}{'Student':<{width}}"
        f"{'Maths':>8}{'English':>9}{'Science':>9}"
        f"{'Average':>9}{'Grade':>7}"
    )

    for rank, name, maths, english, science, mark, grade in rows:
        print(
            f"{rank:<6}{name:<{width}}"
            f"{maths:>8g}{english:>9g}{science:>9g}"
            f"{mark:>9.1f}{grade:>7}"
        )

    print("\nSubject averages:")

    for subject in SUBJECTS:
        total = sum(scores[subject] for scores in students.values())
        print(f"{subject}: {total / len(students):.1f}")

    class_average = sum(averages.values()) / len(averages)
    print(f"\nClass average: {class_average:.1f}")

    highest = max(averages.values())
    lowest = min(averages.values())

    
    for row in rows:
        name = row[1]
        if averages[name] == highest:
            print("\nTop student(s):")
            print(f"{name}: {highest:.1f}")

        if averages[name] == lowest:
            print("\nLowest student(s):")
            print(f"{name}: {lowest:.1f}")

        
# Export the ranked student results to another CSV.
def export_report():
    rows, _ = get_report()
    temporary = REPORT_FILE.with_suffix(".tmp")

    with temporary.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            "Rank", "Name", "Maths", "English",
            "Science", "Average", "Grade"
        ])
        writer.writerows(rows)

    temporary.replace(REPORT_FILE)
    print(f"Report exported to {REPORT_FILE}")


# Display the menu until the user exits.
def main():
    try:
        load_students()
    except (OSError, ValueError, TypeError, csv.Error) as error:
        print(f"Cannot load students.csv: {error}")
        print("Fix the file and restart. It has not been overwritten.")
        return

    print("Student Grade Analyzer")

    while True:
        print("\n1. View class report")
        print("2. Add student")
        print("3. Edit scores")
        print("4. Remove student")
        print("5. Export CSV report")
        print("6. Exit")

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
            export_report()
        elif choice == "6":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Enter 1-6.")


# Start the program when this file runs directly.
if __name__ == "__main__":
    try:
        main()
    except OSError as error:
        print(f"File operation failed: {error}")
        print("The latest change may not have been saved.")
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
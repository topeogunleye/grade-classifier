# Each student's scores: Maths, English, Science
students = {
    "Ada": [88, 92, 85],
    "Tunde": [75, 80, 91],
    "Chioma": [70, 65, 72],
    "Bola": [95, 90, 94],
    "Emeka": [50, 55, 60],
}


def get_grade(average):
    if average >= 90:
        return "A"
    elif average >= 80:
        return "B"
    elif average >= 70:
        return "C"
    elif average >= 60:
        return "D"
    else:
        return "F"


# Calculate each student's average.
averages = {}
for name, scores in students.items():
    averages[name] = sum(scores) / len(scores)

# Sort student names from highest average to lowest.
ranked = sorted(averages, key=averages.get, reverse=True)

# Print an aligned table.
print(f"{'Rank':<6}{'Student':<12}{'Maths':>8}{'English':>9}"
      f"{'Science':>9}{'Average':>9}{'Grade':>7}")

for rank, name in enumerate(ranked, start=1):
    maths, english, science = students[name]
    average = averages[name]

    print(f"{rank:<6}{name:<12}{maths:>8}{english:>9}"
          f"{science:>9}{average:>9.1f}{get_grade(average):>7}")

class_average = sum(averages.values()) / len(averages)
top = ranked[0]
lowest = ranked[-1]

print(f"\nClass average: {class_average:.1f}")
print(f"Top: {top} ({averages[top]:.1f})")
print(f"Lowest: {lowest} ({averages[lowest]:.1f})")
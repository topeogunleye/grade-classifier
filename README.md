# Student Grade Analyzer

## Complete Levels 3 and 4

This standalone Python program implements the Level 3 and Level 4 requirements in the supplied project brief. It retains student management, score validation, an aligned table and shared ranks from the earlier levels. Only Python's standard library is required.

## Run

1. Extract the ZIP into a writable folder.
2. Keep `student_grade_analyzer.py`, `settings.json`, `term1.csv` and `term2.csv` together.
3. Open a terminal in that folder.
4. Run `python student_grade_analyzer.py` (or `python3 student_grade_analyzer.py`).

Use Python 3.8 or newer. No package installation is needed. The CSV files are new sample data for the weighted-scoring version, not a conversion of the earlier unweighted students.csv.

## Menu

| Option | Action |
|---|---|
| 1 | Class report with ranks, grades, averages, median, standard deviation and support lists |
| 2 | Text bar chart of grade counts |
| 3 | Compare the two terms and save `reports/term_comparison.txt` |
| 4 | Save `reports/class_report.txt` and `reports/calculated_results.csv` |
| 5 | Create a fresh folder of individual report cards under `reports/` |
| 6 | Search names, filter grades or filter a subject's weighted score range |
| 7 | Add a student to term 2 and save |
| 8 | Edit a term 2 student's coursework and exam scores and save |
| 9 | Remove a student from term 2 and save |
| 0 | Exit |

Term 2 is the current class. Term 1 is the historical comparison. Rerun export after edits to refresh reports. Restart after manually editing CSV or JSON files; the program reads current-term records and settings at startup.

## Lists, dictionaries and files

- `SUBJECTS`, `COMPONENTS` and calculated results are lists.
- Students use nested dictionaries: `students[name][subject][component]`.
- CSV stores one row per student and two component columns per subject.
- JSON stores grade boundaries, the pass mark and scoring weights.
- Text files contain class reports, term comparisons and report cards.

The CSV header must be exactly:

```csv
Name,Maths_Coursework,Maths_Exam,English_Coursework,English_Exam,Science_Coursework,Science_Exam
```

Example record:

```csv
Ada,80,90,90,90,70,90
```

Every component must be a number from 0 to 100. Commas within names work when fields are properly quoted. Names are unique without regard to capitalisation. A header-only file is a valid empty class. Empty physical lines are ignored by the CSV reader, but blank score cells are errors.

## Calculations and explicit choices

**Weighting:** coursework 40% and exam 60% for each subject. Ada's Maths score is `80 × 0.4 + 90 × 0.6 = 86`. The overall average is the mean of the three weighted subject scores, with equal subject weights.

**Ties:** equal averages receive competition ranks, for example `1, 1, 3, 4, 5`. Alphabetical order breaks display-order ties without changing the shared rank. Calculations normalize to ten decimal places to remove insignificant floating-point noise, and reports display two decimal places. Values which merely look equal after display rounding need not share a rank.

**Grades:** JSON values are lower bounds, checked from highest to lowest. Defaults are A >= 90, B >= 80, C >= 70, D >= 60 and F >= 0. The pass mark defaults to 60. A teacher can change it independently of the grade boundaries.

**Statistics:** median and population standard deviation use Python's `statistics` module. Population standard deviation is appropriate because the data represents the whole class being reported. A one-student class has standard deviation zero. An empty class has no statistics.

**Support lists:** below the pass mark means strictly less than it. Above 80 means strictly greater than 80, as requested in the brief. A score exactly at either threshold is excluded from that corresponding list.

**Subjects:** strongest and weakest use the class mean of weighted scores in each subject. All ties appear.

**Term comparison:** both terms use the same current settings so a settings difference does not distort the comparison. Names match without regard to letter case. Students present in only one term are listed separately and excluded from change rankings. All tied most-improved or most-declined students appear. If nobody improved or nobody declined, the corresponding result is None.

**Search:** names use a case-insensitive substring search, grades use a case-insensitive exact match, and subject score ranges are inclusive. Filtered rows retain their full-class ranks.

## Level 3 requirement mapping

| Requirement | Implementation |
|---|---|
| CSV loading and helpful errors | `load_students()` reports the row and problematic field; missing files produce a path-bearing error message |
| Weighted scoring | `calculate_results()` applies coursework and exam weights from JSON |
| Median and standard deviation | `class_statistics()` calls `statistics.median()` and `statistics.pstdev()` |
| Below-pass and above-80 students | `report_text()` lists both groups |
| Strongest and weakest subjects | `report_text()` compares subject averages and includes ties |
| Text and CSV report exports | Option 4 writes the class report and calculated student results |

## Level 4 requirement mapping

| Requirement | Implementation |
|---|---|
| Text grade-distribution chart | Option 2 prints one `#` per student, including zero-count grades |
| Compare two terms | Option 3 loads term 1 and compares it with current term 2 |
| JSON settings | `load_settings()` reads and validates `settings.json` |
| Individual report cards | Option 5 writes each student's raw scores, weighted scores, rank, grade and differences from each subject's class average |
| Search and filter menu | Option 6 supports name, grade and subject score range |

## Error handling and storage

A bad CSV causes the entire load to fail rather than silently losing a student's record. Messages identify the row (the header is row 1). A missing startup file or invalid settings gives a readable message and stops startup. An error during a menu action returns to the menu.

CSV saves write a temporary file before replacing the original. Student-management actions update the in-memory dictionary only after saving succeeds. The program does not overwrite a malformed source file during loading. Individual report cards use safe filenames in a fresh timestamped folder so earlier batches remain separate.

This is a single-user classroom tool. It does not lock files against concurrent edits. Names are identifiers, so renamed students require matching names across terms. Grade and pass settings are teacher-editable, not a prescribed school policy. CSV contains data only and does not preserve Excel cell formatting.

## Verified sample results

With the supplied files and settings:

| Rank | Student | Average | Grade |
|---|---|---:|---|
| 1 | Ada | 86.00 | B |
| 1 | Bola | 86.00 | B |
| 3 | Tunde | 83.00 | B |
| 4 | Chioma | 68.00 | D |
| 5 | Emeka | 53.00 | F |

- Class average: 75.20
- Median: 83.00
- Population standard deviation: 12.95
- Strongest subject: Science, 77.40
- Weakest subject: Maths, 73.00
- Below pass mark: Emeka
- Above 80: Ada, Bola and Tunde
- Most improved: Ada, +5.00
- Most declined: Chioma, -5.00
- Grade distribution: A 0, B 3, C 0, D 1, F 1

`example_reports/` contains outputs generated from these supplied sample files. New runs write to `reports/`.

## Suggested live demonstration

1. Choose 1 and explain the shared first place, median and population standard deviation.
2. Choose 2 and show the grade counts.
3. Choose 3 and identify Ada's improvement and Chioma's decline.
4. Choose 6, then 3, subject Maths, minimum 86 and maximum 90. Ada and Bola match.
5. Choose 4, then open the text and CSV outputs in `reports/`.
6. Choose 5, then open Ada's report card. Her Maths score is 13 points above the class Maths average.
7. Exit with 0. In `settings.json`, temporarily change A's boundary from 90 to 85 and restart. Ada and Bola now receive A. Restore 90 afterwards.
8. To demonstrate validation, use a spare copy of the whole project folder. Blank a score cell in term2.csv, start the copy and show the row-specific error. Restore the cell before continuing.

## Tests

Run:

```bash
python -m unittest -v test_analyzer.py
```

The 12 automated tests cover weighted scores and shared ranks, statistics, empty and one-student classes, bad CSV rows and missing files, headers and duplicates, CSV round trips, configurable grades and invalid weights, comparison matching and ties, filters and charts, report outputs and safe failure during saving. Tests use temporary files for mutations and leave the supplied CSV files unchanged.

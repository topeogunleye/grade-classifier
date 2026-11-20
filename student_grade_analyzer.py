

import csv
import json
import math
import re
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# ==============================================================================
# SECTION 1: GLOBAL CONSTANTS & SCHEMA CONFIGURATION
# ==============================================================================

# Base directory where this script resides. All data and report paths default
# relative to this location, allowing the program to run from any working directory.
BASE: Path = Path(__file__).resolve().parent
BASE_DIRECTORY: Path = BASE  # Semantic alias for improved readability

# The standardized academic subjects tracked in student records.
SUBJECTS: List[str] = ["Maths", "English", "Science"]

# The evaluation components required for every subject.
COMPONENTS: List[str] = ["Coursework", "Exam"]

# Standardized CSV header schema. Row 1 of student CSV files must match this exactly:
# Name,Maths_Coursework,Maths_Exam,English_Coursework,English_Exam,Science_Coursework,Science_Exam
HEADERS: List[str] = ["Name"] + [
    f"{subject_name}_{component_name}"
    for subject_name in SUBJECTS
    for component_name in COMPONENTS
]

# Internal mathematical rounding precision (decimal digits) to eliminate float drift
CALCULATION_ROUNDING_DECIMALS: int = 10

# Default minimum column width allocated to the student name in formatted tables
DEFAULT_STUDENT_COLUMN_WIDTH: int = 12


# ==============================================================================
# SECTION 2: CONFIGURATION LOADING & VALIDATION
# ==============================================================================

def load_settings(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load, parse, and validate teacher-configurable grading rules from a JSON file.

    This function reads grading weights, pass marks, and grade classification
    thresholds from disk, performing strict structural and value-range validation
    to ensure calculation integrity before any grading occurs.

    Validation Rules:
      1. Every component in COMPONENTS must have a numeric weight between 0.0 and 1.0.
      2. The sum of all component weights must equal 1.0 (verified with math.isclose).
      3. The pass mark must be a number between 0.0 and 100.0.
      4. Grade boundaries must be a non-empty dictionary mapping string labels to numbers [0, 100].
      5. The lowest grade boundary must start at exactly 0.0 (ensuring complete coverage).
      6. All grade boundary numeric thresholds must be strictly unique.

    Args:
        path: Filepath to the JSON settings file (Path object or string).

    Returns:
        Dict[str, Any]: The validated settings dictionary containing:
            - "weights": Dict[str, float] mapping component names to fractional weights.
            - "pass_mark": float representing the minimum score required to pass.
            - "grade_boundaries": Dict[str, float] mapping grade labels to lower threshold marks.

    Raises:
        FileNotFoundError: If the specified settings file does not exist.
        json.JSONDecodeError: If the file contains malformed JSON.
        ValueError: If any validation rule is violated, with a clear explanation.
    """
    settings_file_path: Path = Path(path)

    # Step 1: Read and parse JSON content from disk
    with settings_file_path.open(mode="r", encoding="utf-8") as json_file:
        settings_data: Dict[str, Any] = json.load(json_file)

    # Step 2: Validate component weights
    component_weights: Dict[str, Any] = settings_data["weights"]
    for component_name in COMPONENTS:
        weight_value: Any = component_weights[component_name]

        # Weights must be numeric (int or float) and within the unit interval [0, 1]
        if type(weight_value) not in (int, float) or not (0 <= weight_value <= 1):
            raise ValueError("Each weight must be a number from 0 to 1.")

    # Total sum of all component weights must mathematically equal 1.0 (100%)
    total_weight: float = sum(component_weights[comp] for comp in COMPONENTS)
    if not math.isclose(total_weight, 1.0):
        raise ValueError("Coursework and exam weights must total 1.")

    # Step 3: Validate the academic pass mark
    pass_mark_value: Any = settings_data["pass_mark"]
    if type(pass_mark_value) not in (int, float) or not (0 <= pass_mark_value <= 100):
        raise ValueError("Pass mark must be a number from 0 to 100.")

    # Step 4: Validate grade boundary thresholds
    grade_boundaries: Any = settings_data["grade_boundaries"]
    if not isinstance(grade_boundaries, dict) or not grade_boundaries:
        raise ValueError("Grade boundaries must be a nonempty object.")

    for grade_label, threshold_value in grade_boundaries.items():
        # Every grade boundary must have a non-blank string label
        if not isinstance(grade_label, str) or not grade_label.strip():
            raise ValueError("Every grade needs a label.")

        # Thresholds must be numeric and within [0, 100]
        if type(threshold_value) not in (int, float) or not (0 <= threshold_value <= 100):
            raise ValueError("Grade boundaries must be numbers from 0 to 100.")

    # Step 5: Ensure lowest grade starts at 0 to guarantee total grade assignment coverage
    if min(grade_boundaries.values()) != 0:
        raise ValueError("The lowest grade must start at zero.")

    # Step 6: Ensure all grade boundaries are distinct (no ambiguous duplicate cutoffs)
    if len(set(grade_boundaries.values())) != len(grade_boundaries):
        raise ValueError("Grade boundaries must be different.")

    return settings_data


# ==============================================================================
# SECTION 3: CSV DATA LOADING, PARSING & VALIDATION
# ==============================================================================

def load_students(path: Union[str, Path]) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Load, validate, and parse student academic records from a CSV file.

    Reads a CSV file into a nested in-memory dictionary. If any validation
    error is detected (invalid header, malformed row, duplicate student,
    blank cell, non-numeric score, or out-of-range value), loading halts
    immediately and raises a ValueError pinpointing the exact CSV row number.
    The source file on disk is left completely unchanged.

    CSV Format Expectations:
      - Line 1: Header row matching HEADERS exactly.
      - Line 2+: One row per student, starting with 'Name', followed by pairs
        of 'Coursework' and 'Exam' scores for each subject in SUBJECTS.
      - File encoding: UTF-8 with optional Byte Order Mark ('utf-8-sig') to
        seamlessly support CSV files exported from Microsoft Excel.

    In-Memory Data Structure:
      {
          "Student Name": {
              "Maths": {"Coursework": 80.0, "Exam": 90.0},
              "English": {"Coursework": 90.0, "Exam": 90.0},
              "Science": {"Coursework": 70.0, "Exam": 90.0}
          },
          ...
      }

    Args:
        path: Path to the CSV file (Path object or string).

    Returns:
        Dict[str, Dict[str, Dict[str, float]]]: Nested dictionary of student records.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If any structural, syntax, or data value validation check fails.
    """
    csv_file_path: Path = Path(path)
    student_records: Dict[str, Dict[str, Dict[str, float]]] = {}
    normalized_names_seen: Set[str] = set()

    # Open with newline="" as required by the Python standard csv module documentation.
    # Use "utf-8-sig" to transparently strip BOM characters emitted by Excel.
    with csv_file_path.open(mode="r", newline="", encoding="utf-8-sig") as file_handle:
        csv_reader: csv.DictReader = csv.DictReader(file_handle, strict=True)

        try:
            # Step 1: Validate header row structure (Row 1 of file)
            if csv_reader.fieldnames != HEADERS:
                expected_headers_str: str = ",".join(HEADERS)
                raise ValueError(f"Row 1: expected headers {expected_headers_str}")

            # Step 2: Iterate over each data row with strict row-by-row validation
            for row_dictionary in csv_reader:
                current_row_number: int = csv_reader.line_num

                # When a CSV line has more values than headers, DictReader stores
                # the excess values under the dictionary key None.
                if None in row_dictionary:
                    raise ValueError(f"Row {current_row_number}: too many cells.")

                # Extract and sanitize student name
                raw_student_name: Optional[str] = row_dictionary.get("Name")
                cleaned_student_name: str = (raw_student_name or "").strip()

                # Student name cannot be blank, nor can it duplicate an existing student
                # (case-insensitive comparison ensures "Ada" and "ada" are rejected as duplicates)
                if not cleaned_student_name or cleaned_student_name.casefold() in normalized_names_seen:
                    raise ValueError(f"Row {current_row_number}: blank or duplicate name.")

                # Step 3: Parse and validate individual subject component scores
                student_subject_scores: Dict[str, Dict[str, float]] = {}

                for subject_name in SUBJECTS:
                    student_subject_scores[subject_name] = {}

                    for component_name in COMPONENTS:
                        column_header: str = f"{subject_name}_{component_name}"
                        raw_cell_value: Optional[str] = row_dictionary.get(column_header)

                        # Check for blank / empty score cells (e.g., missing values or trailing commas)
                        if raw_cell_value is None or not raw_cell_value.strip():
                            raise ValueError(f"Row {current_row_number}: {column_header} is blank.")

                        # Convert cell value to a floating-point number
                        try:
                            score_number: float = float(raw_cell_value)
                        except ValueError:
                            raise ValueError(f"Row {current_row_number}: {column_header} is not numeric.")

                        # Verify academic score falls strictly within the allowable percentage range [0, 100].
                        # Note: Comparisons with NaN yield False, so `not (0 <= score <= 100)` correctly
                        # catches NaN and Inf values and rejects them.
                        if not (0 <= score_number <= 100):
                            raise ValueError(f"Row {current_row_number}: {column_header} must be 0-100.")

                        student_subject_scores[subject_name][component_name] = score_number

                # Register validated student in memory
                student_records[cleaned_student_name] = student_subject_scores
                normalized_names_seen.add(cleaned_student_name.casefold())

        except csv.Error as csv_error:
            # Catch low-level CSV formatting syntax errors (e.g., unescaped quotes)
            raise ValueError(f"CSV row near line {csv_reader.line_num}: {csv_error}")

    return student_records


# ==============================================================================
# SECTION 4: FILE WRITING & ATOMIC PERSISTENCE
# ==============================================================================

def write_csv(path: Union[str, Path], headers: List[str], rows: List[List[Any]]) -> None:
    """
    Write tabular data to a CSV file using atomic file replacement.

    To protect data integrity against write interruptions (such as power outages,
    full disk, or abrupt process termination), this function first writes all
    content to a temporary staging file (`.tmp`). Once the temporary file is
    safely written, closed, and flushed to storage, it replaces the target file
    atomically via `Path.replace()`.

    Args:
        path: Target file destination path.
        headers: List of column header strings written as the first row.
        rows: List of data rows, where each row is a list of cell values.
    """
    destination_file_path: Path = Path(path)
    temporary_file_path: Path = destination_file_path.with_suffix(".tmp")

    # Step 1: Write all data into temporary staging file
    with temporary_file_path.open(mode="w", newline="", encoding="utf-8") as temp_file:
        csv_writer = csv.writer(temp_file)
        csv_writer.writerow(headers)
        csv_writer.writerows(rows)

    # Step 2: Atomically replace destination path with temporary file
    temporary_file_path.replace(destination_file_path)


def save_students(
    path: Union[str, Path],
    students: Dict[str, Dict[str, Dict[str, float]]]
) -> None:
    """
    Serialize in-memory student records into standardized CSV format on disk.

    Flattens the nested student records dictionary into a 2D table of rows
    conforming to HEADERS and saves it using atomic file writes.

    Args:
        path: File destination path for the student CSV file.
        students: Dictionary of student records to serialize.
    """
    flattened_rows: List[List[Any]] = []

    for student_name, subject_records in students.items():
        row_cells: List[Any] = [student_name]
        for subject_name in SUBJECTS:
            for component_name in COMPONENTS:
                row_cells.append(subject_records[subject_name][component_name])
        flattened_rows.append(row_cells)

    write_csv(path, HEADERS, flattened_rows)


# ==============================================================================
# SECTION 5: ACADEMIC CALCULATIONS & GRADE CLASSIFICATION
# ==============================================================================

def get_grade(mark: float, settings: Dict[str, Any]) -> str:
    """
    Determine the letter grade for an overall percentage mark.

    Iterates through grade boundary thresholds sorted in descending order
    (highest threshold first, e.g., A: 90, B: 80, C: 70, D: 60, F: 0) and
    returns the label of the first boundary that the mark satisfies (mark >= threshold).

    Because `load_settings` guarantees that the lowest threshold starts at 0,
    every valid percentage mark (>= 0) is guaranteed to receive a grade.

    Args:
        mark: Numerical score or overall average percentage (0 to 100).
        settings: Validated settings dictionary containing "grade_boundaries".

    Returns:
        str: The corresponding letter grade label (e.g., 'A', 'B', 'C', 'D', 'F').
    """
    grade_boundaries: Dict[str, float] = settings["grade_boundaries"]

    # Sort grade labels from highest threshold to lowest threshold
    sorted_grades_descending: List[str] = sorted(
        grade_boundaries.keys(),
        key=lambda grade_key: grade_boundaries[grade_key],
        reverse=True,
    )

    for grade_label in sorted_grades_descending:
        minimum_required_score: float = grade_boundaries[grade_label]
        if mark >= minimum_required_score:
            return grade_label

    # Fallback to the lowest defined grade label if score is below all thresholds
    return sorted_grades_descending[-1]


def calculate_results(
    students: Dict[str, Dict[str, Dict[str, float]]],
    settings: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Calculate weighted subject scores, overall averages, letter grades, and ranks.

    Algorithmic Steps:
      1. For each student and each subject, calculate the weighted score:
         `Weighted_Score = sum(Raw_Score[component] * Weight[component])`
         Normalize weighted scores to 10 decimal places to eliminate float drift.
      2. Compute the overall student average across all subjects:
         `Overall_Average = mean(Weighted_Subject_Scores)`
         Normalize overall average to 10 decimal places.
      3. Assign the letter grade using `get_grade()`.
      4. Sort students primarily by overall average (descending) and secondarily
         by student name (case-insensitive ascending) to break display ties consistently.
      5. Compute Standard Competition Ranks ("1224" Scheme):
         Tied averages receive identical ranks, and the subsequent rank skips
         proportionally to the size of the tied group.

    Args:
        students: Dictionary of student records.
        settings: Validated settings dictionary containing weights and grade boundaries.

    Returns:
        List[Dict[str, Any]]: List of calculated student result records:
            [
                {
                    "name": "Ada",
                    "scores": {"Maths": 86.0, "English": 90.0, "Science": 82.0},
                    "average": 86.0,
                    "grade": "B",
                    "rank": 1
                },
                ...
            ]
    """
    calculated_results: List[Dict[str, Any]] = []
    component_weights: Dict[str, float] = settings["weights"]

    # Step 1: Calculate weighted scores and overall average for each student
    for student_name, subject_records in students.items():
        weighted_subject_scores: Dict[str, float] = {}

        for subject_name in SUBJECTS:
            subject_components = subject_records[subject_name]
            # Apply coursework and exam weights
            raw_weighted_sum: float = sum(
                subject_components[component_name] * component_weights[component_name]
                for component_name in COMPONENTS
            )
            # Normalize to 10 decimal places to prevent microscopic IEEE 754 float drift
            weighted_subject_scores[subject_name] = round(
                raw_weighted_sum, CALCULATION_ROUNDING_DECIMALS
            )

        # Overall average is the arithmetic mean of all weighted subject scores
        student_overall_average: float = round(
            statistics.mean(weighted_subject_scores.values()),
            CALCULATION_ROUNDING_DECIMALS,
        )

        assigned_grade: str = get_grade(student_overall_average, settings)

        calculated_results.append({
            "name": student_name,
            "scores": weighted_subject_scores,
            "average": student_overall_average,
            "grade": assigned_grade,
        })

    # Step 2: Sort students by average descending, breaking ties by name alphabetically
    calculated_results.sort(
        key=lambda record: (-record["average"], record["name"].casefold())
    )

    # Step 3: Assign Standard Competition Ranks ("1224" scheme)
    current_competition_rank: int = 0
    previous_average_score: Optional[float] = None

    for position_index, result_record in enumerate(calculated_results, start=1):
        # When average score changes, update rank to the current 1-based position
        if result_record["average"] != previous_average_score:
            current_competition_rank = position_index

        result_record["rank"] = current_competition_rank
        previous_average_score = result_record["average"]

    return calculated_results


# ==============================================================================
# SECTION 6: STATISTICAL ANALYSIS & AGGREGATIONS
# ==============================================================================

def class_statistics(results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Calculate summary statistics across the whole class.

    Computes class mean, median, population standard deviation, and per-subject
    mean scores. If the results list is empty (0 students), returns None.

    Why Population Standard Deviation (pstdev)?
      This system assesses an entire closed classroom group, representing the
      complete population rather than an arbitrary sample. Population standard
      deviation (dividing by N) is therefore statistically correct.
      For a 1-student class, pstdev is mathematically 0.0.

    Args:
        results: List of calculated student result dictionaries.

    Returns:
        Optional[Dict[str, Any]]: None if results is empty; otherwise a dictionary:
            {
                "average": float,
                "median": float,
                "std_dev": float,
                "subjects": {
                    "Maths": float,
                    "English": float,
                    "Science": float
                }
            }
    """
    if not results:
        return None

    student_averages: List[float] = [record["average"] for record in results]

    # Calculate mean score for each subject across all enrolled students
    subject_class_averages: Dict[str, float] = {}
    for subject_name in SUBJECTS:
        subject_class_averages[subject_name] = statistics.mean(
            record["scores"][subject_name] for record in results
        )

    return {
        "average": statistics.mean(student_averages),
        "median": statistics.median(student_averages),
        "std_dev": statistics.pstdev(student_averages),
        "subjects": subject_class_averages,
    }


# ==============================================================================
# SECTION 7: VISUAL TABLES & REPORT FORMATTING
# ==============================================================================

def results_table(results: List[Dict[str, Any]]) -> str:
    """
    Format calculated student results into a clean, dynamically aligned text table.

    Dynamically calculates the required column width for student names to
    prevent clipping or misaligned columns when long names are present.

    Args:
        results: List of calculated student result dictionaries.

    Returns:
        str: Multi-line string table representing student results.
    """
    # Calculate column width: at least DEFAULT_STUDENT_COLUMN_WIDTH (12), or max name length + 2
    max_student_name_length: int = max(
        [len(record["name"]) for record in results],
        default=10
    )
    student_column_width: int = max(DEFAULT_STUDENT_COLUMN_WIDTH, max_student_name_length + 2)

    # Build the header row
    header_line: str = (
        f"{'Rank':<6}{'Student':<{student_column_width}}"
        + "".join(f"{subject_name:>10}" for subject_name in SUBJECTS)
        + f"{'Average':>10}{'Grade':>8}"
    )
    formatted_table_lines: List[str] = [header_line]

    # Build individual student rows
    for record in results:
        formatted_subject_scores: str = "".join(
            f"{record['scores'][subject_name]:>10.2f}"
            for subject_name in SUBJECTS
        )
        row_string: str = (
            f"{record['rank']:<6}"
            f"{record['name']:<{student_column_width}}"
            f"{formatted_subject_scores}"
            f"{record['average']:>10.2f}"
            f"{record['grade']:>8}"
        )
        formatted_table_lines.append(row_string)

    if not results:
        formatted_table_lines.append("No students found.")

    return "\n".join(formatted_table_lines)


def report_text(results: List[Dict[str, Any]], settings: Dict[str, Any]) -> str:
    """
    Generate the complete comprehensive text report for the class.

    Includes the tabular grade list, overall class statistics, top and lowest
    students (including ties), per-subject averages, strongest and weakest
    subjects, and academic support lists (below pass mark and above 80).

    Args:
        results: List of calculated student result dictionaries.
        settings: Validated settings dictionary containing pass mark and grade rules.

    Returns:
        str: Comprehensive multi-line text report.
    """
    report_lines: List[str] = [
        "STUDENT GRADE ANALYZER",
        "Weighted subject scores",
        results_table(results),
    ]

    stats_summary: Optional[Dict[str, Any]] = class_statistics(results)
    if stats_summary is None:
        return "\n".join(report_lines)

    # Core class metrics
    report_lines.append(f"\nClass average: {stats_summary['average']:.2f}")
    report_lines.append(f"Median: {stats_summary['median']:.2f}")
    report_lines.append(f"Population standard deviation: {stats_summary['std_dev']:.2f}")

    # Top and lowest student achievements (listing all students who share the top/lowest mark)
    highest_average_score: float = results[0]["average"]
    lowest_average_score: float = results[-1]["average"]

    for label, target_score in [("Top", highest_average_score), ("Lowest", lowest_average_score)]:
        matching_students: List[str] = [
            record["name"] for record in results if record["average"] == target_score
        ]
        matching_students_str: str = ", ".join(matching_students)
        report_lines.append(f"{label}: {matching_students_str} ({target_score:.2f})")

    # Subject averages breakdown
    report_lines.append("\nSubject averages:")
    for subject_name, subject_mean_score in stats_summary["subjects"].items():
        report_lines.append(f"  {subject_name}: {subject_mean_score:.2f}")

    # Strongest and weakest subject(s) (including all ties)
    strongest_subject_score: float = max(stats_summary["subjects"].values())
    weakest_subject_score: float = min(stats_summary["subjects"].values())

    for label, target_mark in [
        ("Strongest", strongest_subject_score),
        ("Weakest", weakest_subject_score),
    ]:
        matching_subjects: List[str] = [
            subject_name
            for subject_name, mean_score in stats_summary["subjects"].items()
            if mean_score == target_mark
        ]
        matching_subjects_str: str = ", ".join(matching_subjects)
        report_lines.append(f"{label} subject(s): {matching_subjects_str} ({target_mark:.2f})")

    # Academic support lists:
    # - Below pass mark: strictly less than pass_mark
    # - Distinction: strictly greater than 80
    pass_mark_threshold: float = settings["pass_mark"]
    students_below_pass_mark: List[str] = [
        record["name"] for record in results if record["average"] < pass_mark_threshold
    ]
    students_above_eighty: List[str] = [
        record["name"] for record in results if record["average"] > 80
    ]

    below_pass_names_str: str = ", ".join(students_below_pass_mark) or "None"
    above_eighty_names_str: str = ", ".join(students_above_eighty) or "None"

    # Use :g format for pass_mark so integers (like 60) print cleanly without trailing decimals (60)
    report_lines.append(f"Below pass mark ({pass_mark_threshold:g}): {below_pass_names_str}")
    report_lines.append(f"Above 80: {above_eighty_names_str}")

    return "\n".join(report_lines)


# ==============================================================================
# SECTION 8: TEXT BAR CHART VISUALIZATION
# ==============================================================================

def show_grade_chart(results: List[Dict[str, Any]], settings: Dict[str, Any]) -> None:
    """
    Print a text-based ASCII horizontal bar chart representing grade distribution.

    Displays each grade label in descending order, accompanied by a bar of '#'
    characters (one '#' per student) and the exact integer count in parentheses.
    Zero-count grades are explicitly displayed with an empty bar.

    Args:
        results: List of calculated student result dictionaries.
        settings: Validated settings dictionary containing "grade_boundaries".
    """
    print("\nGRADE DISTRIBUTION (each # represents one student)")
    grade_boundaries: Dict[str, float] = settings["grade_boundaries"]

    # Order grades from highest threshold to lowest threshold
    sorted_grades_descending: List[str] = sorted(
        grade_boundaries.keys(),
        key=lambda grade_key: grade_boundaries[grade_key],
        reverse=True,
    )

    for grade_label in sorted_grades_descending:
        student_count_for_grade: int = sum(
            1 for record in results if record["grade"] == grade_label
        )
        bar_visual: str = "#" * student_count_for_grade
        print(f"{grade_label:>3}: {bar_visual} ({student_count_for_grade})")


# ==============================================================================
# SECTION 9: REPORT EXPORTING & REPORT CARDS GENERATION
# ==============================================================================

def export_reports(
    results: List[Dict[str, Any]],
    settings: Dict[str, Any],
    output: Union[str, Path]
) -> None:
    """
    Export class reports to disk in both plain text and CSV formats.

    Creates the destination directory if it does not already exist, and writes:
      1. 'class_report.txt': Full human-readable class performance summary report.
      2. 'calculated_results.csv': Tabular CSV containing Rank, Name, Subject scores,
         Average, and Grade.

    Args:
        results: List of calculated student result dictionaries.
        settings: Validated settings dictionary.
        output: Destination directory path (Path object or string).
    """
    output_directory_path: Path = Path(output)
    output_directory_path.mkdir(parents=True, exist_ok=True)

    # 1. Export the textual narrative report
    class_report_file_path: Path = output_directory_path / "class_report.txt"
    class_report_file_path.write_text(report_text(results, settings), encoding="utf-8")

    # 2. Export the tabular CSV results
    csv_table_rows: List[List[Any]] = []
    for record in results:
        row_values: List[Any] = [record["rank"], record["name"]]
        for subject_name in SUBJECTS:
            row_values.append(f"{record['scores'][subject_name]:.2f}")
        row_values.append(f"{record['average']:.2f}")
        row_values.append(record["grade"])
        csv_table_rows.append(row_values)

    calculated_results_headers: List[str] = ["Rank", "Name"] + SUBJECTS + ["Average", "Grade"]
    calculated_results_csv_path: Path = output_directory_path / "calculated_results.csv"
    write_csv(calculated_results_csv_path, calculated_results_headers, csv_table_rows)


def create_report_cards(
    students: Dict[str, Dict[str, Dict[str, float]]],
    results: List[Dict[str, Any]],
    settings: Dict[str, Any],
    output: Union[str, Path]
) -> int:
    """
    Generate individual performance report cards for every student in the class.

    Each student receives a standalone text file containing:
      - Student name, rank, assigned grade, and overall average.
      - Whole-class average comparison.
      - Per-subject breakdown of raw Coursework and Exam scores.
      - Weighted score achieved in each subject.
      - Class average in each subject and the student's relative difference (+/- delta).

    Filenames are formatted with zero-padded 3-digit rank indices and sanitized
    student names to prevent invalid characters in filesystem paths
    (e.g., '001_Ada.txt').

    Args:
        students: Raw nested dictionary of student component scores.
        results: Calculated student result records.
        settings: Validated settings dictionary.
        output: Destination directory where report cards will be created.

    Returns:
        int: Total number of report card files generated (0 if results is empty).
    """
    output_directory_path: Path = Path(output)
    output_directory_path.mkdir(parents=True, exist_ok=True)

    stats_summary: Optional[Dict[str, Any]] = class_statistics(results)
    if stats_summary is None:
        return 0

    total_class_size: int = len(results)

    for index_counter, record in enumerate(results, start=1):
        student_name: str = record["name"]
        raw_student_scores = students[student_name]

        report_card_lines: List[str] = [
            "INDIVIDUAL REPORT CARD",
            f"Student: {student_name}",
            f"Rank: {record['rank']} of {total_class_size}",
            f"Grade: {record['grade']}",
            f"Overall average: {record['average']:.2f}",
            f"Class average: {stats_summary['average']:.2f}",
            "",
        ]

        # Detail performance across each subject
        for subject_name in SUBJECTS:
            raw_components = raw_student_scores[subject_name]
            coursework_score: float = raw_components["Coursework"]
            exam_score: float = raw_components["Exam"]
            weighted_subject_score: float = record["scores"][subject_name]
            subject_class_mean: float = stats_summary["subjects"][subject_name]
            score_delta_from_mean: float = weighted_subject_score - subject_class_mean

            report_card_lines.extend([
                subject_name,
                f"  Coursework: {coursework_score:.2f}; exam: {exam_score:.2f}",
                f"  Weighted score: {weighted_subject_score:.2f}",
                f"  Subject class average: {subject_class_mean:.2f}",
                f"  Difference from subject class average: {score_delta_from_mean:+.2f}",
            ])

        # Sanitize filename by replacing non-alphanumeric chars with '_' and limiting length
        safe_filesystem_name: str = re.sub(r"[^a-zA-Z0-9_-]", "_", student_name)[:60]
        card_file_path: Path = output_directory_path / f"{index_counter:03}_{safe_filesystem_name}.txt"
        card_file_path.write_text("\n".join(report_card_lines), encoding="utf-8")

    return total_class_size


# ==============================================================================
# SECTION 10: LONGITUDINAL MULTI-TERM COMPARISON
# ==============================================================================

def compare_terms(
    first: Dict[str, Dict[str, Dict[str, float]]],
    second: Dict[str, Dict[str, Dict[str, float]]],
    settings: Dict[str, Any]
) -> str:
    """
    Compare student performance longitudinally across two academic terms.

    Both terms are evaluated using the identical current settings (weights and
    grade thresholds) to ensure that comparisons isolate genuine academic
    progression from configuration changes.

    Analysis Performed:
      1. Identifies common students enrolled across both terms (case-insensitive name matching).
      2. Calculates student-by-student average score changes (`Term 2 - Term 1`).
      3. Determines the most improved student(s) (positive score deltas).
      4. Determines the most declined student(s) (negative score deltas).
      5. Reports unmatched students who were enrolled in only one of the terms.

    Args:
        first: Dictionary of Term 1 student records.
        second: Dictionary of Term 2 student records.
        settings: Current validated settings dictionary.

    Returns:
        str: Comprehensive multi-line term comparison report.
    """
    # Calculate results for both terms using current settings
    term1_results_by_key: Dict[str, Dict[str, Any]] = {
        record["name"].casefold(): record
        for record in calculate_results(first, settings)
    }
    term2_results_by_key: Dict[str, Dict[str, Any]] = {
        record["name"].casefold(): record
        for record in calculate_results(second, settings)
    }

    # Find the set of students common to both terms
    common_student_keys: Set[str] = term1_results_by_key.keys() & term2_results_by_key.keys()

    report_lines: List[str] = [
        "TERM COMPARISON (same current weights applied to both terms)"
    ]

    score_changes: List[Tuple[str, float]] = []

    # Detail progress for each common student in alphabetical order
    for student_key in sorted(common_student_keys):
        term1_record = term1_results_by_key[student_key]
        term2_record = term2_results_by_key[student_key]

        average_difference: float = round(
            term2_record["average"] - term1_record["average"],
            CALCULATION_ROUNDING_DECIMALS
        )
        score_changes.append((term2_record["name"], average_difference))

        report_lines.append(
            f"{term2_record['name']}: {term1_record['average']:.2f} -> "
            f"{term2_record['average']:.2f} ({average_difference:+.2f})"
        )

    if not common_student_keys:
        report_lines.append("No matching student names across the two terms.")

    # Determine most improved and most declined students (including ties)
    improved_candidates: List[Tuple[str, float]] = [
        (student_name, delta) for student_name, delta in score_changes if delta > 0
    ]
    declined_candidates: List[Tuple[str, float]] = [
        (student_name, delta) for student_name, delta in score_changes if delta < 0
    ]

    for label, candidates_list, extreme_fn in [
        ("Most improved", improved_candidates, max),
        ("Most declined", declined_candidates, min),
    ]:
        if candidates_list:
            extreme_delta_value: float = extreme_fn(delta for _, delta in candidates_list)
            matching_student_names: str = ", ".join(
                student_name
                for student_name, delta in candidates_list
                if delta == extreme_delta_value
            )
            report_lines.append(f"{label}: {matching_student_names} ({extreme_delta_value:+.2f})")
        else:
            report_lines.append(f"{label}: None")

    # Identify students enrolled in only one of the two terms
    term1_only_keys: Set[str] = term1_results_by_key.keys() - term2_results_by_key.keys()
    term2_only_keys: Set[str] = term2_results_by_key.keys() - term1_results_by_key.keys()

    term1_only_names: List[str] = [
        term1_results_by_key[key]["name"] for key in sorted(term1_only_keys)
    ]
    term2_only_names: List[str] = [
        term2_results_by_key[key]["name"] for key in sorted(term2_only_keys)
    ]

    term1_only_str: str = ", ".join(term1_only_names) if term1_only_names else "None"
    term2_only_str: str = ", ".join(term2_only_names) if term2_only_names else "None"

    report_lines.append("Only in term 1: " + term1_only_str)
    report_lines.append("Only in term 2: " + term2_only_str)

    return "\n".join(report_lines)


# ==============================================================================
# SECTION 11: FILTERING & SEARCH OPERATIONS
# ==============================================================================

def filter_results(
    results: List[Dict[str, Any]],
    mode: str,
    query: str = "",
    subject: str = "",
    low: float = 0,
    high: float = 100,
) -> List[Dict[str, Any]]:
    """
    Filter calculated student results according to search criteria.

    Filtered students retain their original whole-class ranks.

    Supported Modes:
      - "name": Case-insensitive substring matching against student names.
      - "grade": Case-insensitive exact match against assigned letter grades.
      - "subject": Inclusive range check on a specific subject's weighted score:
                   `low <= score <= high`.

    Args:
        results: Full list of calculated student result records.
        mode: Search mode string ('name', 'grade', or 'subject').
        query: Search query string (used for 'name' and 'grade' modes).
        subject: Target subject name (required for 'subject' mode).
        low: Minimum acceptable score boundary, inclusive (default 0).
        high: Maximum acceptable score boundary, inclusive (default 100).

    Returns:
        List[Dict[str, Any]]: Filtered subset of student result records.

    Raises:
        ValueError: If mode is 'subject' and an invalid subject or range is specified.
    """
    # Mode 1: Student name substring filter
    if mode == "name":
        search_query_normalized: str = query.casefold()
        return [
            record for record in results
            if search_query_normalized in record["name"].casefold()
        ]

    # Mode 2: Letter grade exact match filter
    if mode == "grade":
        target_grade_normalized: str = query.casefold()
        return [
            record for record in results
            if record["grade"].casefold() == target_grade_normalized
        ]

    # Mode 3: Subject score range filter
    # Validates that subject is recognized and that 0 <= low <= high <= 100
    if subject not in SUBJECTS or not (0 <= low <= high <= 100):
        raise ValueError("Choose a valid subject and a range from 0 to 100.")

    return [
        record for record in results
        if low <= record["scores"][subject] <= high
    ]


# ==============================================================================
# SECTION 12: CONSOLE INPUT UTILITIES
# ==============================================================================

def read_score(prompt: str) -> float:
    """
    Interactively prompt the user for a valid percentage score between 0 and 100.

    Loops continuously until the user enters a valid numeric value within
    the allowable boundary [0, 100].

    Args:
        prompt: The prompt message string displayed to the user.

    Returns:
        float: Validated score value.
    """
    while True:
        try:
            raw_input_text: str = input(prompt)
            numeric_score: float = float(raw_input_text)
            if 0 <= numeric_score <= 100:
                return numeric_score
        except ValueError:
            pass
        print("Enter a number from 0 to 100.")


def read_scores() -> Dict[str, Dict[str, float]]:
    """
    Interactively prompt for all required component scores across all subjects.

    Returns:
        Dict[str, Dict[str, float]]: Complete nested score mapping:
            {"Maths": {"Coursework": 80.0, "Exam": 90.0}, ...}
    """
    entered_scores: Dict[str, Dict[str, float]] = {}

    for subject_name in SUBJECTS:
        entered_scores[subject_name] = {}
        for component_name in COMPONENTS:
            prompt_label: str = f"{subject_name} {component_name} (0-100): "
            entered_scores[subject_name][component_name] = read_score(prompt_label)

    return entered_scores


# ==============================================================================
# SECTION 13: STUDENT RECORD MANAGEMENT & CRUD OPERATIONS
# ==============================================================================

def manage_student(
    students: Dict[str, Dict[str, Dict[str, float]]],
    path: Union[str, Path],
    action: str
) -> None:
    """
    Add, edit, or remove a student record with transactional memory safety.

    Memory Safety Rationale:
      To ensure consistency between disk storage and in-memory state, all
      mutations are initially applied to a shallow copy of the student
      dictionary (`updated_students`). The modified data is then written to
      disk via `save_students()`.
      If disk persistence fails (e.g., due to an OSError), an exception is
      raised and the original `students` dictionary remains completely
      unaltered in memory. Only after successful disk write is the in-memory
      dictionary updated.

    Args:
        students: Active in-memory student records dictionary to mutate.
        path: CSV destination file path.
        action: The management operation to execute ('add', 'edit', or 'remove').
    """
    entered_name: str = input("Student name: ").strip()

    # Locate existing student record case-insensitively
    existing_student_key: Optional[str] = next(
        (name for name in students if name.casefold() == entered_name.casefold()),
        None
    )

    # Work on a copy of students to guarantee transactional memory safety
    updated_students: Dict[str, Dict[str, Dict[str, float]]] = students.copy()

    if action == "add":
        if not entered_name or existing_student_key is not None:
            print("Enter a nonempty, unique name.")
            return
        updated_students[entered_name] = read_scores()

    else:
        if existing_student_key is None:
            print("Student not found.")
            return

        if action == "edit":
            updated_students[existing_student_key] = read_scores()
        else:  # action == "remove"
            del updated_students[existing_student_key]

    # Save to disk first. If save_students raises OSError, execution stops here
    # and the original students dictionary remains unchanged in memory.
    save_students(path, updated_students)

    # Mutate in-memory dictionary only after confirmed disk write
    students.clear()
    students.update(updated_students)
    print("Change saved to term2.csv.")


# ==============================================================================
# SECTION 14: INTERACTIVE SEARCH & FILTER MENU
# ==============================================================================

def search_menu(results: List[Dict[str, Any]]) -> None:
    """
    Interactive sub-menu for searching and filtering calculated student results.

    Offers filtering by:
      1. Student name substring.
      2. Assigned letter grade.
      3. Subject score range (min and max boundaries).

    Args:
        results: Calculated student result records to filter and display.
    """
    filter_choice: str = input("Filter: 1 name, 2 grade, 3 subject score: ").strip()

    if filter_choice == "1":
        search_query: str = input("Name contains: ").strip()
        matched_results: List[Dict[str, Any]] = filter_results(
            results, mode="name", query=search_query
        )

    elif filter_choice == "2":
        target_grade: str = input("Grade: ").strip()
        matched_results = filter_results(
            results, mode="grade", query=target_grade
        )

    elif filter_choice == "3":
        entered_subject: str = input("Subject (Maths, English, Science): ").strip()
        matched_subject_name: str = next(
            (s for s in SUBJECTS if s.casefold() == entered_subject.casefold()),
            ""
        )
        minimum_score: float = read_score("Minimum weighted score: ")
        maximum_score: float = read_score("Maximum weighted score: ")

        matched_results = filter_results(
            results,
            mode="subject",
            subject=matched_subject_name,
            low=minimum_score,
            high=maximum_score,
        )

    else:
        print("Invalid filter choice.")
        return

    print(results_table(matched_results))
    print("Ranks remain the positions in the full class.")


# ==============================================================================
# SECTION 15: MAIN APPLICATION LOOP
# ==============================================================================

def main() -> None:
    """
    Main program initialization and interactive CLI menu loop.

    Coordinates loading initial data files, dispatching menu options,
    re-computing results dynamically, and catching operational errors.
    """
    settings_file_path: Path = BASE / "settings.json"
    term2_csv_file_path: Path = BASE / "term2.csv"
    term1_csv_file_path: Path = BASE / "term1.csv"
    reports_output_directory: Path = BASE / "reports"

    # Step 1: Initial startup validation and data loading
    try:
        settings: Dict[str, Any] = load_settings(settings_file_path)
        students: Dict[str, Dict[str, Dict[str, float]]] = load_students(term2_csv_file_path)
    except (OSError, ValueError, KeyError, TypeError) as startup_error:
        print(f"Cannot start: {startup_error}\nFix the named file or row and restart.")
        return

    print("Student Grade Analyzer - Levels 3 and 4")

    # Step 2: Main interactive loop
    while True:
        print("\n1 Report   2 Grade chart   3 Compare terms   4 Export reports")
        print("5 Individual cards   6 Search/filter   7 Add   8 Edit   9 Remove   0 Exit")
        menu_choice: str = input("Choice: ").strip()

        # Always re-calculate current results so additions, edits, or removals
        # are reflected immediately in all subsequent views.
        current_results: List[Dict[str, Any]] = calculate_results(students, settings)

        try:
            # Menu Option 1: Display formatted class report
            if menu_choice == "1":
                print(report_text(current_results, settings))

            # Menu Option 2: Show ASCII grade distribution chart
            elif menu_choice == "2":
                show_grade_chart(current_results, settings)

            # Menu Option 3: Compare Term 1 vs Term 2 data
            elif menu_choice == "3":
                term1_students = load_students(term1_csv_file_path)
                comparison_report: str = compare_terms(term1_students, students, settings)
                print(comparison_report)

                reports_output_directory.mkdir(exist_ok=True)
                comparison_file_path: Path = reports_output_directory / "term_comparison.txt"
                comparison_file_path.write_text(comparison_report, encoding="utf-8")

            # Menu Option 4: Export report files to disk
            elif menu_choice == "4":
                export_reports(current_results, settings, reports_output_directory)
                print("Saved reports/class_report.txt and calculated_results.csv.")

            # Menu Option 5: Create individual report card files in a timestamped folder
            elif menu_choice == "5":
                timestamp_string: str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                cards_folder: Path = reports_output_directory / f"cards_{timestamp_string}"
                cards_count: int = create_report_cards(
                    students, current_results, settings, cards_folder
                )
                print(f"Saved {cards_count} report cards in {cards_folder}")

            # Menu Option 6: Search & filter menu
            elif menu_choice == "6":
                search_menu(current_results)

            # Menu Options 7, 8, 9: Student record management
            elif menu_choice in ("7", "8", "9"):
                action_mapping: Dict[str, str] = {
                    "7": "add",
                    "8": "edit",
                    "9": "remove"
                }
                manage_student(students, term2_csv_file_path, action_mapping[menu_choice])

            # Menu Option 0: Exit application
            elif menu_choice == "0":
                print("Goodbye!")
                break

            else:
                print("Invalid menu choice.")

        except (OSError, ValueError, KeyError, TypeError) as operational_error:
            # Catch operational errors during actions to prevent app crashes
            print(f"Could not complete that action: {operational_error}")


# ==============================================================================
# SECTION 16: APPLICATION ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        # Gracefully handle Ctrl+C or terminal EOF without showing traceback
        print("\nGoodbye!")

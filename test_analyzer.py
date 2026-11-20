"""
================================================================================
UNIT TEST SUITE - STUDENT GRADE ANALYZER (LEVELS 3 & 4)
================================================================================

OVERVIEW
--------
This test suite verifies the correctness, statistical validity, data integrity,
and error-handling resilience of the Student Grade Analyzer application.

EXECUTION INSTRUCTIONS
----------------------
Run all unit tests in verbose mode from the project root:
    python -m unittest -v test_analyzer.py
or:
    python3 -m unittest -v test_analyzer.py

TEST COVERAGE AREAS
-------------------
  1. Weighted Score Calculations & Standard Competition Ranking (1224 scheme).
  2. Whole-Class Summary Statistics (Mean, Median, Population Standard Deviation).
  3. Single-Student Classes & Empty Class Boundary Conditions.
  4. CSV Row Syntax Validation (Blanks, Non-Numeric, Out-of-Range, NaN, Inf).
  5. CSV Header Validation, Duplicate Student Rejections & Cell Counts.
  6. CSV Round-Trip Serialization & Quoted Comma Safety.
  7. JSON Settings Parsing & Dynamic Threshold Validation.
  8. Longitudinal Multi-Term Performance Comparisons (Deltas & Unmatched Students).
  9. Tie-Breaking Mechanics in Longitudinal Comparisons.
 10. Student Search & Filtering (Name Substring, Grade Match, Subject Range).
 11. Report File Exports & Individual Student Report Card Generation.
 12. Transactional Memory Safety During Storage I/O Failures.
================================================================================
"""

import contextlib
import copy
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

# Import the main application module under test
import student_grade_analyzer as app


class AnalyzerTests(unittest.TestCase):
    """
    Comprehensive test suite exercising all Level 3 and Level 4 grading requirements.
    """

    def setUp(self) -> None:
        """
        Prepare test fixtures prior to executing each individual test method.

        Loads default configuration settings and sample student data from the
        repository, and creates an isolated temporary working directory for file I/O tests.
        """
        # Load baseline teacher settings (weights, pass mark, grade thresholds)
        self.settings: Dict[str, Any] = app.load_settings(app.BASE / "settings.json")

        # Load baseline student roster for Term 2
        self.students: Dict[str, Dict[str, Dict[str, float]]] = app.load_students(
            app.BASE / "term2.csv"
        )

        # Create an isolated temporary directory to prevent polluting the repository
        self.temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_directory.cleanup)
        self.folder: Path = Path(self.temp_directory.name)

    def flat(self, mark: float) -> Dict[str, Dict[str, float]]:
        """
        Helper method to construct a mock student record with uniform scores.

        Assigns the specified mark value to every component of every subject.

        Args:
            mark: The numeric mark (0-100) to assign to all components.

        Returns:
            Dict[str, Dict[str, float]]: Nested dictionary of subject component scores.
        """
        return {
            subject_name: {
                component_name: mark for component_name in app.COMPONENTS
            }
            for subject_name in app.SUBJECTS
        }

    def csv(self, rows: List[List[Any]], headers: Optional[List[str]] = None) -> Path:
        """
        Helper method to write a temporary CSV file with given headers and rows.

        Args:
            rows: List of data rows to serialize into the CSV file.
            headers: Optional column header list; defaults to standard app.HEADERS.

        Returns:
            Path: The file path to the newly written temporary CSV file.
        """
        csv_file_path: Path = self.folder / "input.csv"
        app.write_csv(csv_file_path, headers or app.HEADERS, rows)
        return csv_file_path

    # ==========================================================================
    # TEST 1: WEIGHTED SCORING & COMPETITION RANKING
    # ==========================================================================

    def test_weighted_results_and_shared_ranks(self) -> None:
        """
        Verify weighted subject calculation, letter grading, and shared competition ranks.

        Ensures that:
          - Students are sorted descending by overall average.
          - Display ties are resolved alphabetically by name.
          - Tied averages share identical ranks under standard competition ranking (1, 1, 3, 4, 5).
          - Component weighting (Coursework 40% + Exam 60%) produces exact expected subject scores.
        """
        calculated_results = app.calculate_results(self.students, self.settings)

        # Verified student display order: Ada and Bola tie for 1st place; Ada precedes Bola alphabetically.
        expected_names_in_order = ["Ada", "Bola", "Tunde", "Chioma", "Emeka"]
        actual_names_in_order = [result["name"] for result in calculated_results]
        self.assertEqual(actual_names_in_order, expected_names_in_order)

        # Standard Competition Ranking ("1224" ranking):
        # Two rank 1s cause the subsequent rank to skip to 3.
        expected_ranks = [1, 1, 3, 4, 5]
        actual_ranks = [result["rank"] for result in calculated_results]
        self.assertEqual(actual_ranks, expected_ranks)

        # Ada's Maths score calculation:
        # Coursework = 80.0, Exam = 90.0 -> (80.0 * 0.4) + (90.0 * 0.6) = 32.0 + 54.0 = 86.0
        self.assertEqual(calculated_results[0]["scores"]["Maths"], 86.0)

        # Overall average of 86.0 maps to Grade 'B' (since 80 <= 86.0 < 90)
        self.assertEqual(calculated_results[0]["grade"], "B")

    # ==========================================================================
    # TEST 2: STATISTICAL AGGREGATIONS & CLASS REPORT
    # ==========================================================================

    def test_statistics_and_report(self) -> None:
        """
        Verify class statistics (mean, median, pstdev) and report narrative generation.

        Checks:
          - Class arithmetic mean calculation.
          - Median calculation across odd-sized student populations.
          - Population standard deviation matches sqrt(variance).
          - The presence of required academic phrases in the narrative report.
        """
        calculated_results = app.calculate_results(self.students, self.settings)
        statistics_summary = app.class_statistics(calculated_results)

        self.assertIsNotNone(statistics_summary)
        # Class average: (86 + 86 + 83 + 68 + 53) / 5 = 376 / 5 = 75.2
        self.assertAlmostEqual(statistics_summary["average"], 75.2)

        # Median of [86, 86, 83, 68, 53] sorted is 83.0
        self.assertEqual(statistics_summary["median"], 83.0)

        # Population standard deviation = sqrt(variance) = sqrt(167.76) ≈ 12.9522
        expected_std_dev = 167.76 ** 0.5
        self.assertAlmostEqual(statistics_summary["std_dev"], expected_std_dev)

        # Verify key narrative phrases inside the generated class report
        full_report_text = app.report_text(calculated_results, self.settings)
        required_phrases = [
            "Strongest subject(s): Science",
            "Weakest subject(s): Maths",
            "Below pass mark (60): Emeka",
            "Above 80: Ada, Bola, Tunde",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, full_report_text)

    # ==========================================================================
    # TEST 3: BOUNDARY CONDITIONS - EMPTY & SINGLE-STUDENT ROSTERS
    # ==========================================================================

    def test_empty_and_single_class(self) -> None:
        """
        Verify boundary conditions: empty student rosters and single-student classes.

        Ensures:
          - An empty class returns None for statistics and reports "No students found."
          - A single-student class has a population standard deviation of exactly 0.0.
          - Generating report cards for an empty class safely returns 0 files created.
        """
        # Empty class verification
        self.assertIsNone(app.class_statistics([]))
        self.assertIn("No students", app.report_text([], self.settings))

        # Single-student class verification
        single_student_roster = {"Only": self.flat(70.0)}
        single_results = app.calculate_results(single_student_roster, self.settings)
        single_stats = app.class_statistics(single_results)
        self.assertEqual(single_stats["std_dev"], 0.0)

        # Empty report card creation returns 0 without raising an error
        cards_output_folder = self.folder / "cards"
        self.assertEqual(
            app.create_report_cards({}, [], self.settings, cards_output_folder),
            0
        )

    # ==========================================================================
    # TEST 4: CSV ROW-LEVEL DATA VALIDATION & ERROR REPORTING
    # ==========================================================================

    def test_csv_row_errors_and_missing_file(self) -> None:
        """
        Verify that CSV loading rejects invalid cell values with line-specific errors.

        Tests that:
          - Blank score cells, non-numeric text, out-of-bounds numbers (>100),
            NaN (not-a-number), and Inf (infinity) are all rejected with informative
            ValueError messages referencing 'Row 2'.
          - Malformed files are not modified or corrupted on disk during validation.
          - Attempting to load a non-existent file raises FileNotFoundError.
        """
        invalid_cell_test_cases = [
            ("", "blank"),
            ("hello", "not numeric"),
            ("101", "0-100"),
            ("nan", "0-100"),
            ("inf", "0-100"),
        ]

        for invalid_cell_value, expected_message_fragment in invalid_cell_test_cases:
            # Construct a row with an invalid Maths_Coursework cell at Row 2
            test_row = [["Ada", invalid_cell_value, 80, 80, 80, 80, 80]]
            csv_path = self.csv(test_row)
            file_bytes_before_read = csv_path.read_bytes()

            # Ensure ValueError is raised identifying Row 2 and the error reason
            with self.assertRaisesRegex(ValueError, f"Row 2:.*{expected_message_fragment}"):
                app.load_students(csv_path)

            # Ensure source file on disk remained completely unmodified
            self.assertEqual(csv_path.read_bytes(), file_bytes_before_read)

        # Missing file must raise FileNotFoundError with path context
        with self.assertRaises(FileNotFoundError):
            app.load_students(self.folder / "missing.csv")

    # ==========================================================================
    # TEST 5: CSV HEADER, DUPLICATE NAME & ROW SHAPE VALIDATION
    # ==========================================================================

    def test_bad_headers_duplicates_and_shape(self) -> None:
        """
        Verify that CSV loading rejects invalid headers, duplicate names, and wrong column counts.

        Checks:
          - Headers that don't match HEADERS raise an error identifying Row 1.
          - Case-insensitive duplicate student names raise an error identifying the duplicate's row.
          - Rows with too few or too many cells raise an error identifying the offending row.
        """
        # Test 1: Header mismatch (Row 1)
        truncated_header_csv = self.csv([], headers=["Name", "Maths"])
        with self.assertRaisesRegex(ValueError, "Row 1"):
            app.load_students(truncated_header_csv)

        # Test 2: Case-insensitive duplicate student names (Ada vs ada at Row 3)
        duplicate_name_rows = [
            ["Ada"] + [80] * 6,
            ["ada"] + [80] * 6,
        ]
        with self.assertRaisesRegex(ValueError, "Row 3"):
            app.load_students(self.csv(duplicate_name_rows))

        # Test 3: Row with too few cells (Row 2: only 2 cells instead of 7)
        too_few_cells_row = [["Ada", 80]]
        with self.assertRaisesRegex(ValueError, "Row 2"):
            app.load_students(self.csv(too_few_cells_row))

        # Test 4: Row with too many cells (Row 2: 8 cells instead of 7)
        too_many_cells_row = [["Ada"] + [80] * 7]
        with self.assertRaisesRegex(ValueError, "Row 2"):
            app.load_students(self.csv(too_many_cells_row))

    # ==========================================================================
    # TEST 6: CSV ROUND-TRIP SERIALIZATION & QUOTED COMMAS
    # ==========================================================================

    def test_csv_roundtrip_and_header_only(self) -> None:
        """
        Verify that student data saves to CSV and reloads without loss or corruption.

        Checks:
          - Student names containing embedded commas (e.g., 'Name, With Comma')
            are properly escaped and round-trip successfully.
          - Empty classes save a header-only CSV and reload as an empty dictionary.
        """
        original_student_roster = {"Name, With Comma": self.flat(82.5)}
        saved_csv_path = self.folder / "saved.csv"

        # Save and reload populated roster
        app.save_students(saved_csv_path, original_student_roster)
        reloaded_student_roster = app.load_students(saved_csv_path)
        self.assertEqual(reloaded_student_roster, original_student_roster)

        # Save and reload empty roster (header-only file)
        app.save_students(saved_csv_path, {})
        reloaded_empty_roster = app.load_students(saved_csv_path)
        self.assertEqual(reloaded_empty_roster, {})

    # ==========================================================================
    # TEST 7: JSON SETTINGS & DYNAMIC THRESHOLD VALIDATION
    # ==========================================================================

    def test_json_settings_and_boundaries(self) -> None:
        """
        Verify grade threshold classification and strict validation of settings.json.

        Checks:
          - Boundary score mapping: 59.99->F, 60->D, 70->C, 80->B, 90->A, 100->A.
          - Custom teacher-edited settings correctly take effect on reload.
          - Invalid weights sum (e.g., Coursework 0.4 + Exam 0.9 = 1.3 != 1.0) raises ValueError.
        """
        test_score_values = [59.99, 60.0, 70.0, 80.0, 90.0, 100.0]
        assigned_letter_grades = [
            app.get_grade(score, self.settings) for score in test_score_values
        ]
        self.assertEqual(assigned_letter_grades, list("FDCBAA"))

        # Mutate settings to lower the 'A' boundary to 85 and raise pass mark to 70
        customized_settings = copy.deepcopy(self.settings)
        customized_settings["grade_boundaries"]["A"] = 85
        customized_settings["pass_mark"] = 70

        settings_json_path = self.folder / "settings.json"
        settings_json_path.write_text(json.dumps(customized_settings))

        loaded_custom_settings = app.load_settings(settings_json_path)
        # Score of 86 should now be graded 'A' under the new 85 boundary
        self.assertEqual(app.get_grade(86, loaded_custom_settings), "A")

        # Mutate weights to sum to 1.3 (0.4 + 0.9), which violates the unit sum rule
        customized_settings["weights"]["Exam"] = 0.9
        settings_json_path.write_text(json.dumps(customized_settings))

        with self.assertRaises(ValueError):
            app.load_settings(settings_json_path)

    # ==========================================================================
    # TEST 8: LONGITUDINAL TERM COMPARISON & UNMATCHED STUDENTS
    # ==========================================================================

    def test_comparison_and_unmatched(self) -> None:
        """
        Verify longitudinal term comparison tracking student deltas and enrollment changes.

        Checks:
          - Accurate detection of most improved student (Ada, +5.00).
          - Accurate detection of most declined student (Chioma, -5.00).
          - Unmatched students enrolled in only one term are segregated and reported.
        """
        first_term_students = app.load_students(app.BASE / "term1.csv")
        comparison_report_text = app.compare_terms(
            first_term_students, self.students, self.settings
        )

        self.assertIn("Most improved: Ada (+5.00)", comparison_report_text)
        self.assertIn("Most declined: Chioma (-5.00)", comparison_report_text)

        # Test case with completely disjoint student rosters across terms
        disjoint_term1 = {"Old": self.flat(70.0)}
        disjoint_term2 = {"New": self.flat(80.0)}
        disjoint_report_text = app.compare_terms(
            disjoint_term1, disjoint_term2, self.settings
        )

        self.assertIn("No matching", disjoint_report_text)
        self.assertIn("Only in term 1: Old", disjoint_report_text)
        self.assertIn("Only in term 2: New", disjoint_report_text)

    # ==========================================================================
    # TEST 9: COMPARISON TIES & NO-DECLINE EDGE CASES
    # ==========================================================================

    def test_comparison_ties_and_no_decline(self) -> None:
        """
        Verify term comparison handling when multiple students tie or no students decline.

        Ensures:
          - When two students achieve the identical maximum improvement, both are listed.
          - When no student declined in average, 'Most declined' reports 'None'.
        """
        term1_roster = {"A": self.flat(70.0), "B": self.flat(70.0)}
        term2_roster = {"A": self.flat(80.0), "B": self.flat(80.0)}

        comparison_report = app.compare_terms(term1_roster, term2_roster, self.settings)

        # Both student A and student B improved by +10.00
        self.assertIn("Most improved: A, B (+10.00)", comparison_report)
        # Since no student decreased, decline must report None
        self.assertIn("Most declined: None", comparison_report)

    # ==========================================================================
    # TEST 10: SEARCH, FILTERING & GRADE DISTRIBUTION CHART
    # ==========================================================================

    def test_filters_and_chart(self) -> None:
        """
        Verify filtering by name substring, grade, and subject score range, plus chart output.

        Checks:
          - Filtering by letter grade (case-insensitive).
          - Substring searching by name (case-insensitive).
          - Inclusive range filtering on weighted subject scores.
          - Inverted range (low > high) raises ValueError.
          - Grade distribution ASCII chart prints accurate bar lengths and counts.
        """
        calculated_results = app.calculate_results(self.students, self.settings)

        # 1. Filter by grade 'b' (case-insensitive) matches 3 students (Ada, Bola, Tunde)
        grade_b_matches = app.filter_results(calculated_results, mode="grade", query="b")
        self.assertEqual(len(grade_b_matches), 3)

        # 2. Filter by name 'ADA' matches 'Ada'
        name_matches = app.filter_results(calculated_results, mode="name", query="ADA")
        self.assertEqual(name_matches[0]["name"], "Ada")

        # 3. Filter by Maths score between 86 and 90 matches 2 students (Ada with 86, Bola with 90)
        subject_matches = app.filter_results(
            calculated_results, mode="subject", subject="Maths", low=86, high=90
        )
        self.assertEqual(len(subject_matches), 2)

        # 4. Inverted range (low=90 > high=80) must raise ValueError
        with self.assertRaises(ValueError):
            app.filter_results(
                calculated_results, mode="subject", subject="Maths", low=90, high=80
            )

        # 5. Verify ASCII chart printing
        captured_output_stream = io.StringIO()
        with contextlib.redirect_stdout(captured_output_stream):
            app.show_grade_chart(calculated_results, self.settings)

        printed_chart_text = captured_output_stream.getvalue()
        self.assertIn("B: ### (3)", printed_chart_text)
        self.assertIn("A:  (0)", printed_chart_text)

    # ==========================================================================
    # TEST 11: REPORT EXPORTING & INDIVIDUAL REPORT CARDS
    # ==========================================================================

    def test_report_files_and_cards(self) -> None:
        """
        Verify export of class summary files and individual student report cards.

        Checks:
          - export_reports() writes 'class_report.txt' and 'calculated_results.csv'.
          - create_report_cards() creates a report card per student with class average deltas.
        """
        calculated_results = app.calculate_results(self.students, self.settings)

        # Export reports to temporary folder
        app.export_reports(calculated_results, self.settings, self.folder)

        # Validate calculated_results.csv contents and ranks
        csv_path = self.folder / "calculated_results.csv"
        with csv_path.open(mode="r", encoding="utf-8") as csv_file:
            csv_reader = csv.DictReader(csv_file)
            exported_ranks = [row["Rank"] for row in csv_reader]
        self.assertEqual(exported_ranks, ["1", "1", "3", "4", "5"])

        # Validate class_report.txt content
        class_report_text = (self.folder / "class_report.txt").read_text(encoding="utf-8")
        self.assertIn("Median: 83.00", class_report_text)

        # Create individual report cards
        cards_directory = self.folder / "cards"
        created_cards_count = app.create_report_cards(
            self.students, calculated_results, self.settings, cards_directory
        )
        self.assertEqual(created_cards_count, 5)

        # Verify Ada's specific report card content
        ada_card_text = (cards_directory / "001_Ada.txt").read_text(encoding="utf-8")
        self.assertIn("Coursework: 80.00; exam: 90.00", ada_card_text)
        self.assertIn("Difference from subject class average: +13.00", ada_card_text)

    # ==========================================================================
    # TEST 12: MEMORY SAFETY & TRANSACTIONAL DISK WRITE FAILURE
    # ==========================================================================

    def test_save_failure_preserves_memory(self) -> None:
        """
        Verify that a disk save failure prevents corruption of in-memory data.

        Mocks an OSError during student saving to simulate a read-only filesystem
        or hardware failure, ensuring that the active `students` dictionary remains
        completely intact.
        """
        in_memory_students_backup = copy.deepcopy(self.students)

        # Simulate user input selecting 'Ada' and mock save_students to raise OSError
        with patch("builtins.input", return_value="Ada"), patch.object(
            app, "save_students", side_effect=OSError("Read only filesystem")
        ):
            with self.assertRaises(OSError):
                app.manage_student(
                    self.students, self.folder / "students.csv", action="remove"
                )

        # Verify that memory was not modified when save failed
        self.assertEqual(self.students, in_memory_students_backup)


if __name__ == "__main__":
    unittest.main()

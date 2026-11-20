"""Run with: python -m unittest -v test_analyzer.py"""
import contextlib
import copy
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import student_grade_analyzer as app


class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.settings = app.load_settings(app.BASE / "settings.json")
        self.students = app.load_students(app.BASE / "term2.csv")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def flat(self, mark):
        return {s: {c: mark for c in app.COMPONENTS} for s in app.SUBJECTS}

    def csv(self, rows, headers=None):
        path = self.folder / "input.csv"
        app.write_csv(path, headers or app.HEADERS, rows)
        return path

    def test_weighted_results_and_shared_ranks(self):
        results = app.calculate_results(self.students, self.settings)
        self.assertEqual([r['name'] for r in results], ['Ada','Bola','Tunde','Chioma','Emeka'])
        self.assertEqual([r['rank'] for r in results], [1,1,3,4,5])
        self.assertEqual(results[0]['scores']['Maths'],86)
        self.assertEqual(results[0]['grade'],'B')

    def test_statistics_and_report(self):
        results = app.calculate_results(self.students,self.settings)
        stats = app.class_statistics(results)
        self.assertAlmostEqual(stats['average'],75.2)
        self.assertEqual(stats['median'],83)
        self.assertAlmostEqual(stats['std_dev'],167.76 ** 0.5)
        report = app.report_text(results,self.settings)
        for phrase in ['Strongest subject(s): Science','Weakest subject(s): Maths',
                       'Below pass mark (60): Emeka','Above 80: Ada, Bola, Tunde']:
            self.assertIn(phrase,report)

    def test_empty_and_single_class(self):
        self.assertIsNone(app.class_statistics([]))
        self.assertIn('No students',app.report_text([],self.settings))
        results=app.calculate_results({'Only':self.flat(70)},self.settings)
        self.assertEqual(app.class_statistics(results)['std_dev'],0)
        self.assertEqual(app.create_report_cards({},[],self.settings,self.folder/'cards'),0)

    def test_csv_row_errors_and_missing_file(self):
        for bad,message in [('', 'blank'),('hello','not numeric'),('101','0-100'),('nan','0-100'),('inf','0-100')]:
            path=self.csv([['Ada',bad,80,80,80,80,80]])
            before=path.read_bytes()
            with self.assertRaisesRegex(ValueError,f'Row 2:.*{message}'):
                app.load_students(path)
            self.assertEqual(path.read_bytes(),before)
        with self.assertRaises(FileNotFoundError):
            app.load_students(self.folder/'missing.csv')

    def test_bad_headers_duplicates_and_shape(self):
        path=self.csv([],['Name','Maths'])
        with self.assertRaisesRegex(ValueError,'Row 1'):
            app.load_students(path)
        for rows,expected in [([['Ada']+[80]*6,['ada']+[80]*6],'Row 3'),
                              ([['Ada',80]],'Row 2'),([['Ada']+[80]*7],'Row 2')]:
            with self.assertRaisesRegex(ValueError,expected):
                app.load_students(self.csv(rows))

    def test_csv_roundtrip_and_header_only(self):
        students={'Name, With Comma':self.flat(82.5)}
        path=self.folder/'saved.csv'
        app.save_students(path,students)
        self.assertEqual(app.load_students(path),students)
        app.save_students(path,{})
        self.assertEqual(app.load_students(path),{})

    def test_json_settings_and_boundaries(self):
        self.assertEqual([app.get_grade(v,self.settings) for v in [59.99,60,70,80,90,100]],list('FDCBAA'))
        modified=copy.deepcopy(self.settings)
        modified['grade_boundaries']['A']=85
        modified['pass_mark']=70
        path=self.folder/'settings.json'
        path.write_text(json.dumps(modified))
        loaded=app.load_settings(path)
        self.assertEqual(app.get_grade(86,loaded),'A')
        modified['weights']['Exam']=0.9
        path.write_text(json.dumps(modified))
        with self.assertRaises(ValueError):app.load_settings(path)

    def test_comparison_and_unmatched(self):
        first=app.load_students(app.BASE/'term1.csv')
        text=app.compare_terms(first,self.students,self.settings)
        self.assertIn('Most improved: Ada (+5.00)',text)
        self.assertIn('Most declined: Chioma (-5.00)',text)
        text=app.compare_terms({'Old':self.flat(70)},{'New':self.flat(80)},self.settings)
        self.assertIn('No matching',text)
        self.assertIn('Only in term 1: Old',text)
        self.assertIn('Only in term 2: New',text)

    def test_comparison_ties_and_no_decline(self):
        first={'A':self.flat(70),'B':self.flat(70)}
        second={'A':self.flat(80),'B':self.flat(80)}
        text=app.compare_terms(first,second,self.settings)
        self.assertIn('Most improved: A, B (+10.00)',text)
        self.assertIn('Most declined: None',text)

    def test_filters_and_chart(self):
        results=app.calculate_results(self.students,self.settings)
        self.assertEqual(len(app.filter_results(results,'grade','b')),3)
        self.assertEqual(app.filter_results(results,'name','ADA')[0]['name'],'Ada')
        self.assertEqual(len(app.filter_results(results,'subject',subject='Maths',low=86,high=90)),2)
        with self.assertRaises(ValueError):
            app.filter_results(results,'subject',subject='Maths',low=90,high=80)
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream):app.show_grade_chart(results,self.settings)
        self.assertIn('B: ### (3)',stream.getvalue())
        self.assertIn('A:  (0)',stream.getvalue())

    def test_report_files_and_cards(self):
        results=app.calculate_results(self.students,self.settings)
        app.export_reports(results,self.settings,self.folder)
        with (self.folder/'calculated_results.csv').open() as f: rows=list(csv.DictReader(f))
        self.assertEqual([r['Rank'] for r in rows],['1','1','3','4','5'])
        self.assertIn('Median: 83.00',(self.folder/'class_report.txt').read_text())
        count=app.create_report_cards(self.students,results,self.settings,self.folder/'cards')
        self.assertEqual(count,5)
        card=(self.folder/'cards'/'001_Ada.txt').read_text()
        self.assertIn('Coursework: 80.00; exam: 90.00',card)
        self.assertIn('Difference from subject class average: +13.00',card)

    def test_save_failure_preserves_memory(self):
        before=copy.deepcopy(self.students)
        with patch('builtins.input',return_value='Ada'),patch.object(app,'save_students',side_effect=OSError('Read only')):
            with self.assertRaises(OSError):
                app.manage_student(self.students,self.folder/'students.csv','remove')
        self.assertEqual(self.students,before)


if __name__ == '__main__':
    unittest.main()

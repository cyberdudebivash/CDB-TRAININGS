"""Unit tests for the offline FND-M05 guided reference."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'solution'))
from support_metrics import summarize_csv

HEADER='ticket_id,team,minutes,severity\n'
DATA='AB-001,Support,5,HIGH\nCD-002,Support,10,LOW\nEF-003,Platform,0,MEDIUM\n'

class SupportMetricsContract(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.csv=self.root/'records.csv'
    def run_case(self, contents=HEADER+DATA):
        self.csv.write_text(contents,encoding='utf8')
        return summarize_csv(self.root,Path('records.csv'))
    def test_correct_grouping_and_sorted_output(self):
        self.assertEqual(self.run_case(),{
            'total_tickets':3,'total_minutes':15,
            'by_team':[{'team':'Platform','tickets':1,'minutes':0,'high':0},
                       {'team':'Support','tickets':2,'minutes':15,'high':1}]})
    def test_repeat_is_deterministic_and_read_only(self):
        data=HEADER+DATA;self.csv.write_text(data)
        one=summarize_csv(self.root,Path('records.csv'))
        self.assertEqual(one,summarize_csv(self.root,Path('records.csv')))
        self.assertEqual(self.csv.read_text(),data)
    def test_wrong_schema_rejected(self):
        with self.assertRaisesRegex(ValueError,'header'):self.run_case('team,ticket_id,minutes,severity\n'+DATA)
    def test_empty_rows_rejected(self):
        with self.assertRaisesRegex(ValueError,'at least one'):self.run_case(HEADER)
    def test_duplicate_id_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):self.run_case(HEADER+DATA+'AB-001,Support,7,HIGH\n')
    def test_invalid_team_rejected(self):
        with self.assertRaisesRegex(ValueError,'team'):self.run_case(HEADER+'AB-001,Team;command,1,LOW\n')
    def test_bad_minute_formats_rejected(self):
        for m in ('-1','1.5','01','+2','NaN','999999',''):
            with self.subTest(m=m),self.assertRaises(ValueError):self.run_case(HEADER+f'AB-001,Support,{m},LOW\n')
    def test_invalid_severity_rejected(self):
        with self.assertRaisesRegex(ValueError,'severity'):self.run_case(HEADER+'AB-001,Support,1,CRITICAL\n')
    def test_malformed_column_counts(self):
        for row in ('AB-001,Support,1\n','AB-001,Support,1,LOW,extra\n'):
            with self.subTest(row=row),self.assertRaises(ValueError):self.run_case(HEADER+row)
    def test_absolute_or_traversal_paths_rejected(self):
        self.csv.write_text(HEADER+DATA)
        for path in (self.csv, Path('../records.csv')):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError,'relative'):summarize_csv(self.root,path)
    def test_symlink_file_rejected(self):
        self.csv.write_text(HEADER+DATA)
        link=self.root/'linked.csv'
        try:link.symlink_to(self.csv)
        except (OSError,NotImplementedError):self.skipTest('host cannot create symlinks')
        with self.assertRaisesRegex(ValueError,'symlink'):summarize_csv(self.root,Path('linked.csv'))
    def test_symlink_root_rejected(self):
        self.csv.write_text(HEADER+DATA)
        link=self.root.parent/(self.root.name+'-link')
        try:link.symlink_to(self.root,target_is_directory=True)
        except (OSError,NotImplementedError):self.skipTest('host cannot create symlinks')
        self.addCleanup(lambda:link.unlink(missing_ok=True))
        with self.assertRaisesRegex(ValueError,'non-symlink'):summarize_csv(link,Path('records.csv'))
    def test_rejects_oversized_file(self):
        self.csv.write_bytes(b'x'*65537)
        with self.assertRaisesRegex(ValueError,'byte budget'):summarize_csv(self.root,Path('records.csv'))
    def test_rejects_too_many_records(self):
        rows=''.join(f'AB-{i:03d},Support,1,LOW\n' for i in range(1001))
        with self.assertRaisesRegex(ValueError,'too many'):self.run_case(HEADER+rows)
    def test_unicode_error_not_data_leak(self):
        self.csv.write_bytes(b'\xff\xfe\xff')
        with self.assertRaisesRegex(ValueError,'read or parsed'):summarize_csv(self.root,Path('records.csv'))
    def test_sql_or_shell_like_id_remains_rejected_data(self):
        with self.assertRaisesRegex(ValueError,'ticket id'):self.run_case(HEADER+'AB-001;rm,Support,1,LOW\n')

if __name__=='__main__':unittest.main()

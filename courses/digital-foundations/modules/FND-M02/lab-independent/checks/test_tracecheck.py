"""Published student contract. Starter failures are intentional; no solution is stored here."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'starter'))
from tracecheck import summarize

class TranscriptContract(unittest.TestCase):
    def test_all_zero(self):
        self.assertEqual(summarize(['0|inventory','0|parse']),{'total':2,'zero':2,'nonzero':0,'failures':[]})
    def test_mixed_codes(self):
        self.assertEqual(summarize(['0|inventory','3|synthetic-alert','2|bad-input']),
                         {'total':3,'zero':1,'nonzero':2,'failures':[{'label':'synthetic-alert','status':3},{'label':'bad-input','status':2}]})
    def test_empty_input(self):
        self.assertEqual(summarize([]),{'total':0,'zero':0,'nonzero':0,'failures':[]})
    def test_rejects_non_numeric(self):
        with self.assertRaises(ValueError):summarize(['oops|inventory'])
    def test_rejects_negative_or_out_of_range(self):
        for text in ('-1|inventory','256|inventory','+2|inventory'):
            with self.subTest(text=text), self.assertRaises(ValueError):summarize([text])
    def test_rejects_shell_like_labels(self):
        for text in ('0|ls;rm','0|my command','0|$(command)'):
            with self.subTest(text=text),self.assertRaises(ValueError):summarize([text])
    def test_rejects_duplicates(self):
        with self.assertRaises(ValueError):summarize(['0|inventory','1|inventory'])
    def test_rejects_wrong_field_count(self):
        with self.assertRaises(ValueError):summarize(['0|inventory|unexpected'])
    def test_rejects_wrong_container_and_too_many(self):
        with self.assertRaises(ValueError):summarize('0|inventory')
        with self.assertRaises(ValueError):summarize([f'0|job-{i}' for i in range(101)])
if __name__=='__main__':unittest.main()

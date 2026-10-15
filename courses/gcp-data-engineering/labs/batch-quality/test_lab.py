import unittest
from quality import validate_batch
H='order_id,order_date,total,region\n'
class QualityTests(unittest.TestCase):
 def test_clean_batch(self):
  x=validate_batch(H+'1,2026-10-14,13.25,APAC\n2,2026-10-15,0.00,EMEA\n')
  self.assertTrue(x['is_safe_to_load']);self.assertEqual(len(x['accepted']),2)
 def test_duplicate_keys(self):
  x=validate_batch(H+'1,2026-10-14,3.00,APAC\n1,2026-10-14,3.00,APAC\n')
  self.assertEqual(len(x['rejected_rows']),1);self.assertFalse(x['is_safe_to_load'])
 def test_invalid_numeric(self):
  for n in ('NaN','-2.00','1.001','Infinity'):
   with self.subTest(n=n):self.assertFalse(validate_batch(H+f'1,2026-10-14,{n},APAC\n')['is_safe_to_load'])
 def test_header_reorder_rejected(self):
  with self.assertRaisesRegex(ValueError,'schema'):validate_batch('order_date,order_id,total,region\n')
 def test_missing_column_rejected(self):
  self.assertFalse(validate_batch(H+'1,2026-10-14,3.00\n')['is_safe_to_load'])
 def test_unsupported_region(self):
  self.assertFalse(validate_batch(H+'1,2026-10-14,3.00,UNDEFINED\n')['is_safe_to_load'])
if __name__=='__main__':unittest.main()

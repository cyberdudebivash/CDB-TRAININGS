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
 def test_header_only_batch_not_safe(self):
  result=validate_batch(H)
  self.assertFalse(result['is_safe_to_load'])
  self.assertEqual(result['rejected_rows'][0]['reasons'],['empty batch'])
 def test_only_canonical_dates_accepted(self):
  for value in ('2026-W42-4','20261014','2026-02-30','2026-1-1'):
   with self.subTest(value=value):
    self.assertFalse(validate_batch(H+f'1,{value},3.00,APAC\n')['is_safe_to_load'])
 def test_blank_identifier_rejected(self):
  self.assertFalse(validate_batch(H+' ,2026-10-14,3.00,APAC\n')['is_safe_to_load'])
 def test_header_reorder_rejected(self):
  with self.assertRaisesRegex(ValueError,'schema'):validate_batch('order_date,order_id,total,region\n')
 def test_missing_column_rejected(self):
  self.assertFalse(validate_batch(H+'1,2026-10-14,3.00\n')['is_safe_to_load'])
 def test_unsupported_region(self):
  self.assertFalse(validate_batch(H+'1,2026-10-14,3.00,UNDEFINED\n')['is_safe_to_load'])
if __name__=='__main__':unittest.main()

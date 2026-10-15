import tempfile
import unittest
from pathlib import Path
from reconcile import reconcile,money
class ReconciliationTests(unittest.TestCase):
    def check(self,inv,pay):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'invoices.csv';b=Path(d)/'payments.csv'
            a.write_text(inv,encoding='utf-8');b.write_text(pay,encoding='utf-8')
            return reconcile(a,b)
    def test_customer_balances(self):
        got=self.check('invoice_id,amount\nA,15.00\nB,7.50\nC,2.00\nD,3.00\n', 'payment_id,invoice_id,amount\np1,A,10.00\np2,A,5.00\np3,B,10.00\np4,C,1.00\n')
        self.assertEqual({r['invoice_id']:r['state'] for r in got},{'A':'SETTLED','B':'OVERPAID','C':'UNDERPAID','D':'UNPAID'})
    def test_duplicate_payment_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate payment'):
            self.check('invoice_id,amount\nA,3.00\n','payment_id,invoice_id,amount\np,A,1.00\np,A,1.00\n')
    def test_unknown_invoice_rejected(self):
        with self.assertRaisesRegex(ValueError,'unknown invoice'):
            self.check('invoice_id,amount\nA,3.00\n','payment_id,invoice_id,amount\np,B,1.00\n')
    def test_non_finite_money_rejected(self):
        for value in ('NaN','Infinity','-1.00','0.001','abc'):
            with self.subTest(value=value),self.assertRaises(ValueError):money(value)
    def test_invalid_headers_rejected(self):
        with self.assertRaisesRegex(ValueError,'schema'):
            self.check('id,amount\nA,3.00\n','payment_id,invoice_id,amount\n')
    def test_duplicate_invoice_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate invoice'):
            self.check('invoice_id,amount\nA,3.00\nA,4.00\n','payment_id,invoice_id,amount\n')
if __name__=='__main__': unittest.main()

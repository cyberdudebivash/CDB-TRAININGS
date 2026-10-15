"""Reconcile customer invoice ledger and recorded payments, offline and deterministic."""
from __future__ import annotations
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

CENTS = Decimal('0.01')
def money(value: str) -> Decimal:
    try:
        number=Decimal(value)
        if not number.is_finite() or number < 0 or number != number.quantize(CENTS):
            raise ValueError('amount must be nonnegative exact cents')
        return number
    except (InvalidOperation, TypeError) as exc:
        raise ValueError('invalid money value') from exc

def rows(path: Path, required: set[str]) -> list[dict[str,str]]:
    with Path(path).open('r', encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames or set(reader.fieldnames) != required:
            raise ValueError('unexpected CSV schema')
        values=list(reader)
    for row in values:
        if None in row or any(v is None for v in row.values()):
            raise ValueError('malformed CSV row')
    return values

def reconcile(invoices: Path, payments: Path) -> list[dict[str,str]]:
    invoice_map:dict[str, Decimal]={}
    for row in rows(invoices, {'invoice_id','amount'}):
        key=row['invoice_id'].strip()
        if not key or key in invoice_map: raise ValueError('empty or duplicate invoice id')
        invoice_map[key]=money(row['amount'])
    paid:dict[str,Decimal]={}
    seen:set[str]=set()
    for row in rows(payments, {'payment_id','invoice_id','amount'}):
        pid=row['payment_id'].strip()
        iid=row['invoice_id'].strip()
        if not pid or pid in seen: raise ValueError('empty or duplicate payment id')
        if iid not in invoice_map: raise ValueError('payment refers to unknown invoice')
        seen.add(pid)
        paid[iid]=paid.get(iid,Decimal('0.00'))+money(row['amount'])
    report=[]
    for iid in sorted(invoice_map):
        expected=invoice_map[iid]; actual=paid.get(iid,Decimal('0.00'))
        state='SETTLED' if actual==expected else 'UNPAID' if actual==0 else 'UNDERPAID' if actual<expected else 'OVERPAID'
        report.append({'invoice_id':iid, 'due':str(expected), 'paid':str(actual), 'state':state})
    return report

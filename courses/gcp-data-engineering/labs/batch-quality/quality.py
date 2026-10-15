"""Pre-ingestion offline gate for a would-be Cloud Storage to BigQuery batch.
No actual GCP APIs are called and no cloud resource is created.
"""
from __future__ import annotations
import csv
import io
import re
from datetime import date
from decimal import Decimal, InvalidOperation
FIELDS=['order_id','order_date','total','region']
REGIONS={'APAC','EMEA','AMER'}

def validate_batch(raw: str) -> dict:
    reader=csv.DictReader(io.StringIO(raw))
    if reader.fieldnames != FIELDS: raise ValueError('schema mismatch or reordered columns')
    ids=set(); accepted=[]; errors=[]; rows_seen=0
    for n,row in enumerate(reader, start=2):
        rows_seen+=1
        failures=[]
        if None in row or any(v is None for v in row.values()):
            failures.append('column count')
        else:
            if not row['order_id'].strip() or row['order_id'] in ids:failures.append('duplicate/empty id')
            try:
                if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', row['order_date']):
                    raise ValueError('date must be YYYY-MM-DD')
                date.fromisoformat(row['order_date'])
            except ValueError:failures.append('invalid date')
            try:
                v=Decimal(row['total'])
                if not v.is_finite() or v<0 or v!=v.quantize(Decimal('0.01')):raise ValueError()
            except (InvalidOperation,ValueError):failures.append('invalid total')
            if row['region'] not in REGIONS:failures.append('unknown region')
        if failures:
            errors.append({'line':n,'reasons':failures})
        else:
            ids.add(row['order_id']);accepted.append(row)
    if rows_seen==0:
        errors.append({'line':1,'reasons':['empty batch']})
    return {'accepted':accepted,'rejected_rows':errors,'is_safe_to_load':len(errors)==0 and rows_seen>0}

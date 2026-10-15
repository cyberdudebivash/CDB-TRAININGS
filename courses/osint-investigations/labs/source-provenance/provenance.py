"""Synthetic public-interest claim corroboration; no internet or person targeting."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
@dataclass(frozen=True)
class Evidence:
    document_id: str
    publisher: str
    origin_group: str
    claim: str
    supports: bool
    body: bytes

def assess(records: list[Evidence], expected_claim: str) -> dict:
    if not expected_claim.strip():raise ValueError('claim required')
    seen_ids=set(); groups={}
    hashes=[]
    for r in records:
        if not all((r.document_id.strip(),r.publisher.strip(),r.origin_group.strip())):
            raise ValueError('incomplete source metadata')
        if r.document_id in seen_ids:raise ValueError('duplicate evidence id')
        seen_ids.add(r.document_id)
        if r.claim != expected_claim: raise ValueError('mixed claim set')
        hashes.append({'document_id':r.document_id,'sha256':hashlib.sha256(r.body).hexdigest()})
        groups.setdefault(r.origin_group,set()).add(r.supports)
    supporting=sum(choices=={True} for choices in groups.values())
    opposing=sum(choices=={False} for choices in groups.values())
    conflicts=sum(len(choices)>1 for choices in groups.values())
    return {'claim':expected_claim,'independent_support_groups':supporting,'independent_oppose_groups':opposing,
            'conflicted_groups':conflicts,'corroborated':supporting>=2 and opposing==0 and conflicts==0,
            'evidence_hashes':sorted(hashes,key=lambda x:x['document_id'])}

"""Schema and permission guard for untrusted model-proposed tool actions.
Educational component only: no LLM or external API is connected.
"""
from __future__ import annotations
import json
from dataclasses import dataclass

ALLOWED = {'lookup_invoice', 'draft_reply'}
MAX_BYTES = 4096
@dataclass(frozen=True)
class Decision:
    accepted: bool
    reason: str
    requires_human: bool = False
    action: str | None = None

def authorize(raw: str, *, consented_invoice_ids: set[str]) -> Decision:
    if not isinstance(raw,str) or len(raw.encode('utf-8')) > MAX_BYTES:
        return Decision(False,'invalid or oversized payload')
    def unique_pairs(pairs: list[tuple[str,object]]) -> dict:
        result={}
        for key,value in pairs:
            if key in result:
                raise ValueError('duplicate JSON object key')
            result[key]=value
        return result
    try:
        proposal=json.loads(raw, object_pairs_hook=unique_pairs)
    except (ValueError,TypeError,RecursionError):
        return Decision(False,'not valid JSON')
    if type(proposal) is not dict or set(proposal) != {'action','arguments'}:
        return Decision(False,'unexpected envelope fields')
    action=proposal['action'];args=proposal['arguments']
    if type(action) is not str or action not in ALLOWED or type(args) is not dict:
        return Decision(False,'unauthorized action or invalid arguments')
    if action=='lookup_invoice':
        if set(args)!={'invoice_id'} or type(args.get('invoice_id')) is not str:
            return Decision(False,'invalid lookup schema')
        if args['invoice_id'] not in consented_invoice_ids:
            return Decision(False,'invoice not in authorized scope')
        return Decision(True,'read-only lookup allowed',False,action)
    if set(args)!={'recipient','body'} or not all(type(args.get(k)) is str for k in ('recipient','body')):
        return Decision(False,'invalid draft schema')
    if not 1<=len(args['body'])<=2000 or not 1<=len(args['recipient'])<=160:
        return Decision(False,'invalid draft lengths')
    return Decision(True,'draft permitted; human approval required before delivery',True,action)

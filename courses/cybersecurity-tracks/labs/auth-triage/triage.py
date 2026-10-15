"""A bounded offline authentication triage exercise over synthetic normalized events."""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
@dataclass(frozen=True)
class AuthEvent:
    event_id:str
    account:str
    source:str
    success:bool
    when:datetime

def detect(events:list[AuthEvent], *, threshold:int=3, window:timedelta=timedelta(minutes=5)) -> list[dict]:
    if type(threshold) is not int or not 2<=threshold<=100 or not isinstance(window,timedelta) or window<=timedelta(0):
        raise ValueError('invalid detection settings')
    grouped=defaultdict(list); seen=set()
    for event in events:
        if not isinstance(event,AuthEvent) or any(not isinstance(v,str) or not v.strip() for v in (event.event_id,event.account,event.source)) or type(event.success) is not bool or not isinstance(event.when,datetime) or event.when.tzinfo is None or event.when.utcoffset() is None:
            raise ValueError('event fields, boolean outcome and timezone-aware datetime required')
        if event.event_id in seen:raise ValueError('duplicate event id')
        seen.add(event.event_id)
        if not event.success:
            grouped[(event.account,event.source)].append(event)
    findings=[]
    for (account,source),failures in sorted(grouped.items()):
        failures.sort(key=lambda e:(e.when,e.event_id))
        start=0
        for end,latest in enumerate(failures):
            while latest.when-failures[start].when>window:
                start+=1
            if end-start+1>=threshold:
                evidence=failures[start:end+1]
                findings.append({'account':account,'source':source,'last_seen':latest.when.astimezone(timezone.utc).isoformat(),
                                 'event_ids':[e.event_id for e in evidence]})
                break
    return findings

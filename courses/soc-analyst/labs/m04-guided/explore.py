"""First look at the data (guided lab, step A).  Usage:  python m04-guided/explore.py <events.enriched.jsonl>"""
import collections
import json
import sys

rows = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8")]
print(f"events: {len(rows)}   first: {rows[0]['@timestamp']}   last: {rows[-1]['@timestamp']}")
print("by EventID:", dict(sorted(collections.Counter(r["EventID"] for r in rows).items())))
fails = [r for r in rows if r["EventID"] == 4625]
src = collections.defaultdict(lambda: {"fails": 0, "accounts": set()})
for r in fails:
    src[r["IpAddress"]]["fails"] += 1
    src[r["IpAddress"]]["accounts"].add(r["TargetUserName"])
print("\nTop failing sources (failures, distinct accounts):")
for ip, d in sorted(src.items(), key=lambda kv: (-kv[1]["fails"], kv[0]))[:8]:
    print(f"  {ip:16} failures={d['fails']:4}  distinct_accounts={len(d['accounts']):3}")
acct = collections.Counter(r["TargetUserName"] for r in fails)
print("\nTop failing accounts:", acct.most_common(5))

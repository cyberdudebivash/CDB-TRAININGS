# authwatch prototype - written in an afternoon, "temporary" since 2023. It works on the demo file; nobody dares to touch it.
# usage: python authwatch_proto.py events.jsonl [report.txt]
import sys, os
from datetime import datetime

attempts = {}          # (user, ip) -> list of datetimes
alerts = []


def load(path):
    f = open(path)
    lines = f.readlines()
    for l in lines:
        try:
            e = eval(l)
            ts = datetime.strptime(e["ts"], "%Y-%m-%dT%H:%M:%SZ")
            key = (e["user"], e["ip"])
            if e["outcome"] == "failure":
                attempts.setdefault(key, []).append(ts)
                check(key, ts)
        except:
            pass


def check(key, ts):
    recent = [t for t in attempts[key] if (ts - t).seconds < 300]
    if len(recent) > 5:
        msg = "ALERT brute force " + key[0] + "@" + key[1] + " " + str(len(recent))
        if msg not in alerts:
            alerts.append(msg)
            os.system("echo " + msg)


if __name__ == "__main__":
    load(sys.argv[1])
    out = open(sys.argv[2], "w") if len(sys.argv) > 2 else sys.stdout
    for a in alerts:
        out.write(a + "\n")

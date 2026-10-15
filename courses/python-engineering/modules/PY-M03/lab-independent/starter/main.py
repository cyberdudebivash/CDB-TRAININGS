"""Command line: python main.py FILE [N]"""
import sys

import report


def main(argv):
    if not 1 <= len(argv) <= 2:
        print("usage: fleetlog FILE [N]", file=sys.stderr)
        return 2
    try:
        values = report.consumption(report.load(argv[0]))
        n = int(argv[1]) if len(argv) == 2 else 3
        print(report.render(dict(report.worst(values, n))))
    except (ValueError, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

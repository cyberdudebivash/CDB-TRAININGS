"""rulekit - match events against rules and alert when a rule has matched often enough for one source (PY-M12 independent lab).

README.md is the specification; this file only holds the names the checks import. Replace every stub with a real implementation (the stubs raise NotImplementedError
or are empty). Decide yourself what is a frozen dataclass, what is a plain class and what is a Protocol, and keep the state of one engine out of every other engine.
"""
from __future__ import annotations

import enum
from typing import Protocol, runtime_checkable


class Severity(enum.IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@runtime_checkable
class Matcher(Protocol):
    """Anything with matches(event) -> bool."""

    def matches(self, event: "Event") -> bool: ...


class FrozenMap:                 # a read-only, hashable mapping of text to text (README: FrozenMap)
    pass


class Event:                     # README: Event
    pass


class MatcherOps:                # README: the operators & | ~
    pass


class KindIs:
    pass


class FieldEquals:
    pass


class SeverityAtLeast:
    pass


class AllOf:
    pass


class AnyOf:
    pass


class Not:
    pass


class Rule:
    pass


class Alert:
    pass


class RuleEngine:
    pass

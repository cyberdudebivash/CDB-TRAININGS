---
id: PY-M12
title: "Classes, dataclasses and object-oriented design"
course: COURSE-PY-ENG
level: 2
audience: "Programmers who have finished PY-M01 to PY-M03 and now need to design the objects of a program: values, state, behaviour behind small interfaces, and code that does not leak state between instances"
prerequisites:
  - "PY-M01 (language core), PY-M02 (pytest) and PY-M03 (types and project layout)"
  - "Python 3.11 or newer; the labs and every code block of this lesson were executed on 3.11, 3.12, 3.13, 3.14 and 3.15 (see docs/qa/LAB_EXECUTION_EVIDENCE.md)"
  - "pytest 9.1.1 from labs/requirements.txt; no network, no account, no paid service"
estimated_time_hours: {lesson: 3.0, guided_lab: 2.5, independent_lab: 2.5, total: 8.0}
status: BUILT_NOT_SME_REVIEWED
versions_cited: {python: "3.11-3.15 (R-005); feature availability by version executed in this lesson (R-096)", pytest: "9.1.1"}
last_verified: 2026-10-15
---

# PY-M12 - Classes, dataclasses and object-oriented design

## Learning objectives

By the end of this module you can:

| ID | You can... |
|---|---|
| **LO1** | Tell instance state from class state, find and fix the bugs that come from a shared mutable class attribute or a mutable default, and say what a leading underscore, name mangling and `__slots__` do and do not protect. |
| **LO2** | Model values with `dataclass` (`frozen`, `slots`, `kw_only`, `default_factory`, `__post_init__`) and define equality, hashing, ordering and `repr` that agree with each other; explain why changing an object that is a dictionary key loses it. |
| **LO3** | Protect invariants with constructors and properties: validate at the boundary, make values immutable, remember that `bool` is an `int`, and write a boundary check that is correct for its unit. |
| **LO4** | Use `super()` and the method resolution order correctly, prefer composition to inheritance, and choose between an abstract base class, a `Protocol` and plain duck typing, knowing what a runtime protocol check does not verify. |
| **LO5** | Build small, testable designs: Strategy, Observer and a registry factory without shared state or leaked subscribers, and test them for the properties that matter (equality, immutability, isolation). |

Every objective is taught here, practised in a lab and assessed (see `outcomes.yaml`).

## 1. Why this matters

Most Python programs are built from objects, and most of their hard-to-find bugs are about **state**: who owns it, who can change it, and whether two things that look equal behave as equal. The 2025 handbook treats object-oriented programming twice, an introduction (PDF pages 40 to 45) and an "advanced" chapter (pages 48 to 55), plus the special methods on pages 64 to 66. It covers the right topics, classes and objects, class versus instance variables, properties, inheritance, abstract classes, composition, special methods and design patterns, but its examples contain errors that a learner would copy, and it leaves out what modern Python code uses every day (dataclasses, `Protocol`, `__slots__`, immutability).

The chapter's errors are not subtle once you run the code. Each of the following is executed in this lesson on five Python versions:

- the **Observer** example keeps its list of observers in a *class* variable (`observers = []`), so every subject in the program shares one list (section 2);
- the **name-mangling** explanation says `self.__secret` becomes `_user__secret`; the real name keeps the capital: `_User__secret` (section 3);
- the **temperature** property rejects `value < -273`, which refuses valid temperatures between -273.15 and -273 and is wrong at exactly absolute zero (section 3);
- the **abstract class** example's `Circle.area` uses an undefined name `r` and `3.14` instead of `math.pi` (section 8);
- the **factory** example names a parameter `type` (which hides the built-in) and chooses a class with an `if` ladder, and the section promises "12 important patterns" and shows four (section 9);
- "**composition ... is how real enterprise systems work**" is an unsupported claim; the lesson shows the design reason instead (section 7);
- the **operator-overloading** example returns a number from `__add__` and fails with `AttributeError` for a non-box (section 4.2).

The goal of the module is the skill, not the vocabulary: after it you can write a small domain model whose objects cannot be broken from the outside, whose equality means what you think it means, and whose behaviour you can swap without editing it. The labs build a money-and-accounts model (guided) and a rule engine (independent).

## 2. State: instance, class and the shared-list trap (LO1)

An attribute set on `self` belongs to **one object** (instance state). An attribute defined in the class body belongs to **the class** and is visible through every instance (class state).

```python run
class User:
    count = 0                      # class state: how many users exist

    def __init__(self, name):
        self.name = name           # instance state: one per user
        User.count += 1            # count on the CLASS

a, b = User("Alice"), User("Bob")
assert (a.name, b.name) == ("Alice", "Bob")
assert User.count == 2 and a.count == 2 and b.count == 2
```

Reading `a.count` finds the class attribute because the instance has none of its own. **Writing** through the instance is different: it creates an instance attribute that hides the class one, and the class counter never moves.

```python run
class Wrong:
    count = 0

    def __init__(self):
        self.count += 1            # reads Wrong.count (0), then creates self.count = 1

a, b = Wrong(), Wrong()
assert Wrong.count == 0, "the class counter never changed"
assert a.count == 1 and b.count == 1
assert "count" in vars(a)          # each instance now carries its own copy
```

The same mechanism turns a mutable class attribute into a bug that nobody sees at the line that causes it. This is the Observer example of the handbook (page 55), reduced to what matters:

```python run
class Subject:
    observers = []                 # ONE list, owned by the class

    def attach(self, observer):
        self.observers.append(observer)          # mutates the shared list; no assignment happens

a, b = Subject(), Subject()
a.attach("only for a")
assert b.observers == ["only for a"], "b never attached anything, yet it has an observer"
assert a.observers is b.observers is Subject.observers
```

Nothing is assigned, so nothing creates an instance attribute: `append` changes the one list that every instance sees. The fix is to create the list **in `__init__`**, once per object:

```python run
class Subject:
    def __init__(self):
        self.observers = []        # one list per instance

    def attach(self, observer):
        self.observers.append(observer)

a, b = Subject(), Subject()
a.attach("only for a")
assert a.observers == ["only for a"] and b.observers == []
```

A rule that prevents the whole family of bugs: **class attributes are for constants and deliberate counters; anything mutable that belongs to one object is created in `__init__`.** When a class attribute really is shared state, say so for readers and type checkers with `typing.ClassVar`.

The function form of the same trap is the mutable default argument, which you met in PY-M02: `def add(item, basket=[])` creates the list once, when the function is defined. The class form and the function form share one cause, an object created once and reused.

```python run
from dataclasses import dataclass, field, fields
from typing import ClassVar

def add_wrong(item, basket=[]):
    basket.append(item)
    return basket

assert add_wrong(1) == [1] and add_wrong(2) == [1, 2], "the default list survived between calls"

def add(item, basket=None):
    basket = [] if basket is None else basket
    return basket + [item]

assert add(1) == [1] and add(2) == [2]

@dataclass
class Order:
    registry_name: ClassVar[str] = "orders"      # class state, declared as such: not a field
    lines: list = field(default_factory=list)    # a new list per Order

assert [f.name for f in fields(Order)] == ["lines"]
assert Order().lines is not Order().lines
```

## 3. Hiding things: conventions, name mangling and properties (LO1, LO3)

Python has no `private` keyword. It has three conventions, and only the third changes the program:

| Spelling | Meaning | Enforced? |
|---|---|---|
| `self.name` | public: part of the interface | no |
| `self._name` | internal: "do not rely on this from outside" | no, a convention |
| `self.__name` | the name is **mangled** to `_ClassName__name` | renamed, not hidden |

Mangling exists so that a base class and a subclass can each have an `__x` without overwriting each other. It is not a security feature, and the mangled name keeps the capital letter of the class name (the handbook writes `_user__secret`, which does not exist):

```python run
class User:
    def __init__(self):
        self.__secret = 1

u = User()
assert vars(u) == {"_User__secret": 1}
assert u._User__secret == 1                       # reachable by anyone who writes the mangled name
assert not hasattr(u, "_user__secret")            # the handbook's spelling is wrong
try:
    u.__secret
except AttributeError:
    pass
else:
    raise AssertionError("the unmangled name does not exist")

class Base:
    def __init__(self):
        self.__id = "base"
class Child(Base):
    def __init__(self):
        super().__init__()
        self.__id = "child"                       # a different attribute: _Child__id
assert vars(Child()) == {"_Base__id": "base", "_Child__id": "child"}
```

What actually protects an object's rules is **a constructor that refuses bad values and properties that keep them true**. A property looks like an attribute to callers and runs code when it is read or set:

```python module=temperature
ABSOLUTE_ZERO_C = -273.15


class Temperature:
    """A temperature in degrees Celsius that can never be below absolute zero."""

    def __init__(self, celsius):
        self.celsius = celsius                       # goes through the setter: one place for the rule

    @property
    def celsius(self):
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"celsius must be a number, not {type(value).__name__}")
        if value < ABSOLUTE_ZERO_C:
            raise ValueError(f"{value} is below absolute zero ({ABSOLUTE_ZERO_C})")
        self._celsius = float(value)

    @property
    def kelvin(self):                                # computed, so it can never disagree with celsius
        return self._celsius + 273.15

    def __repr__(self):
        return f"Temperature({self._celsius!r})"
```

```python test
import pytest
from temperature import ABSOLUTE_ZERO_C, Temperature


def test_the_boundary_is_inclusive_and_exact():
    assert Temperature(-273.15).kelvin == pytest.approx(0.0)
    assert Temperature(-273.14).celsius == -273.14
    with pytest.raises(ValueError):
        Temperature(-273.16)


def test_values_between_minus_273_15_and_minus_273_are_valid():
    # the handbook's check (`value < -273`) would refuse all of these, including absolute zero itself
    for value in (-273.0, -273.1, -273.15):
        assert Temperature(value).celsius == value


def test_the_setter_runs_every_time_not_just_in_the_constructor():
    t = Temperature(20)
    t.celsius = 25
    assert t.celsius == 25.0
    with pytest.raises(ValueError):
        t.celsius = -300
    assert t.celsius == 25.0, "a refused assignment leaves the object unchanged"


def test_a_bool_is_not_a_temperature():
    # bool is a subclass of int: isinstance(True, int) is True, so the type check has to exclude it explicitly
    assert isinstance(True, int)
    with pytest.raises(TypeError):
        Temperature(True)


def test_kelvin_is_read_only():
    with pytest.raises(AttributeError):
        Temperature(0).kelvin = 1
```

Three points in that module are the lesson. **The rule lives in one place** (the setter), so the constructor cannot bypass it. **The boundary is written in the unit of the quantity**, and the handbook's `-273` differs from the physical constant by 0.15 degrees, which is the kind of off-by-a-fraction error that no test finds unless someone writes the boundary case. **`bool` needs an explicit exclusion** wherever "a number" is accepted, because `True` is the integer 1 (section 5 returns to this).

## 4. Dataclasses: values with little code (LO2)

A class that mostly holds data needs `__init__`, `__repr__` and `__eq__`, and writing them by hand invites inconsistency (a field added to `__init__` and forgotten in `__eq__`). `dataclasses.dataclass` generates them from the annotated fields:

```python run
from dataclasses import dataclass, field, fields, replace, FrozenInstanceError

@dataclass(frozen=True, slots=True, kw_only=True)
class Event:
    kind: str
    source: str
    tags: tuple = ()                               # immutable default: fine
    note: str = field(default="", compare=False)   # shown and stored, but ignored by == and hash

e = Event(kind="login", source="10.0.0.1")
assert repr(e) == "Event(kind='login', source='10.0.0.1', tags=(), note='')"
assert e == Event(kind="login", source="10.0.0.1", note="ignored by ==")
assert hash(e) == hash(Event(kind="login", source="10.0.0.1", note="x"))
assert [f.name for f in fields(e)] == ["kind", "source", "tags", "note"]

try:
    e.kind = "logout"
except FrozenInstanceError:
    pass
else:
    raise AssertionError("frozen=True forbids assignment")

assert replace(e, source="10.0.0.2").source == "10.0.0.2" and e.source == "10.0.0.1"   # a changed COPY
assert not hasattr(e, "__dict__")                                                        # slots=True: no per-instance dictionary

try:
    Event("login", "10.0.0.1")
except TypeError as exc:
    assert "positional" in str(exc)                                                      # kw_only=True: arguments must be named
else:
    raise AssertionError("kw_only forbids positional arguments")
```

The options and what they cost:

| Option | Effect | Use it when |
|---|---|---|
| `frozen=True` | assignment raises `FrozenInstanceError`; `__hash__` is generated | the object is a value (money, a coordinate, an event) |
| `slots=True` | no per-instance `__dict__`; smaller, faster attribute access, typos in attribute names fail | many instances, or you want typos to fail |
| `kw_only=True` | fields must be passed by name | more than two or three fields, so call sites stay readable |
| `order=True` | generates `<`, `<=`, `>`, `>=` comparing the fields **as a tuple, in field order** | the field order is the sort order you want |
| `field(default_factory=...)` | a new default object per instance | any mutable default |
| `field(compare=False)` | excluded from `==`, ordering and hash | metadata that is not part of identity |

A mutable default is **refused** at class-definition time instead of silently shared, which is what the plain-class version did in section 2:

```python run
from dataclasses import dataclass, field

try:
    @dataclass
    class Bad:
        items: list = []
except ValueError as exc:
    assert str(exc) == "mutable default <class 'list'> for field items is not allowed: use default_factory"
else:
    raise AssertionError("a list default must be refused")

@dataclass
class Good:
    items: list = field(default_factory=list)

assert Good().items is not Good().items
```

Validation that a type annotation cannot express belongs in `__post_init__`, which runs after the generated `__init__`. A *frozen* dataclass cannot assign `self.x = ...` there; use `object.__setattr__` to set a normalised value, and nowhere else:

```python run
from dataclasses import dataclass

@dataclass(frozen=True)
class Tags:
    items: tuple = ()

    def __post_init__(self):
        object.__setattr__(self, "items", tuple(sorted(set(self.items))))     # normalise: sorted, no duplicates, immutable

assert Tags(["b", "a", "b"]).items == ("a", "b")
assert Tags(["b", "a"]) == Tags(("a", "b")) and hash(Tags(["b", "a"])) == hash(Tags(("a", "b")))
```

`ClassVar` annotations are not fields, and `order=True` compares tuples, which is rarely right when part of the data is another unit (compare money in one currency only; the guided lab shows how):

```python run
from dataclasses import dataclass

@dataclass(order=True)
class Version:
    major: int
    minor: int

assert Version(1, 9) < Version(1, 10)                  # compared as (1, 9) < (1, 10), not as text
try:
    Version(1, 0) < (1, 1)
except TypeError:
    pass                                               # different types are never ordered
else:
    raise AssertionError("a dataclass is not comparable to a tuple")
```

### 4.1 Class methods, static methods and alternative constructors (LO2)

A **class method** receives the class (`cls`) instead of the instance. It is the tool for *alternative constructors*: a second way to build an object from something else (text, a dictionary, a file). Because it builds `cls(...)`, a subclass inherits a constructor that returns the subclass. A **static method** receives nothing: it is a plain function that lives in the class because it belongs with it. The handbook's `build(cls): return cls("Default")` (page 45) has the right shape.

```python run
from dataclasses import dataclass

@dataclass(frozen=True)
class Version:
    major: int
    minor: int

    @classmethod
    def parse(cls, text):                          # alternative constructor: Version.parse("3.14")
        major, minor = text.split(".")
        return cls(int(major), int(minor))

    @staticmethod
    def is_valid(text):                            # needs neither the class nor an instance
        parts = text.split(".")
        return len(parts) == 2 and all(p.isascii() and p.isdigit() for p in parts)

class Release(Version):
    pass

assert Version.parse("3.14") == Version(3, 14)
assert type(Release.parse("3.14")) is Release, "cls, not a hard-coded Version: subclasses get their own type"
assert Version.is_valid("3.14") and not Version.is_valid("3.x")
assert not Version.is_valid("\u0663.\u0661\u0664"), "str.isdigit() is true for digits of other scripts: isascii() excludes them"
```

### 4.2 Special methods: what Python calls when you write syntax (LO2, LO5)

Operators, `len()`, `for`, `with` and `print` are not magic: each is a call to a **special method** (a "dunder" method, from the double underscores) that your class may define. The handbook lists them on pages 44 and 64 to 66; the table is the part to remember.

| You write | Python calls | Contract |
|---|---|---|
| `repr(x)`, the REPL | `__repr__` | an unambiguous description for developers; for values, ideally text that rebuilds the object |
| `str(x)`, `print(x)` | `__str__` (falls back to `__repr__`) | readable text for people |
| `x == y`, `hash(x)` | `__eq__`, `__hash__` | agree with each other (section 5) |
| `x < y` | `__lt__` | return `NotImplemented` for types you do not support |
| `x + y` | `__add__` | return an object of the same kind; `NotImplemented` for unsupported types |
| `len(x)`, `bool(x)` | `__len__`, `__bool__` | without `__bool__`, an object is false when `len()` is 0 |
| `x[i]`, `for a in x`, `a in x` | `__getitem__` (or `__iter__`, `__contains__`) | indexing; iteration falls back to indexes 0, 1, 2 ... until `IndexError` |
| `x(...)` | `__call__` | an object that behaves like a function |
| `with x:` | `__enter__`, `__exit__` | `__exit__` runs even when the body raises; returning true suppresses the exception |

The handbook's operator-overloading example (page 44) returns a *number* from `__add__` and fails with a leaked implementation detail when the other operand is not a box:

```python run
class HandbookBox:
    def __init__(self, volume):
        self.volume = volume

    def __add__(self, other):
        return self.volume + other.volume          # an int, not a box: the result cannot be added again

assert HandbookBox(1) + HandbookBox(2) == 3
try:
    HandbookBox(1) + 5
except AttributeError:
    pass                                           # 'int' has no attribute 'volume': an internal detail, not a TypeError
else:
    raise AssertionError("expected the handbook version to fail with AttributeError")

class Box:
    def __init__(self, volume):
        self.volume = volume

    def __add__(self, other):
        if not isinstance(other, Box):
            return NotImplemented                  # Python then raises TypeError, or tries the other operand's __radd__
        return Box(self.volume + other.volume)

    def __repr__(self):
        return f"Box(volume={self.volume!r})"

assert repr(Box(1) + Box(2) + Box(3)) == "Box(volume=6)"
try:
    Box(1) + 5
except TypeError as exc:
    assert "unsupported operand" in str(exc)
else:
    raise AssertionError("adding a number to a Box must be a TypeError")
```

Container behaviour and truthiness come from two or three methods. The last assertion is the reason the guided lab tests that a `Ledger` keeps a bus it was given "even if that bus is falsy": an object with `__len__` returning 0 is false, so `bus or EventBus()` would replace it.

```python run
class Basket:
    def __init__(self, *items):
        self._items = list(items)

    def __len__(self):
        return len(self._items)

    def __getitem__(self, index):
        return self._items[index]

    def __repr__(self):
        return f"Basket({', '.join(map(repr, self._items))})"

b = Basket("a", "b")
assert len(b) == 2 and b[0] == "a"
assert list(b) == ["a", "b"] and "b" in b, "iteration and `in` fall back to __getitem__ with 0, 1, 2 ... until IndexError"
assert bool(Basket()) is False and bool(b) is True, "no __bool__: truthiness comes from __len__"
assert repr(b) == "Basket('a', 'b')"

class Quiet:
    def __len__(self):
        return 0

assert not Quiet(), "a perfectly good object can be falsy: test `is None`, not truthiness, for optional arguments"
```

`__call__` and the context-manager methods complete the set. The handbook's `__exit__(self, *args)` hides what the method receives and what its return value means:

```python run
class Greeter:
    def __init__(self, greeting):
        self.greeting = greeting

    def __call__(self, name):
        return f"{self.greeting}, {name}"

assert callable(Greeter("Hello")) and Greeter("Hello")("Ann") == "Hello, Ann"

events = []

class Resource:
    def __enter__(self):
        events.append("open")
        return self

    def __exit__(self, exc_type, exc, traceback):
        events.append("close")
        return False                               # True would suppress the exception; almost never what you want

try:
    with Resource():
        raise ValueError("boom")
except ValueError:
    pass
assert events == ["open", "close"], "__exit__ ran although the body raised"
```

## 5. Equality, hashing and the lost key (LO2)

Two rules tie `==` and `hash` together: objects that compare equal must have equal hashes, and an object's hash must not change while it is in a set or is a dictionary key. Python enforces part of the first rule for you:

```python run
from dataclasses import dataclass

class OnlyEq:
    def __eq__(self, other):
        return True

assert OnlyEq.__hash__ is None, "defining __eq__ alone makes the class unhashable"

@dataclass
class Plain:
    x: int

assert Plain.__hash__ is None, "a mutable dataclass with eq=True is unhashable on purpose"

@dataclass(frozen=True)
class Frozen:
    x: int

assert hash(Frozen(1)) == hash(Frozen(1)) and len({Frozen(1), Frozen(1)}) == 1
```

The second rule is on you. If an object's equality depends on mutable data, changing it after it went into a set or became a key **loses it**: the set looks in the bucket of the *new* hash, finds nothing, and the object is still in there under the old one.

```python run
class Key:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, Key) and self.value == other.value

    def __hash__(self):
        return hash(self.value)

k = Key(1)
seen = {k}
k.value = 2                                        # the hash changes while k is in the set
assert k not in seen, "looked up under the new hash: not found"
assert Key(1) not in seen, "looked up under the old hash: found, but no longer equal to the stored object"
assert len(seen) == 1, "it is still stored, unreachable"
```

The cure is structural, not careful use: make the type immutable (`frozen=True`), so the hash cannot change, and change a copy with `dataclasses.replace`. That is why `Money`, `Event` and the rule matchers of the labs are frozen.

`bool` deserves a line because it breaks validators silently: `isinstance(True, int)` is `True`, so `Money(True)` passes a naive `isinstance(cents, int)` check and becomes one cent.

```python run
assert isinstance(True, int) and True + True == 2
def cents_strict(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("cents must be an int")
    return value
assert cents_strict(5) == 5
try:
    cents_strict(True)
except TypeError:
    pass
else:
    raise AssertionError("a bool is not an amount")
```

## 6. Inheritance, `super()` and method resolution order (LO4)

Inheritance says "B **is a** kind of A, and everywhere an A is used a B must work". When Python looks for an attribute it searches the **method resolution order** (MRO), a single linear order of the class and its bases computed by the C3 rule: a class comes before its bases, and the order of bases in the `class` statement is kept.

```python run
class A: pass
class B(A): pass
class C(A): pass
class D(B, C): pass

assert [k.__name__ for k in D.__mro__] == ["D", "B", "C", "A", "object"]      # the diamond: A is last, once

try:
    class Bad(A, B):                              # A before its own subclass B: no consistent order exists
        pass
except TypeError as exc:
    assert "consistent method resolution order" in " ".join(str(exc).split())      # 3.11 and 3.12 wrap the message over two lines
else:
    raise AssertionError("inconsistent bases are refused")
```

`super()` means "the next class in the MRO of *the instance's* class", not "my parent". That is what makes **cooperative** multiple inheritance work: every class calls `super()`, and each method runs exactly once.

```python run
calls = []

class Base:
    def setup(self):
        calls.append("Base")

class Left(Base):
    def setup(self):
        calls.append("Left")
        super().setup()

class Right(Base):
    def setup(self):
        calls.append("Right")
        super().setup()

class Both(Left, Right):
    def setup(self):
        calls.append("Both")
        super().setup()

Both().setup()
assert calls == ["Both", "Left", "Right", "Base"], "Base ran once, after both middle classes"
```

Two traps are worth knowing. First, subclassing a built-in container does not make its methods call each other the way you would expect, so an override can be bypassed:

```python run
class LoggedDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.writes = []

    def __setitem__(self, key, value):
        self.writes.append(key)
        super().__setitem__(key, value)

d = LoggedDict()
d["a"] = 1
d.update(b=2)                                      # dict.update does not call the overridden __setitem__
assert d == {"a": 1, "b": 2} and d.writes == ["a"], "'b' was written but never logged"
```

Wrap the container instead (composition, section 7) or derive from `collections.UserDict`, which routes its methods through `__setitem__`. Second, `@dataclass(slots=True)` builds a *new* class, and until Python 3.13 the zero-argument `super()` inside its methods still pointed at the old one. The executed behaviour on the five versions of this course:

```python run
import sys
from dataclasses import dataclass

@dataclass
class Base:
    a: int

    def hello(self):
        return "base"

@dataclass(slots=True)
class Child(Base):
    b: int = 0

    def hello(self):
        return "child+" + super().hello()

if sys.version_info >= (3, 13):
    assert Child(1).hello() == "child+base"
else:
    try:
        Child(1).hello()
    except TypeError as exc:
        assert "super(type, obj)" in str(exc)
    else:
        raise AssertionError("expected the 3.11 and 3.12 behaviour")
```

On 3.11 and 3.12 write `super(Child, self).hello()` or avoid `slots=True` in a hierarchy that calls `super()`.

## 7. Composition: has-a (LO4)

The handbook's example is right in spirit: a `Car` *has an* `Engine`; it is not a kind of engine. The shape of the example hides the design choice. `Car.__init__` creates its own `Engine`, so nothing can substitute a different engine, for example a fake one in a test. **Inject the part** instead:

```python run
class Engine:
    def start(self):
        return "engine started"

class FakeEngine:
    def __init__(self):
        self.started = 0

    def start(self):
        self.started += 1
        return "fake started"

class Car:
    def __init__(self, engine):                    # the dependency is a parameter
        self._engine = engine

    def start(self):
        return self._engine.start()                # delegation: Car forwards, it does not inherit

assert Car(Engine()).start() == "engine started"
fake = FakeEngine()
assert Car(fake).start() == "fake started" and fake.started == 1
```

A useful test for "is-a or has-a": ask whether *every operation of the base class makes sense on the new class*. A `Ledger` that inherits from `dict` accepts `ledger.update(...)` and `ledger.clear()`, which bypass every rule the ledger exists to enforce; a ledger that **has** a dict exposes only the methods you write. The handbook's claim that composition "is how real enterprise systems work" is not evidence; the reasons above are. In the guided lab a test asserts that `Ledger` does not inherit from anything.

## 8. Abstract base classes, protocols and duck typing (LO4)

Three tools describe "anything that can do X":

| Tool | Declared where | Checked | Use it when |
|---|---|---|---|
| Duck typing | nowhere | when the call happens | small scripts and obvious interfaces |
| `abc.ABC` + `@abstractmethod` | in the base class; subclasses **inherit** | at instantiation (`TypeError`) | you own the hierarchy and want shared code in the base |
| `typing.Protocol` | in the *user*; implementers need not know it | by a static type checker; at runtime only if `@runtime_checkable`, and then names only | you want an interface for classes you do not control |

The handbook's abstract-class example does not run: `Circle.area` uses `r`, which is not defined anywhere, and `3.14` where the standard library has `math.pi`.

```python run
import math
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self):
        ...

try:
    Shape()
except TypeError as exc:
    assert "abstract" in str(exc)                  # the wording differs a little between versions; the TypeError does not
else:
    raise AssertionError("an abstract class cannot be instantiated")

class BrokenCircle(Shape):                         # the handbook's version
    def area(self):
        return 3.14 * r * r                        # r was never defined

try:
    BrokenCircle().area()
except NameError:
    pass
else:
    raise AssertionError("the handbook's example raises NameError")

class Circle(Shape):
    def __init__(self, r):
        self.r = r

    def area(self):
        return math.pi * self.r ** 2

assert round(Circle(2).area(), 4) == 12.5664 and Circle(2).area() != 3.14 * 4
```

A `Protocol` needs no base class. Be exact about what `@runtime_checkable` verifies: **only that the method names exist**, never their signatures:

```python run
from typing import Protocol, runtime_checkable

@runtime_checkable
class Speaks(Protocol):
    def speak(self) -> str: ...

class Dog:
    def speak(self):
        return "Bark"

class Confused:
    def speak(self, loud, extra):                  # wrong signature for the protocol
        return "?"

assert isinstance(Dog(), Speaks) and Speaks not in Dog.__mro__      # no inheritance involved
assert isinstance(Confused(), Speaks), "isinstance only looks for the name 'speak'"
```

Signatures are checked by a static type checker (mypy, pyright), which you met in PY-M03. In a subclass, mark an intended override with `typing.override` (Python 3.12+) so the checker reports an override that matches nothing, for example after a rename in the base class. On 3.11 the decorator does not exist, so code that must run there guards the import:

```python run
import typing

override = getattr(typing, "override", None)
if override is None:                               # Python 3.11
    def override(method):
        return method                              # documentation only; install typing_extensions to get the real one

class Base:
    def run(self):
        return "base"

class Child(Base):
    @override
    def run(self):
        return "child"

assert Child().run() == "child"
```

## 9. Patterns the Python way (LO5)

The handbook promises twelve design patterns and shows four, as skeletons that do nothing (`class Paytm(PaymentStrategy): ...`). The labs build working versions of three of them. Each needs less code in Python than in the languages the patterns come from, because functions are objects.

**Strategy** is "choose the algorithm at run time". A function, or anything callable, is already a strategy; a `Protocol` documents the shape when there is more than one method.

```python run
def flat(amount):
    return 25

def percent(rate):
    def policy(amount):
        return amount * rate // 10_000             # integers only: basis points
    return policy

def fee_for(amount, strategy):
    return strategy(amount)

assert fee_for(100_000, flat) == 25
assert fee_for(100_000, percent(150)) == 1_500
assert [fee_for(1_000, s) for s in (flat, percent(100))] == [25, 10]
```

**Factory** is "make the right object from a description". An `if type == "circle"` ladder must be edited for every new kind, and a parameter called `type` hides the built-in. A **registry**, a mapping from a name to a constructor, is open for extension and fails with a clear message for an unknown name:

```python run
import math

SHAPES = {}

def register(kind):
    def decorator(factory):
        if kind in SHAPES:
            raise ValueError(f"already registered: {kind!r}")
        SHAPES[kind] = factory
        return factory
    return decorator

@register("circle")
def circle(r):
    return ("circle", math.pi * r * r)

@register("square")
def square(side):
    return ("square", side * side)

def make(kind, **params):                          # `kind`, not `type`
    try:
        factory = SHAPES[kind]
    except KeyError:
        raise ValueError(f"unknown shape: {kind!r}") from None
    return factory(**params)

assert make("square", side=3) == ("square", 9)
try:
    make("triangle")
except ValueError as exc:
    assert "unknown shape" in str(exc)
try:
    register("square")(square)
except ValueError:
    pass
else:
    raise AssertionError("duplicate kinds must be refused")
```

**Singleton** ("exactly one instance") is shown in the handbook with `__new__`. That version has two problems that the executed code makes visible: `__init__` runs again on every call, and nothing makes it safe for threads. In Python the idiomatic singleton is a **module-level object** (a module is imported once), or a function cached with `functools.cache`.

```python run
class Single:
    _instance = None
    inits = 0

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        type(self).inits += 1                      # runs on EVERY Single(), although there is one object
        self.state = "fresh"

a = Single()
a.state = "changed"
b = Single()
assert a is b and Single.inits == 2
assert b.state == "fresh", "the second call re-initialised the one shared object"
```

**Observer** is "tell interested parties when something happens". The traps are the shared list of section 2, subscribers that can never be removed, one failing subscriber stopping the rest, and the bus keeping its subscribers alive forever. A bound method needs a special weak reference, because a plain `weakref` to `obj.method` dies at once: the method object is created for the call and has no other owner.

```python run
import gc
import weakref

class Listener:
    def update(self, event):
        pass

listener = Listener()
dead = weakref.WeakSet()
dead.add(listener.update)
gc.collect()
assert len(dead) == 0, "the bound-method object had no owner, so the WeakSet dropped it at once"

ref = weakref.WeakMethod(listener.update)           # holds the object and the function, weakly
assert ref() is not None
del listener
gc.collect()
assert ref() is None, "WeakMethod notices that the listener is gone"
```

The guided lab's `EventBus` uses exactly this: a bound-method subscriber is held through `WeakMethod`, plain functions are held normally, `subscribe` returns an `unsubscribe` function, and `publish` runs every handler even if one raises.

## 10. Testing a design (LO5)

Objects need tests for the properties that make them safe to share, not only for their results. The same four questions find most defects:

1. **Equality and hash**: equal objects have equal hashes; unequal ones differ; the object works as a dict key.
2. **Immutability**: assignment to a value raises; changing the input afterwards does not change the object.
3. **Isolation**: two instances share nothing; operating on one leaves the other untouched.
4. **Refusal**: a bad value is rejected with the right exception, and the object is **unchanged** afterwards.

```python module=counter
class Counter:
    """Counts events per name. Each Counter has its own tallies."""

    def __init__(self, names=()):
        self._tallies = {name: 0 for name in names}

    def hit(self, name):
        if name not in self._tallies:
            raise KeyError(name)
        self._tallies[name] += 1

    def snapshot(self):
        return dict(self._tallies)                 # a copy, so callers cannot edit the tallies
```

```python test
import pytest
from counter import Counter


def test_two_counters_share_nothing():
    a, b = Counter(["x"]), Counter(["x"])
    a.hit("x")
    assert a.snapshot() == {"x": 1} and b.snapshot() == {"x": 0}


def test_the_snapshot_is_a_copy():
    c = Counter(["x"])
    c.snapshot()["x"] = 99
    assert c.snapshot() == {"x": 0}


def test_an_unknown_name_is_refused_and_changes_nothing():
    c = Counter(["x"])
    with pytest.raises(KeyError):
        c.hit("y")
    assert c.snapshot() == {"x": 0}


def test_the_input_is_not_kept_by_reference():
    names = ["x"]
    c = Counter(names)
    names.append("y")
    with pytest.raises(KeyError):
        c.hit("y")
```

A defect that passes all four questions is rare. The guided lab's 160-odd checks and the instructors' hidden suite for the independent lab are built from exactly these questions applied to each class.

## 11. What differs between Python versions (executed)

Every row below was produced by running the same code on CPython 3.11, 3.12, 3.13, 3.14 and 3.15 (R-096) and is asserted again by this lesson on whichever interpreter runs it.

| Behaviour | 3.11 | 3.12 | 3.13 | 3.14 | 3.15 |
|---|---|---|---|---|---|
| `typing.override` exists | no | yes | yes | yes | yes |
| `copy.replace()` (and `__replace__` on dataclasses) | no | no | yes | yes | yes |
| zero-argument `super()` works in a `@dataclass(slots=True)` subclass | no | no | yes | yes | yes |
| a forward reference in a dataclass annotation needs quotes or `from __future__ import annotations` | yes | yes | yes | no | no |
| the `annotationlib` module exists | no | no | no | yes | yes |

```python run
import copy
import importlib.util
import sys
import typing
from dataclasses import dataclass

v = sys.version_info[:2]
assert hasattr(typing, "override") == (v >= (3, 12))
assert hasattr(copy, "replace") == (v >= (3, 13))
assert (importlib.util.find_spec("annotationlib") is not None) == (v >= (3, 14))

namespace = {}
source = "from dataclasses import dataclass\n@dataclass\nclass Node:\n    next: Later\n\nclass Later: pass\n"
try:
    exec(compile(source, "<annotations>", "exec"), namespace)
    deferred = True                                 # 3.14: annotations are evaluated lazily
except NameError:
    deferred = False                                # 3.11 to 3.13: evaluated at class creation, `Later` does not exist yet
assert deferred == (v >= (3, 14))

if hasattr(copy, "replace"):
    @dataclass(frozen=True)
    class P:
        x: int
    assert copy.replace(P(1), x=2) == P(2)
```

The course baseline is 3.11, so the labs avoid all four features; code that uses them must say which Python it needs.

## 12. Where the handbook text went

| Handbook (PDF page) | What it said | What this module does |
|---|---|---|
| 40 to 43 | "Python's MOST IMPORTANT SECTION": class and object, attributes, `__init__`, methods, `self`, inheritance, `super()`, polymorphism | sections 2, 4, 6 and 8 (the introductory pages say what a class is; the lesson assumes that and teaches what goes wrong) |
| 44 to 45 | encapsulation, abstraction, special methods, operator overloading (`__add__` returns a number), class methods | sections 3, 4.1, 4.2 and 8 |
| 48 | class and instance variables; class variables for "tracking objects" | section 2: both kinds, the `self.count += 1` trap, and the rule for what may be a class attribute |
| 49 to 50 | public, protected, private; `self.__secret` becomes `_user__secret` | section 3: the conventions as a table; the executed name is `_User__secret`; mangling is not protection |
| 50 to 51 | property decorator, with `value < -273` | section 3: setter, boundary at -273.15, `bool` excluded, a test of the boundary |
| 51 | inheritance kinds and the MRO | section 6: the MRO and C3 failure, cooperative `super()`, two traps |
| 52 | abstract classes and polymorphism | section 8: `ABC`, `Protocol`, what a runtime check verifies |
| 52 to 53 | composition ("how real enterprise systems work") | section 7: injection and delegation; the claim is replaced by a design reason |
| 54 to 55 | "12 patterns": four skeletons, with a shared observer list | section 9 and the labs: working Strategy, Factory, Singleton and Observer |
| 64 to 66 | `__str__` versus `__repr__`, `__len__`, `__getitem__`, `__call__`, `__enter__` / `__exit__` | section 4.2 (the `__repr__` example does not print what the page shows; `__exit__(self, *args)` hides what the method receives) |
| (absent) | dataclasses, `__slots__`, immutability, hashing, `Protocol` | sections 4, 5 and 8 |

## 13. Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| a list or dict in the class body | every instance sees every other instance's changes | create it in `__init__` or use `default_factory` |
| `self.count += 1` on a class attribute | the class counter never moves | `ClassName.count += 1` |
| a mutable object that defines `__eq__` and `__hash__` and is mutated in a set | the object cannot be found | `frozen=True`, change a copy |
| `isinstance(x, int)` to accept numbers | `True` is accepted | exclude `bool` first |
| a subclass of `dict` or `list` that overrides one method | other methods bypass it | wrap with composition or use `UserDict` |
| `@runtime_checkable` treated as a type check | a wrong signature passes | a static type checker checks signatures |
| `from x import *` of a class registry, or registering twice | silent replacement | refuse duplicates (`ValueError`) |
| catching `BaseException` in a notifier | `Ctrl+C` is swallowed | catch `Exception` |

## 14. Check yourself

1. A class has `items = []` in its body and `def add(self, x): self.items.append(x)`. What do two instances share, and what is the smallest change that fixes it?
2. Why does `Money(True)` succeed with `isinstance(cents, int)` as the only check, and what is the one-line fix?
3. Which two properties must `__eq__` and `__hash__` keep, and what does `frozen=True` guarantee about the second?
4. `class Ledger(dict)` is a bad idea even if the first version works. Name two methods that break its rules.
5. `isinstance(obj, SomeProtocol)` is true for an object whose method takes the wrong arguments. Why, and what catches it?

Answers are in the quiz feedback and are discussed in the lab notes; try them first.

## 15. Sources and verification trail

- The version table of section 11 and every assertion in this lesson: executed on CPython 3.11.17, 3.12.3, 3.13.16, 3.14.8 and 3.15.0 (R-096; reproduced by the lab matrix in `docs/qa/LAB_EXECUTION_EVIDENCE.md`). Language reference for the data model: <https://docs.python.org/3/reference/datamodel.html>; `dataclasses`: <https://docs.python.org/3/library/dataclasses.html>; `typing.Protocol`: <https://docs.python.org/3/library/typing.html#typing.Protocol> (R-005).
- Handbook corrections: finding F-PYH-011 (name-mangled spelling, absolute-zero bound, shared observer list, undefined `r`, `type` shadowing, "12 patterns").
- Not verified here and therefore not claimed: performance differences between slotted and unslotted classes (no benchmark was run); the behaviour of free-threaded builds with shared class state (see PY-M06 for the measured scope of that module).

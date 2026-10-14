"""Step A helper: print what the module under test does for a few inputs. Run from the lab folder:  python explore.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "starter"))

from orderkit import add_line, bulk_discount, order_total, parse_quantity  # noqa: E402

for text in ("3", " 12 ", "abc", "-3", "0"):
    print(f"parse_quantity({text!r}) -> {parse_quantity(text)!r}")
for quantity in (9, 10, 11, 50):
    print(f"bulk_discount({quantity}) -> {bulk_discount(quantity)}")
print("first basket :", add_line("pen", 1))
print("second basket:", add_line("ink", 2))
print("order_total  :", order_total(add_line("pen", 2, []), {"pen": __import__("decimal").Decimal("1.50")}))

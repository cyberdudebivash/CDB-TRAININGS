"""inventory - a small stock report script (PY-M03 guided lab starting point). Works for the sample file; has no type annotations."""
import csv
import sys


def load_products(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def total_value(products):
    return sum(int(p["qty"]) * float(p["price"]) for p in products)


def find_product(products, sku):
    for p in products:
        if p["sku"] == sku:
            return p


def low_stock(products):
    return [p["sku"] for p in products if p["qty"] < p["reorder_level"]]


def restock_plan(products, budget):
    plan = []
    for p in products:
        if p["qty"] < p["reorder_level"]:
            units = int(p["reorder_level"]) - int(p["qty"])
            cost = units * float(p["price"])
            if cost > budget:
                return None
            budget -= cost
            plan.append((p["sku"], units))
    return plan


def format_report(products, focus=None, budget=None):
    lines = [f"products: {len(products)}", f"stock value: {total_value(products):.2f}"]
    if focus:
        lines.append(f"focus: {find_product(products, focus)['name']}")
    lines.append("low stock: " + (", ".join(low_stock(products)) or "none"))
    if budget is not None:
        for sku, units in restock_plan(products, budget):
            lines.append(f"restock {sku}: {units}")
    return "\n".join(lines)


def main(argv):
    products = load_products(argv[0])
    focus = argv[1] if len(argv) > 1 else None
    budget = float(argv[2]) if len(argv) > 2 else None
    print(format_report(products, focus, budget))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

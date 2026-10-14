"""invkit - inventory reports (PY-M03 guided lab reference package)."""
from invkit.loader import load_products
from invkit.models import Product
from invkit.report import format_report
from invkit.stock import find_product, low_stock, restock_plan, total_value

__version__ = "0.1.0"
__all__ = ["Product", "__version__", "find_product", "format_report", "load_products", "low_stock", "restock_plan", "total_value"]

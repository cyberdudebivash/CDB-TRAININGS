from pathlib import Path

from tinycsv.summary import summarise

SAMPLE = Path(__file__).resolve().parents[1] / "sample" / "people.csv"


def test_summary_counts_rows_and_finds_numeric_columns():
    info = summarise(SAMPLE)
    assert info["rows"] == 3
    assert info["columns"] == ["name", "age", "city"]
    assert info["numeric_columns"] == ["age"]

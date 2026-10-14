"""Design-system guarantees: WCAG contrast of every token pair in light and dark themes, and no CSS drift from the tokens."""
import check_contrast


def test_all_token_pairs_meet_their_contrast_minimum():
    rows, problems = check_contrast.check()
    assert problems == [], problems
    assert len(rows) == 24


def test_contrast_function_is_correct_on_known_values():
    assert round(check_contrast.contrast("#000000", "#ffffff"), 2) == 21.0
    assert round(check_contrast.contrast("#777777", "#ffffff"), 2) == 4.48   # the classic just-failing grey

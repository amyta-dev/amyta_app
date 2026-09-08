from tax_review.services.periods import parse_review_period


def test_review_period_labels():
    period = parse_review_period("FY2024", "PTD2026")
    assert period.years == [2024, 2025, 2026]
    assert period.labels == ["FY2024", "FY2025", "PTD2026"]

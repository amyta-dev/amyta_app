from tax_review.services.excel_input import FinancialRow, KeywordRule
from tax_review.services.mapping import map_financial_rows


def test_longest_keyword_wins_per_object():
    rows = [FinancialRow(1, "Bonus - Salaries", -100.0, 2)]
    rules = [
        KeywordRule("Salaries", -1, {"pph23": False, "pph4_2": False, "pph21": True, "ppn": False, "koreksi_pph_badan": False}, 2),
        KeywordRule("Bonus - Salaries", -1, {"pph23": False, "pph4_2": False, "pph21": True, "ppn": False, "koreksi_pph_badan": False}, 3),
    ]
    mapped, totals = map_financial_rows(rows, rules)
    assert mapped[0].values["pph21"] == 100.0
    assert totals["pph21"] == 100.0
    assert mapped[0].matched_keywords["pph21"] == "Bonus - Salaries"

from dataclasses import dataclass

from .constants import OBJECT_KEYS


@dataclass
class MappedFinancialRow:
    account_name: object
    description: str
    amount: float
    source_row: int
    values: dict
    matched_keywords: dict


def _best_rule(description, rules, object_key):
    """One object may only receive one amount per source row.

    The sample contains overlaps such as 'Salaries' and 'Bonus - Salaries'.
    Selecting the longest matching keyword reproduces the sample behaviour and
    avoids double counting while still allowing one row to feed different tax objects.
    """
    desc = (description or "").casefold()
    candidates = [
        rule for rule in rules
        if rule.flags.get(object_key) and rule.keyword.casefold() in desc
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda rule: (len(rule.keyword), -rule.source_row))


def map_financial_rows(financial_rows, rules):
    mapped = []
    totals = {key: 0.0 for key in OBJECT_KEYS}
    for row in financial_rows:
        values = {}
        matched = {}
        for object_key in OBJECT_KEYS:
            rule = _best_rule(row.description, rules, object_key)
            if rule is None:
                values[object_key] = None
                matched[object_key] = None
                continue
            value = row.amount * rule.sign
            values[object_key] = value
            matched[object_key] = rule.keyword
            totals[object_key] += value
        mapped.append(MappedFinancialRow(
            row.account_name, row.description, row.amount, row.source_row, values, matched,
        ))
    return mapped, totals

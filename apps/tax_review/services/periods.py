import re
from dataclasses import dataclass

from .exceptions import TaxReviewError


@dataclass(frozen=True)
class ReviewPeriod:
    start_year: int
    end_year: int

    @property
    def years(self):
        return list(range(self.start_year, self.end_year + 1))

    @property
    def labels(self):
        years = self.years
        if len(years) == 1:
            return [f"PTD{years[0]}"]
        return [f"FY{year}" for year in years[:-1]] + [f"PTD{years[-1]}"]

    def label_for_year(self, year: int) -> str:
        return f"PTD{year}" if year == self.end_year else f"FY{year}"


def _extract_year(value, field_name):
    match = re.search(r"(20\d{2})", str(value or ""))
    if not match:
        raise TaxReviewError(f"{field_name} harus mengandung tahun 4 digit, contoh FY2024 / PTD2026.")
    return int(match.group(1))


def parse_review_period(periode_fy, periode_ptd):
    start = _extract_year(periode_fy, "Periode FY")
    end = _extract_year(periode_ptd, "Periode PTD")
    if end < start:
        raise TaxReviewError("Periode PTD tidak boleh lebih awal daripada periode FY.")
    if end - start > 10:
        raise TaxReviewError("Rentang review maksimal 10 tahun.")
    return ReviewPeriod(start, end)

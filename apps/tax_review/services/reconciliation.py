from dataclasses import dataclass


@dataclass(frozen=True)
class TaxParameters:
    wht23: float
    wht4_2: float
    wht21: float
    ppn: float
    interest_monthly: float
    interest_months: int
    ppn_admin: float

    @property
    def interest_total(self):
        return self.interest_monthly * self.interest_months


def period_reconciliation(period, mapped_totals_by_year, spt, params):
    output = {"wht23": {}, "wht4_2": {}, "wht21": {}, "ppn": {}}
    for year in period.years:
        obj = mapped_totals_by_year.get(year, {})
        p23 = float(obj.get("pph23", 0) or 0)
        p42 = float(obj.get("pph4_2", 0) or 0)
        p21 = float(obj.get("pph21", 0) or 0)
        ppn_obj = float(obj.get("ppn", 0) or 0)

        due23 = p23 * params.wht23 / 100
        paid23 = float(spt["wht23"].get(year, 0) or 0)
        short23 = max(due23 - paid23, 0)
        int23 = short23 * params.interest_total / 100
        output["wht23"][year] = [p23, due23, paid23, short23, int23, short23 + int23]

        due42 = p42 * params.wht4_2 / 100
        paid42 = float(spt["wht4_2"].get(year, 0) or 0)
        short42 = max(due42 - paid42, 0)
        int42 = short42 * params.interest_total / 100
        output["wht4_2"][year] = [p42, due42, paid42, short42, int42, short42 + int42]

        due21 = p21 * params.wht21 / 100
        paid21 = float(spt["wht21"].get(year, 0) or 0)
        short21 = max(due21 - paid21, 0)
        int21 = short21 * params.interest_total / 100
        output["wht21"][year] = [p21, due21, paid21, short21, int21, short21 + int21]

        spt_ppn = float(spt["ppn_object"].get(year, 0) or 0)
        diff = ppn_obj - spt_ppn
        due_ppn = max(diff * params.ppn / 100, 0)
        int_ppn = due_ppn * params.interest_total / 100
        admin = max(diff * params.ppn_admin / 100, 0)
        output["ppn"][year] = [ppn_obj, spt_ppn, diff, due_ppn, int_ppn, admin, due_ppn + int_ppn + admin]
    return output

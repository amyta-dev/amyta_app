from decimal import Decimal
import re

from .excel_input import read_financial_workbook, read_keyword_rules
from .mapping import map_financial_rows
from .periods import parse_review_period
from .reconciliation import TaxParameters, period_reconciliation
from .spt.service import parse_all, pph21_spt_by_year, ppn_object_by_year, unifikasi_paid_by_year
from .workbook import build_workbook

FILE_FIELDS = (
    "spt_pph21_2024", "spt_pph21_2025", "spt_ppn_2024", "spt_ppn_2025", "spt_unifikasi",
    "laporan_keuangan", "mapping_keyword",
)


def _num(value):
    return float(value) if isinstance(value, Decimal) else float(value or 0)


def process_tax_review(validated_data):
    data=dict(validated_data)
    files={name:data.pop(name) for name in FILE_FIELDS}
    period=parse_review_period(data["periode_fy"],data["periode_ptd"])
    rules=read_keyword_rules(files["mapping_keyword"])
    financial=read_financial_workbook(files["laporan_keuangan"])
    mapped_by_year={}; totals_by_year={}
    for year in period.years:
        mapped,totals=map_financial_rows(financial.get(year,[]),rules)
        mapped_by_year[year]=mapped; totals_by_year[year]=totals

    parsed_spt=parse_all(files)
    spt_summary={
        "wht23": unifikasi_paid_by_year(parsed_spt["unifikasi"]["rows"], "23"),
        "wht4_2": unifikasi_paid_by_year(parsed_spt["unifikasi"]["rows"], "4 ayat 2"),
        "wht21": pph21_spt_by_year(parsed_spt["pph21_old"]["rows"], parsed_spt["pph21_new"]["rows"]),
        "ppn_object": ppn_object_by_year(parsed_spt["ppn_old"]["rows"], parsed_spt["ppn_new"]["rows"]),
    }
    params=TaxParameters(
        _num(data["tarif_wht23"]), _num(data["tarif_wht4_2"]), _num(data["tarif_wht21"]),
        _num(data["tarif_ppn"]), _num(data["sanksi_bunga_persen"]), int(data["sanksi_bunga_bulan"]),
        _num(data["sanksi_admin_ppn"]),
    )
    recon=period_reconciliation(period,totals_by_year,spt_summary,params)
    buffer=build_workbook(data["nama_pt"],data["singkatan_pt"],period,parsed_spt,mapped_by_year,recon,params)
    safe=re.sub(r"[^A-Za-z0-9_-]+","_",data["singkatan_pt"]).strip("_") or "Review"
    filename=f"Review_Perpajakan_{safe}_FY{period.start_year}_PTD{period.end_year}.xlsx"
    return buffer, filename

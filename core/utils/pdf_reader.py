"""Base PDF extractor. Parser SPT di apps/tax_review/services/spt.py memakai helper ini."""
import pdfplumber


def extract_text_per_page(file_obj):
    """file_obj: file-like object (BytesIO), tidak ditulis ke disk."""
    pages = []
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return pages


def extract_tables_per_page(file_obj):
    tables = []
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            tables.append(page.extract_tables())
    return tables

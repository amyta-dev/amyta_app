"""Business-service layer for the Tax Review app.

Keep Django views/admin thin and put tax-processing logic in this package.
"""

from .processor import process_tax_review

__all__ = ["process_tax_review"]

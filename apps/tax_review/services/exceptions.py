class TaxReviewError(Exception):
    """Base domain error suitable for displaying to an operational user."""


class InputWorkbookError(TaxReviewError):
    pass


class SPTParseError(TaxReviewError):
    pass

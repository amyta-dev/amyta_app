from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..exceptions import UnsupportedFormatError
from ..models import ParsedStatement
from ..pdf_utils import PdfDocumentData


class BaseStatementParser(ABC):
    code: str
    name: str
    markers: tuple[str, ...] = ()

    def validate_format(self, document: PdfDocumentData) -> None:
        normalized = document.text.upper()
        if not all(marker.upper() in normalized for marker in self.markers):
            raise UnsupportedFormatError(
                f"Layout PDF tidak cocok dengan template {self.name} yang dipilih."
            )

    @abstractmethod
    def parse(self, document: PdfDocumentData, **options: Any) -> ParsedStatement:
        raise NotImplementedError

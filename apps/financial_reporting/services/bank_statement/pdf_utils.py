from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .exceptions import InvalidPdfError, PasswordProtectedPdfError

try:  # PyMuPDF's modern import name
    import pymupdf
except ImportError:  # pragma: no cover - compatibility with older wheels
    import fitz as pymupdf  # type: ignore

_AMOUNT_RE = re.compile(r"^-?\d+(?:,\d{3})*(?:\.\d{2})$")


@dataclass(frozen=True, slots=True)
class Word:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    block: int
    line: int
    number: int

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2


@dataclass(slots=True)
class PdfPageData:
    number: int
    width: float
    height: float
    words: list[Word]
    text: str


@dataclass(slots=True)
class PdfDocumentData:
    pages: list[PdfPageData]
    text: str


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    return value.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")


def load_pdf(pdf_bytes: bytes, max_pages: int = 100) -> PdfDocumentData:
    if not pdf_bytes.startswith(b"%PDF-"):
        raise InvalidPdfError("File yang diunggah tidak memiliki signature PDF yang valid.")

    try:
        document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # pragma: no cover - library-specific errors
        raise InvalidPdfError("PDF tidak dapat dibuka atau file rusak.") from exc

    try:
        if document.needs_pass:
            raise PasswordProtectedPdfError(
                "PDF dilindungi password. Hapus password PDF terlebih dahulu."
            )
        if document.page_count < 1:
            raise InvalidPdfError("PDF tidak memiliki halaman.")
        if document.page_count > max_pages:
            raise InvalidPdfError(
                f"PDF melebihi batas {max_pages} halaman. Pisahkan file lalu coba kembali."
            )

        pages: list[PdfPageData] = []
        all_text: list[str] = []
        word_count = 0

        for page_index in range(document.page_count):
            page = document[page_index]
            raw_words = page.get_text("words", sort=True)
            words = [
                Word(
                    float(item[0]),
                    float(item[1]),
                    float(item[2]),
                    float(item[3]),
                    normalize_text(str(item[4])).strip(),
                    int(item[5]),
                    int(item[6]),
                    int(item[7]),
                )
                for item in raw_words
                if normalize_text(str(item[4])).strip()
            ]
            page_text = normalize_text(page.get_text("text", sort=True))
            word_count += len(words)
            all_text.append(page_text)
            pages.append(
                PdfPageData(
                    number=page_index + 1,
                    width=float(page.rect.width),
                    height=float(page.rect.height),
                    words=words,
                    text=page_text,
                )
            )

        if word_count < 10:
            raise InvalidPdfError(
                "PDF tidak memiliki text layer yang cukup. Versi ini belum menjalankan OCR; "
                "gunakan e-statement PDF asli, bukan hasil scan/foto."
            )

        return PdfDocumentData(pages=pages, text="\n".join(all_text))
    finally:
        document.close()


def parse_amount(text: str) -> Decimal | None:
    cleaned = normalize_text(text).strip().replace(" ", "")
    if not _AMOUNT_RE.fullmatch(cleaned):
        return None
    try:
        return Decimal(cleaned.replace(",", ""))
    except InvalidOperation:
        return None


def words_in_region(
    words: list[Word],
    *,
    width: float,
    left: float,
    right: float,
    top: float,
    bottom: float,
) -> list[Word]:
    """Select words by normalized horizontal center and absolute vertical bounds."""
    left_x = left * width
    right_x = right * width
    return sorted(
        [
            word
            for word in words
            if left_x <= word.cx < right_x and top <= word.y0 < bottom
        ],
        key=lambda word: (word.y0, word.x0),
    )


def line_texts(words: list[Word], y_tolerance: float = 2.5) -> list[str]:
    if not words:
        return []

    grouped: list[tuple[float, list[Word]]] = []
    for word in sorted(words, key=lambda item: (item.y0, item.x0)):
        if not grouped or abs(grouped[-1][0] - word.y0) > y_tolerance:
            grouped.append((word.y0, [word]))
        else:
            grouped[-1][1].append(word)

    lines: list[str] = []
    for _, line_words in grouped:
        line_words.sort(key=lambda item: item.x0)
        text = " ".join(word.text for word in line_words)
        text = re.sub(r"\s+", " ", text).strip()
        if text and text != "-":
            lines.append(text)
    return lines


def description_in_region(
    words: list[Word],
    *,
    width: float,
    left: float,
    right: float,
    top: float,
    bottom: float,
) -> str:
    selected = words_in_region(
        words, width=width, left=left, right=right, top=top, bottom=bottom
    )
    return "\n".join(line_texts(selected)).strip()


def amounts_in_region(
    words: list[Word],
    *,
    width: float,
    left: float,
    right: float,
    top: float,
    bottom: float,
) -> list[tuple[Word, Decimal]]:
    selected = words_in_region(
        words, width=width, left=left, right=right, top=top, bottom=bottom
    )
    result: list[tuple[Word, Decimal]] = []
    for word in selected:
        parsed = parse_amount(word.text)
        if parsed is not None:
            result.append((word, parsed))
    return result


def first_regex_group(pattern: str, text: str, flags: int = re.IGNORECASE | re.DOTALL) -> str | None:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else None

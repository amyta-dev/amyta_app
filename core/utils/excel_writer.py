"""Base openpyxl helper dipakai lintas fitur untuk generate sheet rekap/rekon."""
import io
from openpyxl import Workbook


class ExcelWorkbookBuilder:
    def __init__(self):
        self.wb = Workbook()
        self.wb.remove(self.wb.active)  # buang default sheet kosong

    def add_sheet(self, name, headers, rows):
        ws = self.wb.create_sheet(title=name[:31])  # excel limit 31 char
        ws.append(headers)
        for row in rows:
            ws.append(row)
        return ws

    def to_buffer(self) -> io.BytesIO:
        buffer = io.BytesIO()
        self.wb.save(buffer)
        buffer.seek(0)
        return buffer

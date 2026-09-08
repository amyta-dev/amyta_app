import io
from django.http import FileResponse


class StatelessFileResponseMixin:
    """
    Helper untuk return file (excel/pdf) langsung dari memory tanpa
    disimpan ke disk — dipakai di report_export dan sejenisnya.
    """

    def build_file_response(self, buffer: io.BytesIO, filename: str, content_type: str):
        buffer.seek(0)
        response = FileResponse(buffer, as_attachment=True, filename=filename)
        response["Content-Type"] = content_type
        return response

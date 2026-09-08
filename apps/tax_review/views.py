from django.http import FileResponse
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .serializers import TaxReviewProcessSerializer
from .services.constants import MIME_XLSX
from .services.exceptions import TaxReviewError
from .services.processor import process_tax_review


class ProcessTaxReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TaxReviewProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            buffer, filename = process_tax_review(serializer.validated_data)
        except TaxReviewError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return FileResponse(buffer, as_attachment=True, filename=filename, content_type=MIME_XLSX)

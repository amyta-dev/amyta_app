from io import BytesIO

from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import DepreciationGenerateSerializer
from .services import build_report_bytes, safe_report_filename


def generate_report_response(uploaded, client_name: str = "", year: int | None = None) -> FileResponse:
    """Stateless file pipeline shared by Jazzmin UI and REST API."""
    input_bytes = uploaded.read()
    output_io, metadata = build_report_bytes(BytesIO(input_bytes), client_name=client_name or None, year=year)
    filename = safe_report_filename(metadata.client_name, metadata.year)
    response = FileResponse(
        output_io,
        as_attachment=True,
        filename=filename,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["X-Row-Count"] = str(metadata.row_count)
    return response


class DepreciationGenerateView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request=DepreciationGenerateSerializer,
        responses={
            200: OpenApiResponse(response=OpenApiTypes.BINARY, description="Generated Excel report"),
            400: OpenApiResponse(description="Validation or generation error"),
        },
        description="Generate depreciation schedule in-memory; uploaded files are not persisted.",
    )
    def post(self, request, *args, **kwargs):
        serializer = DepreciationGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            return generate_report_response(
                uploaded=serializer.validated_data["excel_file"],
                client_name=serializer.validated_data.get("client_name", "").strip(),
                year=serializer.validated_data.get("year"),
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

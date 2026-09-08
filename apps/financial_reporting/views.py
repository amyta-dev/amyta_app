from io import BytesIO

from django.http import FileResponse

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    BankStatementConvertSerializer,
    DepreciationGenerateSerializer,
    FinancialReportGenerateSerializer,
)

from .services.generator import (
    FinancialReportService,
    ProcessingValidationError,
)

from .services.depreciation import (
    build_report_bytes,
    safe_report_filename,
)

from .services.bank_statement_service import (
    convert_bank_statement,
)

from .services.bank_statement.exceptions import (
    StatementParserError,
)


XLSX_MIME = (
    "application/vnd.openxmlformats-officedocument."
    "spreadsheetml.sheet"
)

ZIP_MIME = "application/zip"


def generate_financial_report_response(validated_data) -> FileResponse:
    uploads = {
        key: validated_data[key]
        for key in (
            "cash_flow_master",
            "coa_master",
            "beginning_trial_balance",
            "journal_voucher",
            "beginning_ar",
            "beginning_ap",
            "beginning_advance",
            "beginning_cash_flow",
        )
    }

    archive_bytes, filename, metadata = FinancialReportService().generate(
        client_name=validated_data["client_name"],
        period_start=validated_data["period_start"],
        period_end=validated_data["period_end"],
        uploads=uploads,
        ar_account_codes=validated_data.get(
            "ar_account_codes",
            "",
        ),
        ap_account_codes=validated_data.get(
            "ap_account_codes",
            "",
        ),
        advance_account_codes=validated_data.get(
            "advance_account_codes",
            "",
        ),
        strict_validation=validated_data.get(
            "strict_validation",
            True,
        ),
    )

    response = FileResponse(
        BytesIO(archive_bytes),
        as_attachment=True,
        filename=filename,
        content_type=ZIP_MIME,
    )

    response["X-Journal-Rows"] = str(
        metadata["journal_rows_used"]
    )

    response["X-Validation-Errors"] = str(
        metadata["issue_counts"].get(
            "ERROR",
            0,
        )
    )

    response["Cache-Control"] = "no-store"

    return response


def generate_depreciation_response(validated_data) -> FileResponse:
    uploaded = validated_data["excel_file"]

    input_bytes = uploaded.read()

    output_io, metadata = build_report_bytes(
        BytesIO(input_bytes),
        client_name=(
            validated_data.get("client_name")
            or ""
        ).strip()
        or None,
        year=validated_data.get("year"),
    )

    filename = safe_report_filename(
        metadata.client_name,
        metadata.year,
    )

    output_io.seek(0)

    response = FileResponse(
        output_io,
        as_attachment=True,
        filename=filename,
        content_type=XLSX_MIME,
    )

    response["X-Row-Count"] = str(
        metadata.row_count
    )

    response["Cache-Control"] = "no-store"

    return response


def generate_bank_statement_response(
    validated_data,
) -> FileResponse:

    result = convert_bank_statement(
        bank_code=validated_data["bank"],
        uploaded_file=validated_data["pdf_file"],
    )

    result.stream.seek(0)

    response = FileResponse(
        result.stream,
        as_attachment=True,
        filename=result.filename,
        content_type=XLSX_MIME,
    )

    response["X-Bank"] = result.bank_name

    response["X-Transaction-Count"] = str(
        result.transaction_count
    )

    response["X-Parser-Warnings"] = str(
        len(result.warnings)
    )

    response["Cache-Control"] = "no-store"

    return response


class FinancialReportGenerateView(APIView):
    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    @extend_schema(
        request=FinancialReportGenerateSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description=(
                    "ZIP containing seven generated "
                    "financial reports"
                ),
            ),
            400: OpenApiResponse(
                description=(
                    "Input or processing validation error"
                ),
            ),
            422: OpenApiResponse(
                description=(
                    "Strict accounting validation error"
                ),
            ),
        },
        description=(
            "Generate seven accounting reports "
            "from eight Excel inputs."
        ),
    )
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        serializer = FinancialReportGenerateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:
            return generate_financial_report_response(
                serializer.validated_data
            )

        except ProcessingValidationError as exc:
            return Response(
                {
                    "detail": (
                        "Strict validation "
                        "menghentikan proses."
                    ),
                    "issues": [
                        {
                            "severity": issue.severity,
                            "category": issue.category,
                            "reference": issue.reference,
                            "message": issue.message,
                        }
                        for issue in exc.issues
                    ],
                },
                status=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
            )

        except (ValueError, OSError) as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class DepreciationGenerateView(APIView):
    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    @extend_schema(
        request=DepreciationGenerateSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description=(
                    "Generated depreciation schedule Excel"
                ),
            ),
            400: OpenApiResponse(
                description=(
                    "Validation or generation error"
                ),
            ),
        },
        description=(
            "Generate depreciation schedule "
            "from an asset register Excel file."
        ),
    )
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        serializer = DepreciationGenerateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:
            return generate_depreciation_response(
                serializer.validated_data
            )

        except (ValueError, OSError) as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class BankStatementConvertView(APIView):
    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    @extend_schema(
        request=BankStatementConvertSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description=(
                    "Normalized bank statement Excel"
                ),
            ),
            400: OpenApiResponse(
                description=(
                    "Invalid bank statement "
                    "or unsupported layout"
                ),
            ),
        },
        description=(
            "Convert supported bank statement PDF "
            "(BCA, BNI, BOC, CIMB, Mandiri) "
            "to normalized Excel."
        ),
    )
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        serializer = BankStatementConvertSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:
            return generate_bank_statement_response(
                serializer.validated_data
            )

        except (
            StatementParserError,
            ValueError,
        ) as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
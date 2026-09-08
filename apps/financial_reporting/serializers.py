from rest_framework import serializers

from .services.engine.constants import FILE_FIELDS


class FinancialReportGenerateSerializer(serializers.Serializer):
    client_name = serializers.CharField(max_length=180)
    period_start = serializers.DateField()
    period_end = serializers.DateField()

    cash_flow_master = serializers.FileField()
    coa_master = serializers.FileField()
    beginning_trial_balance = serializers.FileField()
    journal_voucher = serializers.FileField()
    beginning_ar = serializers.FileField()
    beginning_ap = serializers.FileField()
    beginning_advance = serializers.FileField()
    beginning_cash_flow = serializers.FileField()

    ar_account_codes = serializers.CharField(required=False, allow_blank=True, default="")
    ap_account_codes = serializers.CharField(required=False, allow_blank=True, default="")
    advance_account_codes = serializers.CharField(required=False, allow_blank=True, default="")
    strict_validation = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        if attrs["period_start"] > attrs["period_end"]:
            raise serializers.ValidationError({"period_end": "Periode akhir harus sama atau setelah periode awal."})
        for key, label in FILE_FIELDS.items():
            uploaded = attrs.get(key)
            if uploaded and not uploaded.name.lower().endswith(".xlsx"):
                raise serializers.ValidationError({key: f"{label} harus berekstensi .xlsx."})
        return attrs


class BankStatementConvertSerializer(serializers.Serializer):
    BANK_CHOICES = ("bca", "bni", "boc", "cimb", "mandiri")

    bank = serializers.ChoiceField(choices=BANK_CHOICES)
    pdf_file = serializers.FileField()

    def validate_pdf_file(self, value):
        if not value.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("File harus menggunakan ekstensi .pdf.")
        return value


class DepreciationGenerateSerializer(serializers.Serializer):
    excel_file = serializers.FileField()
    client_name = serializers.CharField(required=False, allow_blank=True, max_length=255, default="")
    year = serializers.IntegerField(required=False, min_value=1900, max_value=2100, allow_null=True, default=None)

    def validate_excel_file(self, value):
        if not value.name.lower().endswith(".xlsx"):
            raise serializers.ValidationError("File harus berekstensi .xlsx.")
        return value

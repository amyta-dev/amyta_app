from rest_framework import serializers


class DepreciationGenerateSerializer(serializers.Serializer):
    excel_file = serializers.FileField()
    client_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    year = serializers.IntegerField(required=False, min_value=1900, max_value=2100)

    def validate_excel_file(self, value):
        name = value.name.lower()
        if not name.endswith(".xlsx"):
            raise serializers.ValidationError("Only .xlsx files are supported.")
        return value

from rest_framework import serializers


class TaxReviewProcessSerializer(serializers.Serializer):
    nama_pt = serializers.CharField(max_length=255)
    singkatan_pt = serializers.CharField(max_length=20)
    periode_fy = serializers.CharField(max_length=10)
    periode_ptd = serializers.CharField(max_length=10)
    tarif_wht23 = serializers.DecimalField(max_digits=7, decimal_places=3)
    tarif_wht4_2 = serializers.DecimalField(max_digits=7, decimal_places=3)
    tarif_wht21 = serializers.DecimalField(max_digits=7, decimal_places=3)
    tarif_ppn = serializers.DecimalField(max_digits=7, decimal_places=3)
    sanksi_bunga_persen = serializers.DecimalField(max_digits=7, decimal_places=3)
    sanksi_bunga_bulan = serializers.IntegerField(min_value=0, max_value=120)
    sanksi_admin_ppn = serializers.DecimalField(max_digits=7, decimal_places=3)
    spt_pph21_2024 = serializers.FileField()
    spt_pph21_2025 = serializers.FileField()
    spt_ppn_2024 = serializers.FileField()
    spt_ppn_2025 = serializers.FileField()
    spt_unifikasi = serializers.FileField()
    laporan_keuangan = serializers.FileField()
    mapping_keyword = serializers.FileField()

    PDF_FIELDS = ("spt_pph21_2024", "spt_pph21_2025", "spt_ppn_2024", "spt_ppn_2025", "spt_unifikasi")
    EXCEL_FIELDS = ("laporan_keuangan", "mapping_keyword")

    def validate(self, attrs):
        for name in self.PDF_FIELDS:
            f = attrs.get(name)
            if f and not f.name.lower().endswith(".pdf"):
                raise serializers.ValidationError({name: "File harus PDF."})
        for name in self.EXCEL_FIELDS:
            f = attrs.get(name)
            if f and not f.name.lower().endswith((".xlsx", ".xlsm")):
                raise serializers.ValidationError({name: "File harus XLSX/XLSM."})
        return attrs

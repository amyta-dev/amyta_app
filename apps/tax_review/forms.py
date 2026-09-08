from django import forms


class TaxReviewForm(forms.Form):
    nama_pt = forms.CharField(label="Nama PT", max_length=255, initial="Readymix Concrete Indonesia")
    singkatan_pt = forms.CharField(label="Singkatan PT", max_length=20, initial="RCI")
    periode_fy = forms.CharField(label="Periode Awal (FY)", max_length=10, initial="FY2024", help_text="Contoh: FY2024")
    periode_ptd = forms.CharField(label="Periode Akhir (PTD)", max_length=10, initial="PTD2026", help_text="Contoh: PTD2026")

    tarif_wht23 = forms.DecimalField(label="Tarif WHT 23 (%)", max_digits=7, decimal_places=3, initial=2)
    tarif_wht4_2 = forms.DecimalField(label="Tarif WHT 4(2) (%)", max_digits=7, decimal_places=3, initial=10)
    tarif_wht21 = forms.DecimalField(label="Tarif WHT 21 (%)", max_digits=7, decimal_places=3, initial=9)
    tarif_ppn = forms.DecimalField(label="Tarif PPN (%)", max_digits=7, decimal_places=3, initial=11)
    sanksi_bunga_persen = forms.DecimalField(label="Sanksi Bunga per Bulan (%)", max_digits=7, decimal_places=3, initial=1.83)
    sanksi_bunga_bulan = forms.IntegerField(label="Jumlah Bulan Sanksi Bunga", min_value=0, max_value=120, initial=24)
    sanksi_admin_ppn = forms.DecimalField(label="Sanksi Administrasi PPN (%)", max_digits=7, decimal_places=3, initial=1)

    spt_pph21_2024 = forms.FileField(label="SPT PPh 21 - Tahun 2024 dan Sebelumnya")
    spt_pph21_2025 = forms.FileField(label="SPT PPh 21 - Tahun 2025 ke Atas")
    spt_ppn_2024 = forms.FileField(label="SPT PPN - Tahun 2024 dan Sebelumnya")
    spt_ppn_2025 = forms.FileField(label="SPT PPN - Tahun 2025 ke Atas")
    spt_unifikasi = forms.FileField(label="SPT PPh Unifikasi")
    laporan_keuangan = forms.FileField(label="Data Laporan Keuangan")
    mapping_keyword = forms.FileField(label="Mapping Keyword")

    PDF_FIELDS = ("spt_pph21_2024", "spt_pph21_2025", "spt_ppn_2024", "spt_ppn_2025", "spt_unifikasi")
    EXCEL_FIELDS = ("laporan_keuangan", "mapping_keyword")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control-file" if isinstance(field.widget, forms.FileInput) else "form-control"
            if name in self.PDF_FIELDS:
                field.widget.attrs["accept"] = "application/pdf,.pdf"
            elif name in self.EXCEL_FIELDS:
                field.widget.attrs["accept"] = ".xlsx,.xlsm"

    def clean(self):
        cleaned = super().clean()
        for name in self.PDF_FIELDS:
            f = cleaned.get(name)
            if f and not f.name.lower().endswith(".pdf"):
                self.add_error(name, "File harus PDF.")
        for name in self.EXCEL_FIELDS:
            f = cleaned.get(name)
            if f and not f.name.lower().endswith((".xlsx", ".xlsm")):
                self.add_error(name, "File harus XLSX/XLSM.")
        return cleaned

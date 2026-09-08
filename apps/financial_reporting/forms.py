from django import forms

from .services.engine.constants import FILE_FIELDS


class FinancialReportGenerateForm(forms.Form):
    client_name = forms.CharField(label="Nama Klien", max_length=180)
    period_start = forms.DateField(
        label="Periode Awal",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    period_end = forms.DateField(
        label="Periode Akhir",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    cash_flow_master = forms.FileField(label=FILE_FIELDS["cash_flow_master"])
    coa_master = forms.FileField(label=FILE_FIELDS["coa_master"])
    beginning_trial_balance = forms.FileField(label=FILE_FIELDS["beginning_trial_balance"])
    journal_voucher = forms.FileField(label=FILE_FIELDS["journal_voucher"])
    beginning_ar = forms.FileField(label=FILE_FIELDS["beginning_ar"])
    beginning_ap = forms.FileField(label=FILE_FIELDS["beginning_ap"])
    beginning_advance = forms.FileField(label=FILE_FIELDS["beginning_advance"])
    beginning_cash_flow = forms.FileField(label=FILE_FIELDS["beginning_cash_flow"])

    ar_account_codes = forms.CharField(
        label="Override Account Code AR",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Contoh: 112001, 112002"}),
        help_text="Opsional. Pisahkan beberapa account code dengan koma, titik koma, atau baris baru.",
    )
    ap_account_codes = forms.CharField(
        label="Override Account Code AP",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Contoh: 211001, 211002"}),
        help_text="Opsional.",
    )
    advance_account_codes = forms.CharField(
        label="Override Account Code Advance Payment",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Contoh: 114001"}),
        help_text="Opsional.",
    )
    strict_validation = forms.BooleanField(
        label="Strict validation",
        required=False,
        initial=True,
        help_text="Jika aktif, proses dihentikan bila ditemukan error validasi material.",
    )

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("period_start")
        end = cleaned.get("period_end")
        if start and end and start > end:
            raise forms.ValidationError("Periode awal tidak boleh melewati periode akhir.")
        return cleaned

    def _validate_xlsx(self, field_name):
        uploaded = self.cleaned_data.get(field_name)
        if uploaded and not uploaded.name.lower().endswith(".xlsx"):
            self.add_error(field_name, "File harus berekstensi .xlsx.")
        return uploaded

    def clean_cash_flow_master(self):
        return self._validate_xlsx("cash_flow_master")

    def clean_coa_master(self):
        return self._validate_xlsx("coa_master")

    def clean_beginning_trial_balance(self):
        return self._validate_xlsx("beginning_trial_balance")

    def clean_journal_voucher(self):
        return self._validate_xlsx("journal_voucher")

    def clean_beginning_ar(self):
        return self._validate_xlsx("beginning_ar")

    def clean_beginning_ap(self):
        return self._validate_xlsx("beginning_ap")

    def clean_beginning_advance(self):
        return self._validate_xlsx("beginning_advance")

    def clean_beginning_cash_flow(self):
        return self._validate_xlsx("beginning_cash_flow")


class BankStatementParseForm(forms.Form):
    BANK_CHOICES = (
        ("bca", "Bank Central Asia (BCA)"),
        ("bni", "Bank Negara Indonesia (BNI)"),
        ("boc", "Bank of China (BOC)"),
        ("cimb", "Bank CIMB Niaga"),
        ("mandiri", "Bank Mandiri"),
    )

    bank = forms.ChoiceField(label="Bank", choices=BANK_CHOICES)
    pdf_file = forms.FileField(
        label="Bank Statement PDF",
        help_text="Gunakan e-statement PDF asli yang memiliki text layer, bukan scan/foto.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["bank"].widget.attrs.update({"class": "form-control"})
        self.fields["pdf_file"].widget.attrs.update({"class": "form-control-file", "accept": ".pdf,application/pdf"})

    def clean_pdf_file(self):
        uploaded = self.cleaned_data["pdf_file"]
        if not uploaded.name.lower().endswith(".pdf"):
            raise forms.ValidationError("File harus menggunakan ekstensi .pdf.")
        return uploaded


class DepreciationGenerateForm(forms.Form):
    excel_file = forms.FileField(
        label="Asset Register Excel",
        help_text=(
            "Required columns: No, Description, Account Code, Unit, Purchase Date, "
            "Useful Life (in months), Asset Amount, Depreciation Method."
        ),
    )
    client_name = forms.CharField(
        label="Nama Klien",
        required=False,
        max_length=255,
        help_text="Opsional jika nama klien sudah tersedia di file Excel.",
    )
    year = forms.IntegerField(
        label="Tahun Laporan",
        required=False,
        min_value=1900,
        max_value=2100,
        help_text="Opsional jika tahun sudah tersedia di file Excel.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({"class": "form-control-file", "accept": ".xlsx"})
            else:
                field.widget.attrs.update({"class": "form-control"})

    def clean_excel_file(self):
        uploaded = self.cleaned_data["excel_file"]
        if not uploaded.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("File harus berekstensi .xlsx.")
        return uploaded

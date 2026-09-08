from django import forms


class DepreciationGenerateForm(forms.Form):
    excel_file = forms.FileField(label="Asset Register (.xlsx)")
    client_name = forms.CharField(label="Client Name", required=False, max_length=255)
    year = forms.IntegerField(label="Report Year", required=False, min_value=1900, max_value=2100)

    def clean_excel_file(self):
        uploaded = self.cleaned_data["excel_file"]
        if not uploaded.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Only .xlsx files are supported.")
        return uploaded

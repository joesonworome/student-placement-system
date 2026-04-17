from django import forms
from .models import UploadedDataset


class DatasetUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedDataset
        fields = ["name", "file"]

    def clean_file(self):
        file = self.cleaned_data["file"]
        allowed_extensions = [".csv", ".xlsx", ".xls"]
        filename = file.name.lower()

        if not any(filename.endswith(ext) for ext in allowed_extensions):
            raise forms.ValidationError("Only CSV and Excel files are allowed.")

        return file
from django import forms
from django.conf import settings
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
        
        # Check file size
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 10 * 1024 * 1024)
        if file.size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            raise forms.ValidationError(f"File size must not exceed {max_size_mb:.1f}MB.")

        return file
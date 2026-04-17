from django.contrib import admin
from .models import UploadedDataset


@admin.register(UploadedDataset)
class UploadedDatasetAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "uploaded_by", "uploaded_at", "row_count", "column_count", "is_processed")
    list_filter = ("is_processed", "uploaded_at")
    search_fields = ("name", "uploaded_by__username")
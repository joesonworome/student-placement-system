from django.db import models
from django.contrib.auth.models import User


class UploadedDataset(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="datasets/")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    row_count = models.PositiveIntegerField(default=0)
    column_count = models.PositiveIntegerField(default=0)
    is_processed = models.BooleanField(default=False)
    processed_file = models.FileField(upload_to="processed_datasets/", null=True, blank=True)

    def __str__(self):
        return self.name
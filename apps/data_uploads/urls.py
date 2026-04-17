from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.upload_data, name="upload_data"),
    path("preview/<int:dataset_id>/", views.preview_dataset, name="preview_dataset"),
    path("preprocess/<int:dataset_id>/", views.preprocess_data, name="preprocess_data"),
]
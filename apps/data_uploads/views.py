import os
import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files import File
from django.shortcuts import render, redirect, get_object_or_404
from .forms import DatasetUploadForm
from .models import UploadedDataset


def read_dataset(file_path):
    if file_path.endswith(".csv"):
        return pd.read_csv(file_path)
    elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
        return pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file format")


@login_required
def upload_data(request):
    datasets = UploadedDataset.objects.filter(uploaded_by=request.user).order_by("-uploaded_at")

    if request.method == "POST":
        form = DatasetUploadForm(request.POST, request.FILES)
        if form.is_valid():
            dataset = form.save(commit=False)
            dataset.uploaded_by = request.user
            dataset.save()

            file_path = dataset.file.path
            df = read_dataset(file_path)

            dataset.row_count = df.shape[0]
            dataset.column_count = df.shape[1]
            dataset.save()

            messages.success(request, "Dataset uploaded successfully.")
            return redirect("upload_data")
    else:
        form = DatasetUploadForm()

    context = {
        "form": form,
        "datasets": datasets,
    }
    return render(request, "data_upload/upload_data.html", context)


@login_required
def preview_dataset(request, dataset_id):
    dataset = get_object_or_404(UploadedDataset, id=dataset_id, uploaded_by=request.user)

    df = read_dataset(dataset.file.path)
    preview_html = df.head(20).to_html(classes="table table-bordered table-striped", index=False)

    context = {
        "dataset": dataset,
        "preview_html": preview_html,
        "columns": df.columns.tolist(),
        "shape": df.shape,
        "missing_values": df.isnull().sum().to_dict(),
    }
    return render(request, "data_upload/preview_dataset.html", context)


@login_required
def preprocess_data(request, dataset_id):
    dataset = get_object_or_404(UploadedDataset, id=dataset_id, uploaded_by=request.user)
    df = read_dataset(dataset.file.path)

    before_rows = df.shape[0]
    before_cols = df.shape[1]
    missing_before = int(df.isnull().sum().sum())
    duplicates_before = int(df.duplicated().sum())

    if request.method == "POST":
        handle_missing = request.POST.get("handle_missing")
        remove_duplicates = request.POST.get("remove_duplicates")
        encode_categorical = request.POST.get("encode_categorical")

        # Handle missing values
        if handle_missing == "drop":
            df = df.dropna()
        elif handle_missing == "fill":
            for col in df.columns:
                if df[col].dtype == "object":
                    mode_value = df[col].mode()
                    df[col] = df[col].fillna(mode_value[0] if not mode_value.empty else "Unknown")
                else:
                    df[col] = df[col].fillna(df[col].mean())

        # Remove duplicates
        if remove_duplicates == "yes":
            df = df.drop_duplicates()

        # Encode categorical columns
        encoded_columns = []
        if encode_categorical == "yes":
            for col in df.select_dtypes(include=["object"]).columns:
                df[col] = df[col].astype("category").cat.codes
                encoded_columns.append(col)

        processed_folder = os.path.join(settings.MEDIA_ROOT, "processed_datasets")
        os.makedirs(processed_folder, exist_ok=True)

        processed_filename = f"processed_{dataset.id}.csv"
        processed_path = os.path.join(processed_folder, processed_filename)
        df.to_csv(processed_path, index=False)

        with open(processed_path, "rb") as f:
            dataset.processed_file.save(processed_filename, File(f), save=False)

        dataset.is_processed = True
        dataset.row_count = df.shape[0]
        dataset.column_count = df.shape[1]
        dataset.save()

        messages.success(request, "Dataset preprocessed successfully.")

        context = {
            "dataset": dataset,
            "before_rows": before_rows,
            "before_cols": before_cols,
            "after_rows": df.shape[0],
            "after_cols": df.shape[1],
            "missing_before": missing_before,
            "missing_after": int(df.isnull().sum().sum()),
            "duplicates_before": duplicates_before,
            "duplicates_after": int(df.duplicated().sum()),
            "encoded_columns": encoded_columns,
            "preview_html": df.head(20).to_html(classes="table table-bordered table-striped", index=False),
        }
        return render(request, "data_upload/preprocess_result.html", context)

    context = {
        "dataset": dataset,
        "before_rows": before_rows,
        "before_cols": before_cols,
        "missing_before": missing_before,
        "duplicates_before": duplicates_before,
        "columns": df.columns.tolist(),
    }
    return render(request, "data_upload/preprocess_data.html", context)
import io
import os

import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DatasetUploadForm
from .models import UploadedDataset


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Make column names unique strings so preview/export and templates stay stable."""
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [" | ".join(str(c) for c in tup if str(c) != "nan") for tup in out.columns]
    seen = {}
    new_cols = []
    for c in out.columns:
        base = str(c)
        if base in seen:
            seen[base] += 1
            new_cols.append(f"{base}_{seen[base]}")
        else:
            seen[base] = 0
            new_cols.append(base)
    out.columns = new_cols
    return out


def read_dataset(file_path: str) -> pd.DataFrame:
    """Load CSV or Excel; raises ValueError / UnicodeDecodeError with a clear message on failure."""
    ext = os.path.splitext(str(file_path))[1].lower()

    if ext == ".csv":
        last_err = None
        for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                return _normalize_columns(df)
            except UnicodeDecodeError as exc:
                last_err = exc
                continue
        raise ValueError(
            "Could not decode this CSV (tried UTF-8, UTF-8-sig, CP1252, Latin-1). "
            "Save the file as UTF-8 and try again."
        ) from last_err

    if ext in (".xlsx", ".xlsm"):
        df = pd.read_excel(file_path, engine="openpyxl")
        return _normalize_columns(df)

    if ext == ".xls":
        try:
            df = pd.read_excel(file_path, engine="xlrd")
        except ImportError as exc:
            raise ValueError(
                "Reading .xls requires the 'xlrd' package. Install xlrd or save the file as .xlsx."
            ) from exc
        return _normalize_columns(df)

    raise ValueError(f"Unsupported file type {ext!r}. Use .csv, .xlsx, .xlsm, or .xls.")


def _missing_counts_dict(df: pd.DataFrame) -> dict:
    return {str(k): int(v) for k, v in df.isnull().sum().items()}


def _fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Fill NaNs per column; safe for numeric, boolean, datetime, and text columns."""
    out = df.copy()
    for col in out.columns:
        s = out[col]
        if pd.api.types.is_numeric_dtype(s):
            med = s.median()
            fill_val = 0 if pd.isna(med) else med
            out[col] = s.fillna(fill_val)
        elif pd.api.types.is_bool_dtype(s):
            mode = s.mode()
            out[col] = s.fillna(bool(mode.iloc[0]) if not mode.empty else False)
        elif pd.api.types.is_datetime64_any_dtype(s):
            out[col] = s.ffill().bfill()
        else:
            mode = s.astype("object").mode()
            out[col] = s.fillna(str(mode.iloc[0]) if not mode.empty else "Unknown")
    return out


def _dataframe_to_preview_html(df: pd.DataFrame, max_rows: int = 20) -> str:
    sample = df.head(max_rows)
    return sample.to_html(classes="table table-bordered table-striped", index=False, na_rep="")


@login_required
def upload_data(request):
    datasets = UploadedDataset.objects.filter(uploaded_by=request.user).order_by("-uploaded_at")

    if request.method == "POST":
        form = DatasetUploadForm(request.POST, request.FILES)
        if form.is_valid():
            dataset = form.save(commit=False)
            dataset.uploaded_by = request.user
            dataset.save()

            try:
                file_path = dataset.file.path
                df = read_dataset(file_path)
            except Exception as exc:
                messages.error(request, f"Could not read the uploaded file: {exc}")
                dataset.delete()
                return redirect("upload_data")

            dataset.row_count = int(df.shape[0])
            dataset.column_count = int(df.shape[1])
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

    try:
        file_path = dataset.file.path
        df = read_dataset(file_path)
    except Exception as exc:
        messages.error(request, f"Could not open or read this dataset: {exc}")
        return redirect("upload_data")

    preview_html = _dataframe_to_preview_html(df)

    context = {
        "dataset": dataset,
        "preview_html": preview_html,
        "columns": [str(c) for c in df.columns.tolist()],
        "num_rows": int(df.shape[0]),
        "num_cols": int(df.shape[1]),
        "missing_values": _missing_counts_dict(df),
    }
    return render(request, "data_upload/preview_dataset.html", context)


@login_required
def preprocess_data(request, dataset_id):
    dataset = get_object_or_404(UploadedDataset, id=dataset_id, uploaded_by=request.user)

    try:
        df = read_dataset(dataset.file.path)
    except Exception as exc:
        messages.error(request, f"Could not open or read this dataset: {exc}")
        return redirect("upload_data")

    before_rows = int(df.shape[0])
    before_cols = int(df.shape[1])
    missing_before = int(df.isnull().sum().sum())
    duplicates_before = int(df.duplicated().sum())

    if request.method == "POST":
        handle_missing = request.POST.get("handle_missing")
        remove_duplicates = request.POST.get("remove_duplicates")
        encode_categorical = request.POST.get("encode_categorical")

        if handle_missing == "drop":
            df = df.dropna()
        elif handle_missing == "fill":
            df = _fill_missing_values(df)

        if remove_duplicates == "yes":
            df = df.drop_duplicates()

        encoded_columns = []
        if encode_categorical == "yes":
            for col in df.select_dtypes(include=["object", "string", "category"]).columns:
                df[col] = pd.Categorical(df[col].astype(str)).codes
                encoded_columns.append(str(col))

        processed_filename = f"processed_{dataset.id}.csv"
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        csv_bytes = buf.getvalue().encode("utf-8")

        # Save via ContentFile so we never read/write the same path on disk (fixes Windows file locks).
        dataset.processed_file.save(
            processed_filename,
            ContentFile(csv_bytes),
            save=False,
        )

        dataset.is_processed = True
        dataset.row_count = int(df.shape[0])
        dataset.column_count = int(df.shape[1])
        dataset.save()

        messages.success(request, "Dataset preprocessed successfully.")

        context = {
            "dataset": dataset,
            "before_rows": before_rows,
            "before_cols": before_cols,
            "after_rows": int(df.shape[0]),
            "after_cols": int(df.shape[1]),
            "missing_before": missing_before,
            "missing_after": int(df.isnull().sum().sum()),
            "duplicates_before": duplicates_before,
            "duplicates_after": int(df.duplicated().sum()),
            "encoded_columns": encoded_columns,
            "preview_html": _dataframe_to_preview_html(df),
        }
        return render(request, "data_upload/preprocess_result.html", context)

    context = {
        "dataset": dataset,
        "before_rows": before_rows,
        "before_cols": before_cols,
        "missing_before": missing_before,
        "duplicates_before": duplicates_before,
        "columns": [str(c) for c in df.columns.tolist()],
    }
    return render(request, "data_upload/preprocess_data.html", context)

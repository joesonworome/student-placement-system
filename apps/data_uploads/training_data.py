"""
Resolve the student table used for ML training, dashboard stats, and reports.

Uses the logged-in user's latest upload (processed file if available), then
falls back to legacy MEDIA_ROOT/student_data.csv.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple

import pandas as pd
from django.conf import settings

from .dataset_io import read_dataset
from .models import UploadedDataset


def resolve_placement_status_column(df: pd.DataFrame) -> pd.DataFrame:
    """Rename common target column names to ``placement_status``."""
    df = df.copy()
    for col in list(df.columns):
        key = str(col).strip().lower().replace(" ", "_")
        if key == "placement_status":
            if col != "placement_status":
                df.rename(columns={col: "placement_status"}, inplace=True)
            return df
        if key in ("placed", "is_placed"):
            df.rename(columns={col: "placement_status"}, inplace=True)
            return df
    return df


def coerce_placement_status_for_ml(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure ``placement_status`` is numeric 0/1 for sklearn / XGBoost and dashboard counts."""
    if "placement_status" not in df.columns:
        return df
    df = df.copy()
    s = df["placement_status"]
    if pd.api.types.is_bool_dtype(s):
        df["placement_status"] = s.astype(int)
        return df
    if pd.api.types.is_numeric_dtype(s):
        df["placement_status"] = s.fillna(0).astype(int).clip(0, 1)
        return df
    low = s.astype(str).str.strip().str.lower()
    positive = low.isin(
        ["1", "true", "yes", "y", "placed", "success", "hire", "hired"]
    ) | (low.str.contains("placed", na=False) & ~low.str.contains("not", na=False))
    df["placement_status"] = positive.astype(int)
    return df


def load_user_student_dataframe(user) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Return (dataframe, error_code).

    error_code:
        None on success
        "no_dataset" if nothing to load
        other string: exception message from read_dataset / IO
    """
    latest = UploadedDataset.objects.filter(uploaded_by=user).order_by("-uploaded_at").first()
    if latest:
        try:
            if latest.is_processed and latest.processed_file:
                path = latest.processed_file.path
            else:
                path = latest.file.path
            df = read_dataset(path)
        except Exception as exc:
            return None, str(exc)
    else:
        legacy = os.path.join(settings.MEDIA_ROOT, "student_data.csv")
        if not os.path.isfile(legacy):
            return None, "no_dataset"
        try:
            df = read_dataset(legacy)
        except Exception as exc:
            return None, str(exc)

    df = resolve_placement_status_column(df)
    df = coerce_placement_status_for_ml(df)
    return df, None


def sync_student_data_csv(df: pd.DataFrame) -> None:
    """Write a copy for legacy code paths that still read ``student_data.csv``."""
    path = os.path.join(settings.MEDIA_ROOT, "student_data.csv")
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    df.to_csv(path, index=False)

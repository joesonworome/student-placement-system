"""Read uploaded datasets (CSV / Excel) for previews, preprocessing, and ML."""

import os

import pandas as pd


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

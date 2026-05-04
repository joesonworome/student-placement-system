from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import logging

import pandas as pd

from apps.data_uploads.training_data import load_user_student_dataframe

logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    return render(request, "dashboard/dashboard.html")


@login_required
def get_dashboard_stats(request):
    df, err = load_user_student_dataframe(request.user)
    if err or df is None:
        return JsonResponse({
            "total_students": 0,
            "placed_students": 0,
            "placement_rate": 0,
            "avg_cgpa": 0,
        })

    try:
        total_students = len(df)

        if "placement_status" in df.columns:
            placed_students = int((df["placement_status"] == 1).sum())
            placement_rate = (
                round((placed_students / total_students) * 100, 2) if total_students > 0 else 0
            )
        else:
            placed_students = 0
            placement_rate = 0

        if "cgpa" in df.columns:
            avg_cgpa = round(float(df["cgpa"].mean()), 2)
        else:
            avg_cgpa = 0

    except Exception as e:
        logger.exception("Error building dashboard stats: %s", e)
        total_students = 0
        placed_students = 0
        placement_rate = 0
        avg_cgpa = 0

    return JsonResponse({
        "total_students": total_students,
        "placed_students": placed_students,
        "placement_rate": placement_rate,
        "avg_cgpa": avg_cgpa,
    })


@login_required
def train_model(request):
    return redirect('ml_engine:train_model')


@login_required
def predict(request):
    return redirect('ml_engine:predict')


@login_required
def generate_report(request):
    return redirect('reports:generate_report')
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import pandas as pd
import os
from django.conf import settings


@login_required
def dashboard(request):
    return render(request, "dashboard/dashboard.html")


@login_required
def get_dashboard_stats(request):
    data_file = os.path.join(settings.MEDIA_ROOT, "student_data.csv")

    if os.path.exists(data_file):
        try:
            df = pd.read_csv(data_file)
            total_students = len(df)

            if "placement_status" in df.columns:
                placed_students = len(df[df["placement_status"] == 1])
                placement_rate = round((placed_students / total_students) * 100, 2) if total_students > 0 else 0
            else:
                placed_students = 0
                placement_rate = 0

            if "cgpa" in df.columns:
                avg_cgpa = round(df["cgpa"].mean(), 2)
            else:
                avg_cgpa = 0

        except Exception:
            total_students = 0
            placed_students = 0
            placement_rate = 0
            avg_cgpa = 0
    else:
        total_students = 150
        placed_students = 98
        placement_rate = 65.33
        avg_cgpa = 7.8

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
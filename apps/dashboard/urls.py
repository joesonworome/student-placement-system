from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("api/stats/", views.get_dashboard_stats, name="dashboard_stats"),
    path("train-model/", views.train_model, name="train_model"),
    path("predict/", views.predict, name="predict"),
    path("generate-report/", views.generate_report, name="generate_report"),
]
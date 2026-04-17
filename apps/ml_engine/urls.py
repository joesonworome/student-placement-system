from django.urls import path
from . import views

urlpatterns = [
    path('', views.make_prediction, name='predict'),
    path('train/', views.train_model, name='train_model'),
    path('models/', views.list_models, name='list_models'),
]
import os
import django
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'placement_system.settings')
django.setup()

from django.urls import get_resolver, reverse

resolver = get_resolver()
print('PATTERNS:')
for p in resolver.url_patterns:
    print(p)
print('---')

names = [
    'dashboard',
    'upload_data',
    'ml_engine:train_model',
    'ml_engine:predict',
    'reports:generate_report',
    'login',
    'logout',
    'register',
]
for name in names:
    try:
        print(name, '=>', reverse(name))
    except Exception as e:
        print(name, 'ERROR', e)

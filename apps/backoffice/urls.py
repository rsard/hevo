from django.urls import path

from apps.backoffice.views import (
    customer_create,
    customer_detail,
    customer_list,
    error_log,
    platform_dashboard,
)

app_name = 'backoffice'

urlpatterns = [
    path('', platform_dashboard, name='dashboard'),
    path('erros/', error_log, name='error-log'),
    path('clientes/', customer_list, name='customer-list'),
    path('clientes/novo/', customer_create, name='customer-create'),
    path('clientes/<int:pk>/', customer_detail, name='customer-detail'),
]

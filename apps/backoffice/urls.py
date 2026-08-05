from django.urls import path

from apps.backoffice.views import customer_create, customer_list

app_name = 'backoffice'

urlpatterns = [
    path('clientes/', customer_list, name='customer-list'),
    path('clientes/novo/', customer_create, name='customer-create'),
]

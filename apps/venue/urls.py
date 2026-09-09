from django.urls import path

from apps.venue import views

app_name = 'venue'

urlpatterns = [
    path('', views.profile_edit, name='profile'),
    path('whatsapp/conectar/', views.whatsapp_connect, name='whatsapp-connect'),
    path('whatsapp/desconectar/', views.whatsapp_disconnect, name='whatsapp-disconnect'),
    path('horarios/', views.opening_hours_edit, name='opening-hours'),

    path('tipos-evento/', views.EventTypeListView.as_view(), name='event-type-list'),
    path('tipos-evento/novo/', views.EventTypeCreateView.as_view(), name='event-type-create'),
    path('tipos-evento/<int:pk>/editar/', views.EventTypeUpdateView.as_view(), name='event-type-update'),
    path('tipos-evento/<int:pk>/excluir/', views.EventTypeDeleteView.as_view(), name='event-type-delete'),

    path('pacotes/', views.PackageListView.as_view(), name='package-list'),
    path('pacotes/novo/', views.PackageCreateView.as_view(), name='package-create'),
    path('pacotes/<int:pk>/editar/', views.PackageUpdateView.as_view(), name='package-update'),
    path('pacotes/<int:pk>/excluir/', views.PackageDeleteView.as_view(), name='package-delete'),

    path('cardapios/', views.menu_list, name='menu-list'),
    path('cardapios/novo/', views.menu_edit, name='menu-create'),
    path('cardapios/<int:pk>/editar/', views.menu_edit, name='menu-update'),
    path('cardapios/<int:pk>/excluir/', views.menu_delete, name='menu-delete'),

    path('decoracao/', views.DecorationOptionListView.as_view(), name='decoration-list'),
    path('decoracao/novo/', views.DecorationOptionCreateView.as_view(), name='decoration-create'),
    path('decoracao/<int:pk>/editar/', views.DecorationOptionUpdateView.as_view(), name='decoration-update'),
    path('decoracao/<int:pk>/excluir/', views.DecorationOptionDeleteView.as_view(), name='decoration-delete'),

    path('perguntas-frequentes/', views.FAQListView.as_view(), name='faq-list'),
    path('perguntas-frequentes/novo/', views.FAQCreateView.as_view(), name='faq-create'),
    path('perguntas-frequentes/<int:pk>/editar/', views.FAQUpdateView.as_view(), name='faq-update'),
    path('perguntas-frequentes/<int:pk>/excluir/', views.FAQDeleteView.as_view(), name='faq-delete'),
]

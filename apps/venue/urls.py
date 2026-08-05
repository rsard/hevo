from django.urls import path

from apps.venue import views

app_name = 'venue'

urlpatterns = [
    path('', views.profile_edit, name='profile'),
    path('opening-hours/', views.opening_hours_edit, name='opening-hours'),

    path('event-types/', views.EventTypeListView.as_view(), name='event-type-list'),
    path('event-types/new/', views.EventTypeCreateView.as_view(), name='event-type-create'),
    path('event-types/<int:pk>/edit/', views.EventTypeUpdateView.as_view(), name='event-type-update'),
    path('event-types/<int:pk>/delete/', views.EventTypeDeleteView.as_view(), name='event-type-delete'),

    path('packages/', views.PackageListView.as_view(), name='package-list'),
    path('packages/new/', views.PackageCreateView.as_view(), name='package-create'),
    path('packages/<int:pk>/edit/', views.PackageUpdateView.as_view(), name='package-update'),
    path('packages/<int:pk>/delete/', views.PackageDeleteView.as_view(), name='package-delete'),

    path('menus/', views.menu_list, name='menu-list'),
    path('menus/new/', views.menu_edit, name='menu-create'),
    path('menus/<int:pk>/edit/', views.menu_edit, name='menu-update'),
    path('menus/<int:pk>/delete/', views.menu_delete, name='menu-delete'),

    path('decorations/', views.DecorationOptionListView.as_view(), name='decoration-list'),
    path('decorations/new/', views.DecorationOptionCreateView.as_view(), name='decoration-create'),
    path('decorations/<int:pk>/edit/', views.DecorationOptionUpdateView.as_view(), name='decoration-update'),
    path('decorations/<int:pk>/delete/', views.DecorationOptionDeleteView.as_view(), name='decoration-delete'),

    path('faqs/', views.FAQListView.as_view(), name='faq-list'),
    path('faqs/new/', views.FAQCreateView.as_view(), name='faq-create'),
    path('faqs/<int:pk>/edit/', views.FAQUpdateView.as_view(), name='faq-update'),
    path('faqs/<int:pk>/delete/', views.FAQDeleteView.as_view(), name='faq-delete'),

    path('photos/', views.ImageListView.as_view(), name='image-list'),
    path('photos/new/', views.ImageCreateView.as_view(), name='image-create'),
    path('photos/<int:pk>/edit/', views.ImageUpdateView.as_view(), name='image-update'),
    path('photos/<int:pk>/delete/', views.ImageDeleteView.as_view(), name='image-delete'),

    path('documents/', views.DocumentListView.as_view(), name='document-list'),
    path('documents/new/', views.DocumentCreateView.as_view(), name='document-create'),
    path('documents/<int:pk>/edit/', views.DocumentUpdateView.as_view(), name='document-update'),
    path('documents/<int:pk>/delete/', views.DocumentDeleteView.as_view(), name='document-delete'),
]

"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import include, path

from apps.user.forms import HevoPasswordResetForm, HevoSetPasswordForm, LoginForm

urlpatterns = [
    path('admin/', admin.site.urls),
    path('entrar/', LoginView.as_view(form_class=LoginForm), name='login'),
    path('sair/', LogoutView.as_view(), name='logout'),
    path(
        'senha/resetar/',
        PasswordResetView.as_view(
            form_class=HevoPasswordResetForm,
            email_template_name='registration/password_reset_email.txt',
            html_email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
        ),
        name='password_reset',
    ),
    path(
        'senha/resetar/enviado/',
        PasswordResetDoneView.as_view(),
        name='password_reset_done',
    ),
    path(
        'senha/resetar/confirmar/<uidb64>/<token>/',
        PasswordResetConfirmView.as_view(form_class=HevoSetPasswordForm),
        name='password_reset_confirm',
    ),
    path(
        'senha/resetar/concluido/',
        PasswordResetCompleteView.as_view(),
        name='password_reset_complete',
    ),
    path('conversa/', include('apps.conversation.urls')),
    path('', include('apps.crm.urls')),
    path('base-conhecimento/', include('apps.venue.urls')),
    path('administracao/', include('apps.backoffice.urls')),
    path('', include('apps.dashboard.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

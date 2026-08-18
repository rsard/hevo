from django import forms
from django.contrib.auth import password_validation
from django.utils import timezone
from django.utils.text import slugify

from apps.backoffice.models import Subscription
from apps.user.models import User
from apps.venue.models import Venue


class NewCustomerForm(forms.Form):
    """Form for staff to onboard a new venue, its owner account, and its subscription."""

    venue_name = forms.CharField(label="Nome do espaço", max_length=255)
    venue_whatsapp_number = forms.CharField(label="Número do WhatsApp", max_length=20)

    owner_username = forms.CharField(label="Usuário", max_length=150)
    owner_email = forms.EmailField(label="E-mail")
    owner_password = forms.CharField(label="Senha", widget=forms.PasswordInput)

    plan_name = forms.CharField(label="Plano", max_length=100)
    monthly_price = forms.DecimalField(
        label="Valor mensal (R$)", max_digits=10, decimal_places=2, localize=True,
        widget=forms.TextInput(attrs={'data-currency-mask': ''}),
    )
    status = forms.ChoiceField(
        label="Status", choices=Subscription.Status.choices, initial=Subscription.Status.TRIALING,
    )
    started_at = forms.DateField(
        label="Início da assinatura",
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"autocomplete": "off"}),
    )
    notes = forms.CharField(label="Observações", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field, forms.ChoiceField):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"

    def clean_venue_whatsapp_number(self):
        """Rejects a WhatsApp number already used by another venue."""
        number = self.cleaned_data["venue_whatsapp_number"]
        if Venue.objects.filter(whatsapp_number=number).exists():
            raise forms.ValidationError("Já existe um espaço com este número de WhatsApp.")
        return number

    def clean_owner_username(self):
        """Rejects a username already taken by another user."""
        username = self.cleaned_data["owner_username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nome de usuário já está em uso.")
        return username

    def clean_owner_password(self):
        """Validates the new owner's password against Django's password validators."""
        password = self.cleaned_data["owner_password"]
        password_validation.validate_password(password)
        return password

    def unique_slug(self):
        """Builds a unique venue slug, appending a numeric suffix if the base is taken."""
        base = slugify(self.cleaned_data["venue_name"])
        slug = base
        suffix = 2
        while Venue.objects.filter(slug=slug).exists():
            slug = f"{base}-{suffix}"
            suffix += 1
        return slug

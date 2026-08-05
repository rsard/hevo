from django import forms

from apps.venue.models import (
    DecorationOption,
    Document,
    EventType,
    FAQ,
    Image,
    Menu,
    MenuItem,
    OpeningHours,
    Package,
    Venue,
)


class VenueProfileForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = [
            'name',
            'description',
            'address',
            'whatsapp_number',
            'whatsapp_phone_number_id',
            'timezone',
            'parking_info',
            'payment_policy',
            'cancellation_policy',
        ]
        labels = {
            'name': 'Nome',
            'description': 'Descrição',
            'address': 'Endereço',
            'whatsapp_number': 'Número do WhatsApp',
            'whatsapp_phone_number_id': 'ID do número (WhatsApp Cloud API)',
            'timezone': 'Fuso horário',
            'parking_info': 'Informações de estacionamento',
            'payment_policy': 'Política de pagamento',
            'cancellation_policy': 'Política de cancelamento',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'parking_info': forms.Textarea(attrs={'rows': 2}),
            'payment_policy': forms.Textarea(attrs={'rows': 3}),
            'cancellation_policy': forms.Textarea(attrs={'rows': 3}),
        }


class OpeningHoursForm(forms.ModelForm):
    class Meta:
        model = OpeningHours
        fields = ['is_closed', 'opens_at', 'closes_at']
        labels = {'is_closed': 'Fechado', 'opens_at': 'Abre', 'closes_at': 'Fecha'}
        widgets = {
            'opens_at': forms.TimeInput(attrs={'type': 'time'}),
            'closes_at': forms.TimeInput(attrs={'type': 'time'}),
        }


OpeningHoursFormSet = forms.modelformset_factory(
    OpeningHours, form=OpeningHoursForm, extra=0,
)


class EventTypeForm(forms.ModelForm):
    class Meta:
        model = EventType
        fields = ['name', 'min_guests', 'max_guests']
        labels = {
            'name': 'Nome',
            'min_guests': 'Mínimo de convidados',
            'max_guests': 'Máximo de convidados',
        }


class PackageForm(forms.ModelForm):
    class Meta:
        model = Package
        fields = ['name', 'description', 'base_price', 'event_type']
        labels = {
            'name': 'Nome',
            'description': 'Descrição',
            'base_price': 'Preço base',
            'event_type': 'Tipo de evento',
        }
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class MenuForm(forms.ModelForm):
    class Meta:
        model = Menu
        fields = ['name', 'description', 'price_per_person']
        labels = {
            'name': 'Nome',
            'description': 'Descrição',
            'price_per_person': 'Preço por pessoa',
        }
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}


MenuItemFormSet = forms.inlineformset_factory(
    Menu,
    MenuItem,
    fields=['name', 'description', 'category'],
    labels={'name': 'Nome', 'description': 'Descrição', 'category': 'Categoria'},
    extra=1,
    can_delete=True,
)


class DecorationOptionForm(forms.ModelForm):
    class Meta:
        model = DecorationOption
        fields = ['name', 'description', 'price']
        labels = {'name': 'Nome', 'description': 'Descrição', 'price': 'Preço'}
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}


class FAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ['question', 'answer', 'order']
        labels = {'question': 'Pergunta', 'answer': 'Resposta', 'order': 'Ordem'}
        widgets = {'answer': forms.Textarea(attrs={'rows': 3})}


class ImageForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ['image', 'caption', 'order']
        labels = {'image': 'Imagem', 'caption': 'Legenda', 'order': 'Ordem'}


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'file']
        labels = {'title': 'Título', 'file': 'Arquivo'}

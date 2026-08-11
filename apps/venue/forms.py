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


class BootstrapFormMixin:
    """Adds Bootstrap form-control/form-select/form-check-input classes to widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = 'form-check-input'
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs['class'] = 'form-select'
            else:
                widget.attrs['class'] = 'form-control'


class VenueProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Venue
        fields = [
            'name',
            'description',
            'address',
            'whatsapp_number',
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


class OpeningHoursForm(BootstrapFormMixin, forms.ModelForm):
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


class EventTypeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = EventType
        fields = ['name', 'min_guests', 'max_guests']
        labels = {
            'name': 'Nome',
            'min_guests': 'Mínimo de convidados',
            'max_guests': 'Máximo de convidados',
        }


class PackageForm(BootstrapFormMixin, forms.ModelForm):
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


class MenuForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Menu
        fields = ['name', 'description', 'price_per_person']
        labels = {
            'name': 'Nome',
            'description': 'Descrição',
            'price_per_person': 'Preço por pessoa',
        }
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}


class MenuItemForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ['name', 'description', 'category']
        labels = {'name': 'Nome', 'description': 'Descrição', 'category': 'Categoria'}


MenuItemFormSet = forms.inlineformset_factory(
    Menu,
    MenuItem,
    form=MenuItemForm,
    extra=1,
    can_delete=True,
)


class DecorationOptionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = DecorationOption
        fields = ['name', 'description', 'price']
        labels = {'name': 'Nome', 'description': 'Descrição', 'price': 'Preço'}
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}


class FAQForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ['question', 'answer', 'order']
        labels = {'question': 'Pergunta', 'answer': 'Resposta', 'order': 'Ordem'}
        widgets = {'answer': forms.Textarea(attrs={'rows': 3})}


class ImageForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Image
        fields = ['image', 'caption', 'order']
        labels = {'image': 'Imagem', 'caption': 'Legenda', 'order': 'Ordem'}


class DocumentForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'file']
        labels = {'title': 'Título', 'file': 'Arquivo'}

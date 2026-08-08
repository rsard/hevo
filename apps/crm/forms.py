from django import forms

from apps.crm.models import Label


class LabelForm(forms.ModelForm):
    """Form for creating or editing a Label (name and color)."""

    class Meta:
        model = Label
        fields = ['name', 'color']
        labels = {'name': 'Nome', 'color': 'Cor'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            is_select = isinstance(field.widget, forms.Select)
            field.widget.attrs['class'] = 'form-select' if is_select else 'form-control'

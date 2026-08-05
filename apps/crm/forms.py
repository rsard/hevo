from django import forms

from apps.crm.models import Label


class LabelForm(forms.ModelForm):
    class Meta:
        model = Label
        fields = ['name', 'color']
        labels = {'name': 'Nome', 'color': 'Cor'}

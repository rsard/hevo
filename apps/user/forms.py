from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    """AuthenticationForm with Bootstrap's form-control class on its widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

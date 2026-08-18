from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm


class LoginForm(AuthenticationForm):
    """AuthenticationForm with Bootstrap's form-control class on its widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class HevoPasswordResetForm(PasswordResetForm):
    """PasswordResetForm with Bootstrap's form-control class on its widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class HevoSetPasswordForm(SetPasswordForm):
    """SetPasswordForm with Bootstrap's form-control class on its widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

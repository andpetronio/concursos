from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "El usuario o la contraseña no son correctos.",
        "inactive": "Esta cuenta no está habilitada.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuario"
        self.fields["username"].widget.attrs.update(autocomplete="username", autofocus=True)
        self.fields["password"].label = "Contraseña"
        self.fields["password"].widget.attrs["autocomplete"] = "current-password"

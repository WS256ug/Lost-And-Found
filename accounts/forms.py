from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Username",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Password",
                "autocomplete": "current-password",
            }
        ),
    )


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=False)
    phone_number = forms.CharField(max_length=20, required=False)
    identification_number = forms.CharField(
        max_length=50,
        required=True,
        label="Identification card or National ID card number",
    )
    role = forms.ChoiceField(choices=Profile.Role.choices)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "email",
            "phone_number",
            "identification_number",
            "role",
            "password1",
            "password2",
        )

    field_order = (
        "username",
        "email",
        "phone_number",
        "identification_number",
        "role",
        "password1",
        "password2",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {
                "placeholder": "Username",
                "autocomplete": "username",
            }
        )
        self.fields["email"].widget.attrs.update(
            {
                "placeholder": "Email address",
                "autocomplete": "email",
            }
        )
        self.fields["phone_number"].widget.attrs.update(
            {
                "placeholder": "Phone number",
                "autocomplete": "tel",
            }
        )
        self.fields["identification_number"].widget.attrs.update(
            {
                "placeholder": "ID or registration card number",
                "autocomplete": "off",
            }
        )
        self.fields["role"].widget.attrs.update({"autocomplete": "off"})
        self.fields["password1"].widget.attrs.update(
            {
                "placeholder": "Create password",
                "autocomplete": "new-password",
            }
        )
        self.fields["password2"].widget.attrs.update(
            {
                "placeholder": "Confirm password",
                "autocomplete": "new-password",
            }
        )


class AdminUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "is_active", "is_staff")


class AdminProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("role", "phone_number", "identification_number")

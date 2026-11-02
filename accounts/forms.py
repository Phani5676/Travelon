from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from buses.forms import BootstrapMixin
from buses.models import Operator


class SignupForm(BootstrapMixin, UserCreationForm):
    email = forms.EmailField(required=True)
    is_operator = forms.BooleanField(required=False, label="I run a bus company")
    company_name = forms.CharField(required=False, max_length=100, label="Company name (operators only)")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean(self):
        data = super().clean()
        if data.get("is_operator") and not data.get("company_name"):
            self.add_error("company_name", "Enter your company name to sign up as an operator.")
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            if self.cleaned_data.get("is_operator"):
                Operator.objects.create(user=user, company_name=self.cleaned_data["company_name"])
        return user


class LoginForm(BootstrapMixin, AuthenticationForm):
    pass
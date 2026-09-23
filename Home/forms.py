from django import forms
from django.contrib.auth.models import User


class RegisterForm(forms.Form):
    email = forms.EmailField(label="Email (used as your login ID)")
    phone = forms.CharField(label="Phone number (used as your password)", max_length=20)

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self):
        email = self.cleaned_data["email"]
        phone = self.cleaned_data["phone"]
        return User.objects.create_user(username=email, email=email, password=phone)
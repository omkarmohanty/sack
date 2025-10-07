"""Forms for SACK Resource Management Tool"""
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

class LoginForm(forms.Form):
    """Login form for user authentication"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username',
            'id': 'username',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'id': 'password'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise forms.ValidationError("Invalid username or password.")
            if not user.is_active:
                raise forms.ValidationError("This account is inactive.")

        return cleaned_data

class UsageTimeForm(forms.Form):
    """Form for selecting resource usage time"""
    DURATION_CHOICES = [
        (15, '15 minutes'),
        (30, '30 minutes'),
        (60, '1 hour'),
        (120, '2 hours'),
        (180, '3 hours'),
        (240, '4 hours'),
        (480, '8 hours'),
    ]

    minutes = forms.ChoiceField(
        choices=DURATION_CHOICES,
        initial=60,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'usage-minutes'
        })
    )

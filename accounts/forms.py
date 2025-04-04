from django import forms
from django.contrib.auth import get_user_model
from .models import AdminSettings, CustomUser
from accounts.forms import *
from django.contrib.auth.forms import UserCreationForm
User = get_user_model()

class AdminSettingsForm(forms.ModelForm):
    class Meta:
        model = AdminSettings
        fields = [
            'url_domain_value_id',
            'billing_custom_field_id',
            'billing_custom_field_value_id',
            'api_auth_key',
        ]

class CustomUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'patronymic', 'last_name', 'is_staff'] #'is_superuser'
        labels = {
            'is_staff': 'Администратор',  # Замена стандартное название поля
        }

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'patronymic', 'last_name')
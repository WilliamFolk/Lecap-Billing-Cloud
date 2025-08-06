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
            'project_custom_field_id',
        ]

class CustomUserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Пароль",
        help_text="Оставьте пустым, чтобы не менять пароль"
    )
    class Meta:
        model = User
        fields = ['email', 'first_name', 'patronymic', 'last_name', 'is_staff'] #'is_superuser'
        labels = {
            'is_staff': 'Администратор',  # Замена стандартного названия поля
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        pwd = self.cleaned_data.get('password')
        if pwd:
            user.set_password(pwd)
        if commit:
            user.save()
        return user

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'patronymic', 'last_name')
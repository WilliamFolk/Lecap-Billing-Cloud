from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email должен быть указан")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True.')
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField("Имя", max_length=30)
    patronymic = models.CharField("Отчество", max_length=30, blank=True, null=True)
    last_name = models.CharField("Фамилия", max_length=30)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']  # Patronymic не обязателен

    def get_full_name(self):
        return " ".join(filter(None, [self.first_name, self.patronymic, self.last_name]))
    
class AdminSettings(models.Model):
    url_domain_value_id = models.CharField(
        max_length=100, 
        verbose_name="Доменное имя компании"
    )
    billing_custom_field_id = models.CharField(
        max_length=100, 
        verbose_name="ID кастомного поля Billing"
    )
    billing_custom_field_value_id = models.CharField(
        max_length=100, 
        verbose_name="ID значения кастомного поля Billing"
    )
    api_auth_key = models.CharField(
        max_length=255, 
        verbose_name="Ключ для авторизации в API"
    )

    class Meta:
        verbose_name = "Настройка администратора"
        verbose_name_plural = "Настройки администратора"

    def __str__(self):
        return "Настройки администратора"

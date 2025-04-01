from django.db import models

class ProjectRate(models.Model):
    project_id = models.CharField(max_length=50, verbose_name="ID проекта")
    project_title = models.CharField(max_length=200, verbose_name="Название проекта")
    role_id = models.CharField(max_length=50, verbose_name="ID роли")
    role_name = models.CharField(max_length=100, verbose_name="Название роли")
    rate = models.IntegerField(
        verbose_name="Почасовая ставка",
        null=True, blank=True
    )
    
    class Meta:
        unique_together = ('project_id', 'role_id')
    
    def __str__(self):
        return f"{self.project_title} – {self.role_name}: {self.rate}"

class DefaultRoleRate(models.Model):
    role_id = models.CharField(max_length=50, verbose_name="ID роли", unique=True)
    role_name = models.CharField(max_length=100, verbose_name="Название роли")
    default_rate = models.IntegerField(
        verbose_name="Стандартная ставка",
        null=True, blank=True
    )
    
    def __str__(self):
        return f"{self.role_name} ({self.default_rate})"
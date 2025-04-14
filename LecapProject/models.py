from django.db import models
from django.utils import timezone

class ProjectRate(models.Model):
    project_id = models.CharField(max_length=50, verbose_name="ID проекта")
    project_title = models.CharField(max_length=200, verbose_name="Название проекта")
    board_id = models.CharField(max_length=50, verbose_name="ID доски")
    board_title = models.CharField(max_length=200, verbose_name="Название доски")
    role_id = models.CharField(max_length=50, verbose_name="ID роли")
    role_name = models.CharField(max_length=100, verbose_name="Название роли")
    rate = models.IntegerField(
        verbose_name="Почасовая ставка",
        null=True, blank=True
    )
    # Поле для фиксации времени последней успешной синхронизации
    last_sync = models.DateTimeField(default=timezone.now, verbose_name="Последнее обновление")

    class Meta:
        unique_together = ('project_id', 'board_id', 'role_id')
    
    def save(self, *args, **kwargs):
        if self.rate == '':
            self.rate = None
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.project_title} – {self.board_title} – {self.role_name}: {self.rate}"
    

class DefaultRoleRate(models.Model):
    role_id = models.CharField(max_length=50, verbose_name="ID роли", unique=True)
    role_name = models.CharField(max_length=100, verbose_name="Название роли")
    default_rate = models.IntegerField(
        verbose_name="Стандартная ставка",
        null=True, blank=True
    )
    # Поле для фиксации времени последней синхронизации
    last_sync = models.DateTimeField(default=timezone.now, verbose_name="Последнее обновление")

    def __str__(self):
        return f"{self.role_name} ({self.default_rate})"
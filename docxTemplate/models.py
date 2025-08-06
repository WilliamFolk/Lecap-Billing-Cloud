import os
from django.db import models
from .storage import CustomStorage

custom_storage = CustomStorage()

def template_upload_path(instance, filename):
    # Файлы сохраняются в директорию "docxTemplate/savedFiles/"
    return os.path.join('docxTemplate', 'savedFiles', filename)

class TemplateFile(models.Model):
    file = models.FileField(upload_to=template_upload_path, storage=custom_storage)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name
    
    @property
    def filename(self):
        return os.path.basename(self.file.name)

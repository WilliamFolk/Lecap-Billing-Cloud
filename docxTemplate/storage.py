from django.core.files.storage import FileSystemStorage

class CustomStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        # Предполагаю, что имя уже уникально (view проводит проверку), поэтому просто возвращаю переданное имя
        return name

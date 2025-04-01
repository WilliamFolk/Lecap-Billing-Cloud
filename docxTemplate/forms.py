from django import forms

class TemplateUploadForm(forms.Form):
    file = forms.FileField(label='Выберите файл (.docx)')

class TemplateRenameForm(forms.Form):
    new_name = forms.CharField(max_length=255, label='Новое имя файла')
from django import forms
from .models import DefaultRoleRate

class DefaultRoleRateForm(forms.ModelForm):
    class Meta:
        model = DefaultRoleRate
        fields = ('id', 'default_rate',)
        widgets = {
            'id': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Что поле стандартной ставки не обязательным
        self.fields['default_rate'].required = False

DefaultRoleRateFormSet = forms.modelformset_factory(
    DefaultRoleRate,
    form = DefaultRoleRateForm,
    extra = 0  # Для редакции только существующих записей
)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth import update_session_auth_hash
from .forms import CustomUserForm, CustomUserCreationForm
from LecapProject.views import custom_administration
User = get_user_model()
from django.contrib.auth.forms import AuthenticationForm

# Доступ был только для суперпользователей, пока убрал
# @user_passes_test(lambda u: u.is_superuser)
@login_required
def edit_user(request, user_id):
    user_instance = get_object_or_404(User, pk=user_id)
    
    if request.method == "POST":
        form = CustomUserForm(request.POST, instance=user_instance)
        
        if form.is_valid():
            # Проверка: пользователь редактирует сам себя и снимает флаг администратора
            if request.user == user_instance and not form.cleaned_data.get("is_staff", True):
                messages.error(request, "Вы не можете снять с себя права администратора.")
            else:
                form.save()
                # Если админ сменил себе пароль — обновляем сессию, чтобы он не вышел
                if form.cleaned_data.get('password') and request.user == user_instance:
                    update_session_auth_hash(request, user_instance)
                messages.success(request, "Пользователь успешно обновлен.")
                return redirect('custom_administration')
    else:
        form = CustomUserForm(instance=user_instance)

    return render(request, 'edit_user.html', {'form': form})



# @user_passes_test(lambda u: u.is_superuser)
@login_required
def delete_user(request, user_id):
    user_instance = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        if request.user == user_instance:
            messages.error(request, "Вы не можете сами удалить свой профиль из системы.")
        else:
            user_instance.delete()
            messages.success(request, "Пользователь успешно удален.")
        return redirect('custom_administration')
    return render(request, 'delete_user.html', {'user': user_instance})

@login_required
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})



def home_view(request):
    if request.user.is_authenticated:
        return redirect('custom_administration')
    else:
        return redirect('login')

class CustomLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Email',
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Пароль',
        })
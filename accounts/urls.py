from django.urls import path
from .views import custom_administration, edit_user, delete_user, register, CustomLoginForm
from LecapProject import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('custom-administration/', custom_administration, name='custom_administration'),
    path('edit-user/<int:user_id>/', edit_user, name='edit_user'),
    path('delete-user/<int:user_id>/', delete_user, name='delete_user'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', register, name='register'),
    path('login/', auth_views.LoginView.as_view(
    template_name='login.html',
    authentication_form=CustomLoginForm,
    redirect_authenticated_user=True,
), name='login'),

]

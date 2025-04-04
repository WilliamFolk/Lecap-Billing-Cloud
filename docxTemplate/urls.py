from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'docxTemplate'
urlpatterns = [
    path('templates/', views.upload_template, name='templates'),
    path('templates/delete/<int:template_id>/', views.delete_template, name='delete_template'),
    path('templates/rename/<int:template_id>/', views.rename_template, name='rename_template'),
    path('templates/view/<int:template_id>/', views.view_template, name='view_template'),
]
"""
URL configuration for LecapProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView, RedirectView
from LecapProject import views
from accounts.views import home_view
from .views import get_custom_field_values, custom_administration

urlpatterns = [
    path('docxTemplate/', include('docxTemplate.urls', namespace='docxTemplate')), 
    # path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('docxTemplate/templates/', views.templates_view, name='templates'),
    path('reports/', views.reports_view, name='reports'),
    #path('administration/', views.administration_view, name='administration'),
    # accounts/urls.py
    path('custom-administration/', custom_administration, name='custom_administration'),  # :contentReference[oaicite:4]{index=4}
    path('rates/', views.rates_view, name='rates'),
    path('dashboard/', TemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
    path('get_boards/', views.get_boards, name='get_boards'),
    path('get_custom_field_values/', views.get_custom_field_values, name='get_custom_field_values'),
    path('ajax/custom-values/', get_custom_field_values, name='get_custom_field_values'),
    #path('get_swimlanes/', views.get_swimlanes, name='get_swimlanes'),
    path('ajax/swimlanes/', views.get_swimlanes, name='get_swimlanes'),
    path('ajax/statuses/', views.get_statuses, name='get_statuses'),
    path('home/', home_view, name='home'),
    path('', home_view, name='home'),
    
]


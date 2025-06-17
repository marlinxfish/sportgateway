from django.urls import path
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from . import views

app_name = 'fields'

urlpatterns = [
    # Public routes
    path('', views.public_field_list, name='public_field_list'),
    path('detail/<int:pk>/', lambda r, pk: redirect('pages:home'), name='field_detail'),  # Temporary
    
    # Manager routes
    path('manage/', views.manager_field_list, name='manager_field_list'),
    path('manage/create/', lambda r: redirect('fields:manager_field_list'), name='field_create'),  # Redirect to list
    path('manage/edit/<int:pk>/', views.field_edit, name='field_edit'),
    path('manage/delete/<int:pk>/', lambda r, pk: redirect('fields:manager_field_list'), name='field_delete'),
    path('manage/jadwal/', views.operational_menu, name='operational_menu'),
    path('manage/<int:pk>/jam-operasional/', views.edit_operational_hours, name='edit_operational_hours'),
    path('manage/<int:pk>/closures/', views.manage_closures, name='manage_closures'),
]

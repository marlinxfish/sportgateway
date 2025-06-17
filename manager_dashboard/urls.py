from django.urls import path
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, reverse
from django.http import HttpResponseRedirect
from . import views
from .views import export_manager_report_pdf

def is_manager(user):
    return user.is_authenticated and user.role == 'manager'

app_name = 'manager_dashboard'

urlpatterns = [
    # Redirect ke halaman login utama
    path('', lambda request: HttpResponseRedirect(reverse('accounts:login'))),
    path('login/', lambda request: HttpResponseRedirect(reverse('accounts:login'))),
    
    # Tetap pertahankan URL lain yang diperlukan
    path('logout/', views.manager_logout_view, name='logout'),
    path('dashboard/', user_passes_test(is_manager)(views.dashboard), name='dashboard'),
    path('profil/', views.edit_profile, name='edit_profile'),
    path('riwayat-booking/', views.manager_booking_list, name='booking_list'),
    path('laporan/cetak/', export_manager_report_pdf, name='export_pdf'),
    path('laporan/preview/', views.preview_manager_report, name='preview_report'),
    path('laporan/export-pdf/', views.export_manager_report_pdf, name='export_report_pdf'),
    path('laporan/export-excel/', views.export_manager_report_excel, name='export_report_excel'),
]

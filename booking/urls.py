from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'booking'

urlpatterns = [
    path('', views.booking_index, name='index'),
    path('buat/', lambda r: redirect('pages:home'), name='create'),  # Temporary
    path('riwayat/', views.booking_history, name='my_bookings'),
    path('<int:field_id>/', views.booking_form, name='form'),
    path('batal/<int:booking_id>/', views.cancel_booking, name='cancel'),
]

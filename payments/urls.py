from django.urls import path
from . import views

app_name = 'payments'  # Menambahkan namespace 'payments'

urlpatterns = [
    path('method/<int:booking_id>/', views.payment_method, name='method'),
    path('instruction/<uuid:code>/', views.payment_instruction, name='instruction'),
    path('confirm/<uuid:code>/', views.confirm_payment, name='confirm'),
]

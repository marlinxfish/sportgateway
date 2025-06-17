from django.urls import path
from . import views

app_name = 'pages'

urlpatterns = [
    path('', views.home, name='home'),
    path('tentang-kami/', views.about, name='about'),
    path('kontak/', views.contact, name='contact'),
    path('cari/', views.search, name='search'),  # URL untuk pencarian
]

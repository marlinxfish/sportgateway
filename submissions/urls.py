from django.urls import path
from django.views.generic import TemplateView
from .views import submit_field_view

app_name = 'submissions'  

urlpatterns = [
    path('', submit_field_view, name='submit_field'),
    path('success/', TemplateView.as_view(template_name='submissions/success.html'), name='success'),
]

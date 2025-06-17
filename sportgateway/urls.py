from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # Halaman utama langsung ke home view
    path('', include('pages.urls')),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # Aplikasi lainnya
    path('auth/', include('accounts.urls')),
    path('booking/', include('booking.urls')),
    path('fields/', include('fields.urls')),
    path('payments/', include('payments.urls')),
    path('ajukan-lapangan/', include('submissions.urls')),
    
    # Manager dashboard
    path('manager/', include('manager_dashboard.urls')),
]

# Static and media files in development
if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    # Menambahkan URL untuk file media
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Menambahkan URL untuk file static
    urlpatterns += staticfiles_urlpatterns()
    # Menambahkan URL untuk static root jika diperlukan
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
# Handler untuk halaman 404
handler404 = 'pages.views.handler404'

# Handler untuk halaman 500
handler500 = 'pages.views.handler500'

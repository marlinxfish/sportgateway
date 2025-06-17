from django.shortcuts import render, redirect
from django.template import RequestContext
from django.db.models import Q
from fields.models import Field  # Pastikan ini diimpor jika model Field ada di aplikasi fields

def home(request):
    """View untuk halaman beranda"""
    # Redirect ke dashboard manager jika user adalah manager
    if request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role == 'manager':
        from django.shortcuts import redirect
        from django.urls import reverse
        return redirect(reverse('manager_dashboard:dashboard'))
        
    context = {
        'title': 'Beranda',
        'featured_fields': [],  # Anda bisa menambahkan data lapangan unggulan di sini
    }
    return render(request, 'pages/home.html', context)

def about(request):
    """View untuk halaman tentang kami"""
    context = {
        'title': 'Tentang Kami',
    }
    return render(request, 'pages/about.html', context)

def contact(request):
    """View untuk halaman kontak"""
    context = {
        'title': 'Kontak',
    }
    return render(request, 'pages/contact.html', context)

def handler404(request, exception=None, template_name='404.html'):
    """Handler untuk halaman 404"""
    context = {
        'title': 'Halaman Tidak Ditemukan',
        'error_code': 404,
        'error_message': 'Halaman yang Anda cari tidak ditemukan.'
    }
    return render(request, 'pages/error.html', context, status=404)

def handler500(request, template_name='500.html'):
    """Handler untuk halaman 500"""
    context = {
        'title': 'Kesalahan Server',
        'error_code': 500,
        'error_message': 'Terjadi kesalahan pada server. Silakan coba lagi nanti.'
    }
    return render(request, 'pages/error.html', context, status=500)

def search(request):
    """View untuk halaman pencarian"""
    query = request.GET.get('q', '').strip()
    results = []
    
    if query:
        # Lakukan pencarian di model Field
        results = Field.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(location__icontains=query)
        ).distinct()
    
    context = {
        'title': 'Hasil Pencarian',
        'query': query,
        'results': results,
        'results_count': len(results)
    }
    return render(request, 'pages/search_results.html', context)

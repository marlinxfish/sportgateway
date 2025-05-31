from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db import transaction

from .models import Field, OperationalHour
from .forms import FieldForm, OperationalHourFormSet
from .decorators import manager_required, field_owner_required


def public_field_list(request):
    """Menampilkan daftar lapangan untuk umum dengan filter kota dan kategori"""
    city = request.GET.get('city', '')
    category = request.GET.get('category', '')
    fields = Field.objects.all()

    # Ekstrak kota dari address (diasumsikan format: 'jalan, kota, ...')
    def extract_city(address):
        if not address:
            return ''
        parts = [p.strip() for p in address.split(',')]
        if len(parts) >= 2:
            return parts[1]
        return ''

    # Daftar kota unik
    all_cities = [extract_city(f.address) for f in fields if f.address]
    cities = sorted(set([c for c in all_cities if c]))
    # Daftar kategori unik
    categories = sorted(set([f.category for f in fields if f.category]))

    # Filter
    if city:
        fields = [f for f in fields if extract_city(f.address) == city]
    if category:
        fields = [f for f in fields if f.category == category]

    return render(request, 'fields/public_field_list.html', {
        'fields': fields,
        'cities': cities,
        'categories': categories,
        'city': city,
        'category': category,
    })

@login_required
@manager_required
def manager_field_list(request):
    """Menampilkan daftar lapangan yang dimanajeri oleh user yang login"""
    try:
        # Debug: Cetak user yang sedang login
        print(f"[DEBUG] User yang login: {request.user.username} (ID: {request.user.id})")
        
        # Ambil semua lapangan yang dimiliki user
        fields = Field.objects.filter(owner=request.user).order_by('-created_at')
        
        # Debug: Cetak jumlah lapangan yang ditemukan
        print(f"[DEBUG] Jumlah lapangan ditemukan: {fields.count()}")
        
        # Debug: Cetak data yang akan ditampilkan
        if fields.exists():
            print("[DEBUG] Daftar lapangan:")
            for field in fields:
                print(f"- {field.name} (ID: {field.id}, Owner ID: {field.owner_id if field.owner else 'None'})")
        else:
            print("[DEBUG] Tidak ada lapangan yang ditemukan untuk user ini")
            # Tambahkan pesan info jika tidak ada lapangan
            messages.info(request, "Anda belum memiliki lapangan. Silakan tambahkan lapangan terlebih dahulu.")
        
        # Pencarian (akan ditangani oleh DataTables)
        query = request.GET.get('q', '')
        
        context = {
            'fields': fields,
            'query': query,
            'fields_count': fields.count(),
            'has_fields': fields.exists()
        }
        
        return render(request, 'fields/manager/field_list.html', context)
        
    except Exception as e:
        error_msg = f"Terjadi kesalahan saat memuat daftar lapangan: {str(e)}"
        print(f"[ERROR] {error_msg}")
        messages.error(request, error_msg)
        return render(request, 'fields/manager/field_list.html', {
            'fields': [],
            'query': '',
            'fields_count': 0,
            'has_fields': False,
            'error': str(e)
        })

@login_required
@manager_required
def field_create(request):
    if request.method == 'POST':
        form = FieldForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                field = form.save(commit=False)
                field.owner = request.user
                field.save()
                
                # Buat jam operasional default
                from .utils import create_default_operational_hours
                create_default_operational_hours(field)
                
                messages.success(
                    request, 
                    f'Lapangan "{field.name}" berhasil ditambahkan.',
                    extra_tags='success'
                )
                return redirect('fields:manager_field_list')
    else:
        form = FieldForm()
    
    return render(request, 'fields/field_form.html', {
        'form': form,
        'title': 'Tambah Lapangan Baru',
        'submit_text': 'Simpan Lapangan',
        'cancel_url': 'fields:manager_field_list'
    })

@login_required
@manager_required
@field_owner_required
def field_edit(request, pk):
    field = get_object_or_404(Field, pk=pk)
    
    if request.method == 'POST':
        form = FieldForm(request.POST, request.FILES, instance=field)
        if form.is_valid():
            with transaction.atomic():
                field = form.save()
                messages.success(
                    request, 
                    f'Lapangan "{field.name}" berhasil diperbarui.',
                    extra_tags='success'
                )
                return redirect('fields:manager_field_list')
    else:
        form = FieldForm(instance=field)
    
    return render(request, 'fields/field_form.html', {
        'form': form,
        'title': f'Edit {field.name}',
        'submit_text': 'Simpan Perubahan',
        'cancel_url': 'fields:manager_field_list'
    })

@require_http_methods(['POST'])
@login_required
@manager_required
@field_owner_required
def field_delete(request, pk):
    field = get_object_or_404(Field, pk=pk)
    field_name = field.name
    field.delete()
    messages.success(
        request, 
        f'Lapangan "{field_name}" berhasil dihapus.',
        extra_tags='success'
    )
    return redirect('fields:manager_field_list')

@login_required
@manager_required
@field_owner_required
def edit_operational_hours(request, pk):
    field = get_object_or_404(Field, pk=pk)
    
    # Buat jam operasional default jika belum ada
    if not field.operational_hours.exists():
        from .utils import create_default_operational_hours
        create_default_operational_hours(field)
    
    # Ambil queryset yang sudah diurutkan berdasarkan hari
    queryset = field.operational_hours.all().order_by('day')
    
    if request.method == 'POST':
        formset = OperationalHourFormSet(
            request.POST, 
            queryset=queryset,
            form_kwargs={'field': field}
        )
        
        if formset.is_valid():
            try:
                with transaction.atomic():
                    instances = formset.save(commit=False)
                    
                    # Simpan setiap instance
                    for instance in instances:
                        instance.field = field
                        instance.save()
                    
                    # Hapus jam operasional yang ditandai untuk dihapus
                    for obj in formset.deleted_objects:
                        obj.delete()
                
                messages.success(
                    request, 
                    f'Jam operasional untuk {field.name} berhasil diperbarui.',
                    extra_tags='success'
                )
                return redirect('fields:operational_menu')
                
            except Exception as e:
                messages.error(
                    request, 
                    f'Terjadi kesalahan: {str(e)}',
                    extra_tags='danger'
                )
        else:
            # Tampilkan pesan error untuk setiap form yang tidak valid
            for form in formset:
                if form.errors:
                    for field_errors in form.errors.values():
                        for error in field_errors:
                            messages.error(
                                request, 
                                f"{form.instance.get_day_display()}: {error}",
                                extra_tags='danger'
                            )
    else:
        formset = OperationalHourFormSet(queryset=queryset, form_kwargs={'field': field})
    
    return render(request, 'fields/edit_operational_hours.html', {
        'field': field,
        'formset': formset,
        'title': f'Atur Jam Operasional - {field.name}'
    })



from .models import FieldClosure

@login_required
@manager_required
@field_owner_required
def manage_closures(request, pk):
    field = get_object_or_404(Field, pk=pk)
    if request.method == 'POST':
        closure_date = request.POST.get('closure_date')
        reason = request.POST.get('closure_reason')
        if closure_date and reason:
            exists = FieldClosure.objects.filter(field=field, closure_date=closure_date).exists()
            if exists:
                messages.error(request, f"Lapangan sudah ditutup pada tanggal {closure_date}.")
            else:
                FieldClosure.objects.create(field=field, closure_date=closure_date, reason=reason)
                messages.success(request, "Penutupan berhasil ditambahkan.")
        else:
            messages.error(request, "Tanggal dan alasan harus diisi.")
    closures = FieldClosure.objects.filter(field=field)
    return render(request, 'fields/manage_closures.html', {
        'closures': closures,
        'field_id': pk,
        'field': field,
    })

@login_required
@manager_required
def operational_menu(request):
    fields = Field.objects.filter(owner=request.user).order_by('name')
    
    # Pencarian
    query = request.GET.get('q', '')
    if query:
        fields = fields.filter(
            Q(name__icontains=query) |
            Q(address__icontains=query)
        )
    
    return render(request, 'fields/operational_menu.html', {
        'fields': fields,
        'query': query
    })



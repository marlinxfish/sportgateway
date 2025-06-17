from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from fields.models import Field, FieldClosure, OperationalHour
from .models import Booking
from payments.views import create_payment_for_booking
from datetime import datetime, timedelta
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.db.models import Case, When, Value, IntegerField

def manager_required(login_url='manager_dashboard:dashboard'):
    """
    Decorator for views that checks that the user is a manager,
    redirecting to the manager dashboard page if necessary.
    """
    def check_manager(user):
        return user.is_authenticated and hasattr(user, 'role') and user.role == 'manager'
    
    def decorator(view_func):
        decorated_view_func = user_passes_test(
            check_manager,
            login_url=login_url,
            redirect_field_name=None
        )(view_func)
        return decorated_view_func
    return decorator

def prevent_manager(view_func):
    """
    Decorator for views that should not be accessible to managers.
    Redirects managers to their dashboard.
    """
    def _wrapped_view(request, *args, **kwargs):
        if hasattr(request.user, 'role') and request.user.role == 'manager':
            from django.urls import reverse
            from django.shortcuts import redirect
            return redirect(reverse('manager_dashboard:dashboard'))
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
@prevent_manager
def booking_index(request):
    fields = Field.objects.all()
    return render(request, 'booking/index.html', {'fields': fields})

@login_required
@prevent_manager
def booking_form(request, field_id):
    field = get_object_or_404(Field, pk=field_id)

    selected_date_str = request.GET.get('date')
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = datetime.today().date()
    else:
        selected_date = datetime.today().date()

    # Cek penutupan lapangan di tanggal tersebut
    is_closed = FieldClosure.objects.filter(field=field, closure_date=selected_date).exists()

    # Cek jam operasional hari itu
    day_name = selected_date.strftime('%A')  # 'Monday', dst
    hari_map = {
        'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu',
        'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'
    }
    hari_id = hari_map.get(day_name, day_name)
    op_hour = OperationalHour.objects.filter(field=field, day=hari_id).first()

    booking_disabled = False
    reason_closed = None
    if is_closed:
        booking_disabled = True
        reason_closed = 'Lapangan tutup pada tanggal ini.'
    elif not op_hour or op_hour.is_closed:
        booking_disabled = True
        reason_closed = 'Lapangan tidak beroperasi pada hari ini.'

    existing_bookings = Booking.objects.filter(field=field, date=selected_date, is_paid=True)
    booked_slots = set()
    for b in existing_bookings:
        current = datetime.combine(b.date, b.start_time)
        while current.time() < b.end_time:
            booked_slots.add(current.strftime("%H:%M"))
            current += timedelta(hours=1)

    # Generate available hours sesuai jam operasional
    available_hours = []
    if op_hour and not op_hour.is_closed:
        start_hour = op_hour.open_time.hour
        end_hour = op_hour.close_time.hour
        for hour in range(start_hour, end_hour):
            slot = f"{hour:02d}:00"
            available_hours.append(slot)

    if request.method == 'POST' and not booking_disabled:
        selected_hours = request.POST.getlist('hours')
        if not selected_hours:
            messages.error(request, "Pilih minimal satu jam.")
        else:
            start = datetime.strptime(min(selected_hours), '%H:%M').time()
            end = (datetime.combine(datetime.today(), datetime.strptime(max(selected_hours), '%H:%M').time()) + timedelta(hours=1)).time()

            # Validasi jam booking harus di dalam jam operasional
            if op_hour:
                open_time = op_hour.open_time
                close_time = op_hour.close_time
                if start < open_time or end > close_time:
                    messages.error(request, f"Jam booking harus di antara {open_time.strftime('%H:%M')} - {close_time.strftime('%H:%M')}")
                else:
                    booking = Booking.objects.create(
                        user=request.user,
                        field=field,
                        date=selected_date,
                        start_time=start,
                        end_time=end,
                        is_paid=False
                    )
                    # Arahkan ke halaman pemilihan metode pembayaran
                    return redirect('payments:method', booking_id=booking.id)
            else:
                messages.error(request, "Jam operasional tidak ditemukan untuk hari ini.")

    return render(request, 'booking/form.html', {
        'field': field,
        'selected_date': selected_date,
        'available_hours': available_hours,
        'booked_slots': booked_slots,
        'today': datetime.today().date(),
        'booking_disabled': booking_disabled,
        'reason_closed': reason_closed,
        'op_hour': op_hour,
    })

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

@login_required
@prevent_manager
def booking_history(request):
    try:
        # Ambil semua booking untuk user yang login
        # Urutkan: belum bayar dulu, lalu sudah bayar, terakhir yang dibatalkan
        # Diurutkan berdasarkan tanggal booking terbaru dan waktu pembuatan
        
        
        booking_list = Booking.objects.filter(
            user=request.user
        ).select_related('field').annotate(
            status_order=Case(
                When(is_cancelled=True, then=Value(2)),
                When(is_paid=False, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by('status_order', '-date', '-created_at')
        
        # Update total_price untuk booking yang belum ada harganya
        for booking in booking_list:
            if not booking.total_price:
                booking.calculate_total_price()
                booking.save()
        
        # Konfigurasi pagination
        page = request.GET.get('page', 1)
        items_per_page = 10
        paginator = Paginator(booking_list, items_per_page)
        
        try:
            bookings = paginator.page(page)
        except PageNotAnInteger:
            bookings = paginator.page(1)
        except EmptyPage:
            bookings = paginator.page(paginator.num_pages)
        
        # Menentukan range halaman yang akan ditampilkan (maksimal 5 nomor halaman)
        index = bookings.number - 1
        max_index = len(paginator.page_range)
        start_index = index - 2 if index >= 2 else 0
        if index < 2:
            end_index = 5
        else:
            end_index = index + 3 if index <= max_index - 3 else max_index
        
        page_range = list(paginator.page_range)[start_index:end_index]
        
        # Hitung start_index untuk nomor urut
        start_index = (bookings.number - 1) * items_per_page
        
        return render(request, 'booking/history.html', {
            'bookings': bookings,
            'bookings_count': booking_list.count(),
            'paginator': paginator,
            'page_range': page_range,
            'start_index': start_index + 1  # Dimulai dari 1, bukan 0
        })

    except Exception as e:
        print(f"Error in booking_history: {str(e)}")
        # Tampilkan pesan error ke user
        messages.error(request, f"Terjadi kesalahan: {str(e)}")
        return render(request, 'booking/history.html', {
            'bookings': [],
            'bookings_count': 0,
            'start_index': 0,
            'page_range': range(1)
        })

@login_required
@prevent_manager
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Pastikan hanya pemilik booking yang bisa membatalkan
    if booking.user != request.user:
        return HttpResponseForbidden("Anda tidak diizinkan membatalkan booking ini")
    
    # Pastikan booking belum dibayar dan belum dibatalkan
    if booking.is_paid:
        messages.error(request, "Booking yang sudah dibayar tidak dapat dibatalkan")
    elif booking.is_cancelled:
        messages.error(request, "Booking ini sudah dibatalkan sebelumnya")
    else:
        # Lakukan pembatalan booking
        booking.is_cancelled = True
        booking.save()
        messages.success(request, "Booking berhasil dibatalkan")
    
    # Redirect kembali ke halaman riwayat booking
    return HttpResponseRedirect(reverse('booking:my_bookings'))

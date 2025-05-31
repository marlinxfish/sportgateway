from django.shortcuts import render, redirect, HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.utils import timezone
from .forms import ManagerProfileForm
from booking.models import Booking
from django.db.models import Count, Q, Sum
from fields.models import Field
from django.db.models.functions import TruncDate
from xhtml2pdf import pisa
from django.template.loader import get_template
import datetime
import csv
import json



def manager_login_view(request):
    if request.user.is_authenticated and request.user.role == 'manager':
        return redirect('manager_dashboard:dashboard')

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None and user.role == 'manager':
            login(request, user)
            return redirect('manager_dashboard:dashboard')
        else:
            return render(request, 'manager_dashboard/login_standalone.html', {'error': 'Username atau password salah.'})

    return render(request, 'manager_dashboard/login_standalone.html')

def manager_logout_view(request):
    logout(request)
    return redirect('/')

@login_required
def dashboard(request):
    try:
        # Pastikan hanya manager yang bisa mengakses
        if not hasattr(request.user, 'role') or request.user.role != 'manager':
            return HttpResponseForbidden("Akses ditolak")
        
        # Hitung statistik hanya untuk lapangan milik manager ini
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        fields = Field.objects.filter(owner=request.user)
        
        # Inisialisasi variabel dengan nilai default
        monthly_income = 0
        monthly_bookings = 0
        today_bookings = []
        recent_bookings = []
        booking_dates = []
        booking_counts = []
        
        try:
            # Filter booking hanya untuk lapangan milik manager ini
            booking_qs = Booking.objects.filter(field__in=fields)

            # Total pendapatan bulan ini
            monthly_income = booking_qs.filter(
                is_paid=True,
                date__year=start_of_month.year,
                date__month=start_of_month.month
            ).aggregate(total=Sum('total_price'))['total'] or 0
            
            # Total booking bulan ini
            monthly_bookings = booking_qs.filter(
                date__year=start_of_month.year,
                date__month=start_of_month.month
            ).count()
            
            # Booking hari ini
            today_bookings = list(booking_qs.filter(date=today).order_by('start_time'))
            
            # 5 booking terbaru
            recent_bookings = list(booking_qs.all().order_by('-created_at')[:5])
            
            # Data untuk grafik - Hitung booking per hari dalam 7 hari terakhir
            seven_days_ago = today - timezone.timedelta(days=6)
            daily_bookings = list(booking_qs.filter(
                date__range=[seven_days_ago, today]
            ).annotate(
                booking_date=TruncDate('date')
            ).values('booking_date').annotate(
                count=Count('id')
            ).order_by('booking_date'))
            
            # Format data untuk chart
            booking_dates = []
            booking_counts = []
            
            for i in range(7):
                current_date = seven_days_ago + timezone.timedelta(days=i)
                booking_dates.append(current_date.strftime('%a'))
                count = next((item['count'] for item in daily_bookings if item['booking_date'] == current_date), 0)
                booking_counts.append(count)
                
        except Exception as e:
            print(f"Error in dashboard queries: {str(e)}")
            # Tetap lanjut dengan nilai default jika terjadi error
        
        # Statistik tambahan
        from django.contrib.auth import get_user_model
        User = get_user_model()
        total_users = User.objects.filter(is_active=True).count()

        # Status booking hanya untuk lapangan milik manager ini
        booking_status = {
            'success': booking_qs.filter(is_paid=True, is_cancelled=False).count(),
            'pending': booking_qs.filter(is_paid=False, is_cancelled=False).count(),
            'cancelled': booking_qs.filter(is_cancelled=True).count(),
        }

        # Booking per bulan (12 bulan terakhir) hanya untuk lapangan milik manager
        monthly_labels = []
        monthly_revenue = []
        monthly_booking_counts = []
        for i in range(11, -1, -1):
            month = (today.replace(day=1) - timezone.timedelta(days=30*i))
            label = month.strftime('%b %Y')
            monthly_labels.append(label)
            income = booking_qs.filter(
                is_paid=True,
                date__year=month.year,
                date__month=month.month
            ).aggregate(total=Sum('total_price'))['total'] or 0
            if income is None:
                income = 0
            monthly_revenue.append(float(income))
            # Tambahkan jumlah booking per bulan
        context = {
            'monthly_income': monthly_income,
            'monthly_bookings': monthly_bookings,
            'booking_status': booking_status,
            'monthly_revenue': json.dumps(monthly_revenue or []),
            'monthly_labels': json.dumps(monthly_labels or []),
            'monthly_booking_counts': json.dumps(monthly_booking_counts or []),
            'recent_bookings': recent_bookings,
        }
        
        return render(request, 'manager_dashboard/dashboard.html', context)
        
    except Exception as e:
        print(f"Critical error in dashboard view: {str(e)}")
        # Tampilkan halaman error yang lebih ramah
        return render(request, 'manager_dashboard/error.html', {
            'error_message': 'Terjadi kesalahan saat memuat dashboard. Silakan coba lagi nanti.'
        }, status=500)

@login_required
def edit_profile(request):
    user = request.user
    profile_form = ManagerProfileForm(request.POST or None, request.FILES or None, instance=user)
    password_form = PasswordChangeForm(user, request.POST or None)

    success = False

    if request.method == 'POST':
        if profile_form.is_valid():
            profile_form.save()
            success = True
            messages.success(request, "Profil berhasil diperbarui.")

        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, password_form.user)
            success = True
            messages.success(request, "Password berhasil diganti.")

        if not success:
            messages.error(request, "Tidak ada perubahan disimpan. Mohon cek kembali.")

        return redirect('manager_dashboard:edit_profile')

    return render(request, 'manager_dashboard/edit_profile.html', {
        'form': profile_form,
        'password_form': password_form,
    })

@login_required
def manager_booking_list(request):
    try:
        # Debug: Cetak user yang sedang login
        print(f"Manager yang login: {request.user.username}")
        
        # Dapatkan semua lapangan yang dimiliki oleh manager
        fields = Field.objects.filter(owner=request.user)
        print(f"Jumlah lapangan yang dimiliki: {fields.count()}")
        
        # Dapatkan parameter filter
        selected_field = request.GET.get('field')
        selected_date = request.GET.get('date')
        
        # Query dasar untuk booking
        bookings = Booking.objects.filter(field__in=fields)
        
        # Terapkan filter jika ada
        if selected_field:
            bookings = bookings.filter(field__id=selected_field)
        if selected_date:
            bookings = bookings.filter(date=selected_date)
            
        # Urutkan dan select_related untuk optimasi query
        bookings = bookings.select_related('field', 'user').order_by('-date', '-start_time')
        print(f"Jumlah booking ditemukan: {bookings.count()}")
        
        # Hitung statistik
        total_booking = bookings.count()
        unpaid_booking = bookings.filter(is_paid=False).count()
        
        # Hitung statistik per lapangan
        field_stats = list(bookings.values('field__name').annotate(
            jumlah=Count('id'),
            total_pendapatan=Sum('total_price')
        ).order_by('-jumlah'))
        # Tambahkan persentase untuk progress bar
        for fs in field_stats:
            if total_booking > 0:
                fs['percent'] = int(fs['jumlah'] * 100 / total_booking)
            else:
                fs['percent'] = 0
        
        # Hitung statistik harian untuk chart (compatible dengan SQLite)
        from collections import Counter
        dates = list(bookings.values_list('date', flat=True))
        date_counts = Counter(dates)
        sorted_dates = sorted(date_counts.keys())
        chart_labels = [str(d) for d in sorted_dates]
        chart_data = [date_counts[d] for d in sorted_dates]
        # daily_stats tetap dikirim agar tidak error di template
        daily_stats = [
            {'day': d, 'jumlah': date_counts[d]} for d in sorted_dates
        ]
        
        # Debug: Cetak beberapa data booking
        for i, booking in enumerate(bookings[:3]):  # Cetak 3 booking pertama
            print(f"Booking {i+1}: {booking.field.name} - {booking.date} {booking.start_time}")
        
        context = {
            'bookings': bookings,
            'fields': fields,  # Untuk dropdown filter
            'selected_field': int(selected_field) if selected_field else '',
            'selected_date': selected_date if selected_date else '',
            'bookings_count': total_booking,
            'unpaid_booking': unpaid_booking,
            'field_stats': field_stats,
            'daily_stats': daily_stats,
            'chart_labels': json.dumps(chart_labels),
            'chart_data': json.dumps(chart_data)
        }
        
        return render(request, 'manager_dashboard/booking_list.html', context)
        
    except Exception as e:
        import traceback
        print(f"Error in manager_booking_list: {str(e)}")
        traceback.print_exc()
        messages.error(request, f"Terjadi kesalahan: {str(e)}")
        return render(request, 'manager_dashboard/booking_list.html', {
            'bookings': [],
            'fields': Field.objects.filter(owner=request.user),
            'selected_field': '',
            'selected_date': '',
            'bookings_count': 0,
            'unpaid_booking': 0,
            'field_stats': [],
            'daily_stats': [],
            'chart_labels': json.dumps([]),
            'chart_data': json.dumps([])
        })

@login_required
def preview_manager_report(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    today = datetime.date.today()

    fields = Field.objects.filter(owner=request.user)
    bookings = Booking.objects.filter(field__in=fields)

    if start_date:
        bookings = bookings.filter(date__gte=start_date)
    if end_date:
        bookings = bookings.filter(date__lte=end_date)

    total_earning = bookings.filter(is_paid=True).aggregate(total=Sum('field__price_per_hour'))['total'] or 0
    booking_count = bookings.count()
    paid_count = bookings.filter(is_paid=True).count()
    unpaid_count = bookings.filter(is_paid=False).count()

    context = {
        'manager': request.user,
        'bookings': bookings,
        'total_earning': total_earning,
        'booking_count': booking_count,
        'paid_count': paid_count,
        'unpaid_count': unpaid_count,
        'date': today,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'manager_dashboard/report_preview.html', context)

@login_required
def export_manager_report_excel(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Handle None or 'None' string values
    if start_date == 'None':
        start_date = None
    if end_date == 'None':
        end_date = None

    fields = Field.objects.filter(owner=request.user)
    bookings = Booking.objects.filter(field__in=fields)

    if start_date and start_date.lower() != 'none':
        bookings = bookings.filter(date__gte=start_date)
    if end_date and end_date.lower() != 'none':
        bookings = bookings.filter(date__lte=end_date)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="laporan-booking.csv"'

    writer = csv.writer(response)
    writer.writerow(['No', 'Penyewa', 'Lapangan', 'Tanggal', 'Jam', 'Status'])

    for idx, b in enumerate(bookings, start=1):
        writer.writerow([
            idx,
            b.user.username,
            b.field.name,
            b.date,
            f"{b.start_time} - {b.end_time}",
            'Sudah Dibayar' if b.is_paid else 'Belum Dibayar'
        ])

    return response

@login_required
def export_manager_report_pdf(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    today = datetime.date.today()

    # Handle None or 'None' string values
    if start_date == 'None':
        start_date = None
    if end_date == 'None':
        end_date = None

    fields = Field.objects.filter(owner=request.user)
    bookings = Booking.objects.filter(field__in=fields).select_related('user', 'field').order_by('-date')

    # Apply date filters if provided
    if start_date and start_date.lower() != 'none':
        bookings = bookings.filter(date__gte=start_date)
    if end_date and end_date.lower() != 'none':
        bookings = bookings.filter(date__lte=end_date)

    total_earning = (
        bookings.filter(is_paid=True).aggregate(total=Sum('field__price_per_hour'))['total'] or 0
    )
    booking_count = bookings.count()
    paid_count = bookings.filter(is_paid=True).count()
    unpaid_count = bookings.filter(is_paid=False).count()

    context = {
        'manager': request.user,
        'bookings': bookings,
        'total_earning': total_earning,
        'booking_count': booking_count,
        'paid_count': paid_count,
        'unpaid_count': unpaid_count,
        'date': today,
        'start_date': start_date if start_date and start_date != 'None' else None,
        'end_date': end_date if end_date and end_date != 'None' else None,
    }

    template = get_template('manager_dashboard/report_pdf.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="laporan-manager-{today}.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    return response if not pisa_status.err else HttpResponse('Terjadi kesalahan saat membuat PDF', status=500)

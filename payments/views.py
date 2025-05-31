from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_http_methods
from .models import Payment
from booking.models import Booking
import random

@require_http_methods(["GET", "POST"])
def payment_method(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Cek apakah sudah ada pembayaran yang sedang berlangsung
    payment = Payment.objects.filter(booking=booking).first()
    
    # Hitung durasi sewa dalam jam
    duration_hours = (booking.end_time.hour - booking.start_time.hour)
    # Hitung total pembayaran berdasarkan harga per jam lapangan
    amount = duration_hours * booking.field.price_per_hour
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        if not payment_method:
            messages.error(request, 'Silakan pilih metode pembayaran')
            return redirect('payments:method', booking_id=booking.id)
        
        if not payment:
            # Buat pembayaran baru
            payment = Payment.objects.create(
                booking=booking,
                amount=amount,
                payment_method=payment_method,
                payment_status='pending'
            )
        else:
            # Update metode pembayaran jika berubah
            if payment.payment_method != payment_method:
                payment.payment_method = payment_method
                # Reset nomor VA jika metode pembayaran berubah
                payment.virtual_account = None
                payment.save()
        
        # Generate kode unik untuk pembayaran
        if not payment.code:
            payment.code = f"PAY-{booking.id:04d}-{random.randint(1000, 9999)}"
            payment.save()
        
        # Set waktu kedaluwarsa pembayaran (contoh: 24 jam dari sekarang)
        if not payment.payment_expiry:
            payment.payment_expiry = timezone.now() + timedelta(hours=24)
            payment.save()
        
        # Generate nomor VA berdasarkan bank yang dipilih jika belum ada
        if not payment.virtual_account:
            bank_codes = {
                'va_bca': '39012',
                'va_bni': '39013',
                'va_bri': '39014',
                'va_mandiri': '39015',
                'va_permata': '39016',
                'qris': '39999',  # Khusus QRIS
            }
            
            # Ambil kode bank atau default ke 39999 (lainnya)
            bank_code = bank_codes.get(payment.payment_method, '39999')
            
            # Format: Kode Bank + 8 digit nomor acak
            va_number = f"{bank_code}{random.randint(10000000, 99999999)}"
            payment.virtual_account = va_number
            payment.save()
        
        return redirect('payments:instruction', code=payment.code)
    
    # Jika belum ada payment, buat dulu dengan default values untuk ditampilkan di template
    if not payment:
        payment = Payment(
            booking=booking,
            amount=amount,
            payment_status='pending'
        )
    
    return render(request, 'payments/payment_method.html', {
        'booking': booking,
        'payment': payment
    })

def payment_instruction(request, code):
    payment = get_object_or_404(Payment, code=code, booking__user=request.user)
    
    # Debug logging
    print(f"Payment Status: {payment.payment_status}")
    print(f"Payment Method: {payment.payment_method}")
    print(f"Is VA: {'va_' in str(payment.payment_method)}")
    
    return render(request, 'payments/payment_instruction.html', {
        'payment': payment,
        'booking': payment.booking
    })

def confirm_payment(request, code):
    payment = get_object_or_404(Payment, code=code, booking__user=request.user)
    
    # Redirect ke halaman instruksi jika bukan metode VA
    if not payment.payment_method.startswith('va_'):
        return redirect('payments:instruction', code=payment.code)
    
    if request.method == 'POST':
        va_number = request.POST.get('payment_code', '').strip()
        
        # Validasi nomor VA
        if not va_number:
            messages.error(request, '❌ Nomor Virtual Account tidak boleh kosong')
        elif payment.payment_status == 'completed':
            messages.info(request, 'ℹ️ Pembayaran ini sudah dikonfirmasi sebelumnya')
        else:
            # Cek apakah slot waktu masih tersedia
            booking = payment.booking
            existing_booking = Booking.objects.filter(
                field=booking.field,
                date=booking.date,
                start_time__lt=booking.end_time,
                end_time__gt=booking.start_time,
                is_paid=True  # Hanya periksa booking yang sudah dibayar
            ).exclude(id=booking.id).first()
            
            if existing_booking:
                # Update status booking menjadi 'dibatalkan' karena sudah dipesan orang lain
                booking.status = 'cancelled'
                booking.cancellation_reason = 'Slot waktu sudah dipesan oleh orang lain'
                booking.save()
                
                # Update status pembayaran
                payment.payment_status = 'expired'
                payment.save()
                
                messages.error(request, '❌ Maaf, slot waktu ini sudah dipesan oleh orang lain. Booking Anda telah dibatalkan.')
                return redirect('payments:instruction', code=payment.code)
            
            # Validasi nomor VA sesuai dengan yang di-generate sebelumnya
            if va_number == payment.virtual_account:
                # Update status pembayaran dan simpan kode konfirmasi
                payment.payment_status = 'completed'
                payment.payment_confirmation_code = va_number
                payment.save()
                
                # Update status booking
                booking.is_paid = True
                booking.status = 'confirmed'
                booking.save()
                
                messages.success(request, '✅ Pembayaran berhasil dikonfirmasi!')
                return redirect('booking:my_bookings')
            else:
                messages.error(request, '❌ Nomor Virtual Account tidak valid. Pastikan nomor yang dimasukkan benar.')
    
    return render(request, 'payments/confirm_payment.html', {
        'payment': payment
    })

def create_payment_for_booking(booking):
    # Hitung durasi sewa dalam jam
    duration_hours = (booking.end_time.hour - booking.start_time.hour)
    # Hitung total pembayaran berdasarkan harga per jam lapangan
    amount = duration_hours * booking.field.price_per_hour
    
    payment = Payment.objects.create(
        booking=booking,
        payment_method='bank_transfer',  # Default method
        amount=amount,
        payment_status='pending',
        payment_expiry=timezone.now() + timedelta(hours=24)  # Expiry 24 jam
    )
    return payment
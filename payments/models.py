from django.db import models
from booking.models import Booking
import uuid

class Payment(models.Model):
    PAYMENT_METHODS = [
        ('va_bca', 'BCA Virtual Account'),
        ('va_mandiri', 'Mandiri Virtual Account'),
        ('va_bni', 'BNI Virtual Account'),
        ('bank_transfer', 'Transfer Bank'),
        ('qris', 'QRIS'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Menunggu Pembayaran'),
        ('processing', 'Menunggu Verifikasi'),
        ('completed', 'Lunas'),
        ('expired', 'Kadaluarsa'),
        ('failed', 'Ditolak'),
    ]
    
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='bank_transfer')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    virtual_account = models.CharField(max_length=50, blank=True, null=True)
    payment_expiry = models.DateTimeField(blank=True, null=True)
    payment_confirmation_code = models.CharField(max_length=50, blank=True, null=True, help_text='Kode konfirmasi pembayaran')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Payment {self.code} - {self.booking.field.name} ({self.get_payment_status_display()})"
    
    def generate_va_number(self, bank_code):
        """Generate virtual account number based on bank code"""
        # Implementasi generate VA number sesuai kebutuhan
        # Contoh: bank_code + random digits
        import random
        va_number = f"{bank_code}{random.randint(100000000, 999999999)}"
        return va_number

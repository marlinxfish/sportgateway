from django.db import models
from django.conf import settings
from fields.models import Field

class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    field = models.ForeignKey(Field, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_paid = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False, verbose_name='Dibatalkan')
    total_price = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name='Total Harga')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def calculate_total_price(self):
        # Hitung durasi dalam jam
        duration_hours = self.end_time.hour - self.start_time.hour
        # Hitung total harga
        self.total_price = int(duration_hours * self.field.price_per_hour)
        return self.total_price
    
    def save(self, *args, **kwargs):
        # Hitung total harga sebelum menyimpan
        if not self.pk or 'force_insert' in kwargs:  # Untuk pembuatan baru
            self.calculate_total_price()
        super().save(*args, **kwargs)

    @property
    def duration(self):
        """Menghitung durasi sewa dalam jam"""
        return self.end_time.hour - self.start_time.hour
    
    def __str__(self):
        return f"{self.field.name} - {self.date} {self.start_time}-{self.end_time}"

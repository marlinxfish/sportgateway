from django.db import models
from django.conf import settings

DAYS_OF_WEEK = [
    ('Senin', 'Senin'), ('Selasa', 'Selasa'), ('Rabu', 'Rabu'),
    ('Kamis', 'Kamis'), ('Jumat', 'Jumat'), ('Sabtu', 'Sabtu'), ('Minggu', 'Minggu'),
]

class Field(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    price_per_hour = models.PositiveIntegerField()
    image = models.ImageField(upload_to='field_images/', blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text='Centang untuk menampilkan lapangan di daftar booking')
    created_at = models.DateTimeField(auto_now_add=True)

    def delete(self, *args, **kwargs):
        owner = self.owner
        super().delete(*args, **kwargs)
        # Hapus user jika tidak punya field lain
        if not Field.objects.filter(owner=owner).exists():
            owner.delete()

    def __str__(self):
        return self.name

class OperationalHour(models.Model):
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='operational_hours')
    day = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    open_time = models.TimeField()
    close_time = models.TimeField()
    is_closed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.field.name} - {self.day}"

class FieldClosure(models.Model):
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='closures')
    closure_date = models.DateField()
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('field', 'closure_date')
        ordering = ['-closure_date']

    def __str__(self):
        return f"{self.field.name} - {self.closure_date} ({self.reason})"


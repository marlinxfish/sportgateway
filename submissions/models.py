from django.db import models

import os
from django.utils.text import slugify

class FieldSubmission(models.Model):
    FIELD_CATEGORIES = [
        ('futsal', 'Futsal'),
        ('basket', 'Basket'),
        ('badminton', 'Badminton'),
        ('voli', 'Voli'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Menunggu Validasi'),
        ('approved', 'Disetujui'),
        ('rejected', 'Ditolak'),
    ]

    email = models.EmailField()
    username = models.CharField(max_length=50, unique=True, null=True, blank=True, help_text="Username untuk login ke sistem")
    password = models.CharField(max_length=128, null=True, blank=True, help_text="Password untuk login ke sistem (disimpan dalam format hash)")
    name = models.CharField(max_length=100)
    nama_pengelola = models.CharField(max_length=100)
    nik = models.CharField(max_length=20)
    category = models.CharField(max_length=20, choices=FIELD_CATEGORIES)
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    images = models.ImageField(upload_to='field_images/', blank=True, null=True)
    default_price = models.PositiveIntegerField(help_text="Harga per jam dalam Rupiah")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    city = models.CharField(max_length=100, blank=True, null=True)

    agreement_letter = models.FileField(upload_to='documents/')
    ownership_proof = models.FileField(upload_to='documents/')

    def __str__(self):
        return f"{self.name} ({self.category}) - {self.status}"

    def save(self, *args, **kwargs):
        # Rename images
        if self.images and hasattr(self.images, 'name'):
            ext = os.path.splitext(self.images.name)[1]
            new_name = f"{self.category}-{slugify(self.name)}{ext}"
            self.images.name = new_name
        # Rename agreement_letter
        if self.agreement_letter and hasattr(self.agreement_letter, 'name'):
            ext = os.path.splitext(self.agreement_letter.name)[1]
            new_name = f"agreement-{slugify(self.name)}{ext}"
            self.agreement_letter.name = new_name
        # Rename ownership_proof
        if self.ownership_proof and hasattr(self.ownership_proof, 'name'):
            ext = os.path.splitext(self.ownership_proof.name)[1]
            new_name = f"ownership-{slugify(self.name)}{ext}"
            self.ownership_proof.name = new_name
        super().save(*args, **kwargs)


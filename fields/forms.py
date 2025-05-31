from django import forms
from django.forms import modelformset_factory, BaseModelFormSet
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import os

from .models import Field, OperationalHour


def validate_image_extension(value):
    """Validasi ekstensi file gambar"""
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    if ext not in valid_extensions:
        raise ValidationError(
            _('Format file tidak didukung. Gunakan format: {}').format(', '.join(valid_extensions))
        )
    # Batas ukuran file 2MB
    if value.size > 2 * 1024 * 1024:
        raise ValidationError(_('Ukuran file maksimal 2MB'))


class FieldForm(forms.ModelForm):
    """Form untuk menambah/mengedit data lapangan"""
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set placeholder dan class untuk setiap field
        self.fields['name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nama lapangan...'
        })
        self.fields['category'].widget.attrs.update({
            'class': 'form-select',
        })
        self.fields['address'].widget.attrs.update({
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Alamat lengkap lapangan...'
        })
        self.fields['price_per_hour'].widget.attrs.update({
            'class': 'form-control',
            'min': 0,
            'step': '1000',
            'placeholder': 'Contoh: 100000'
        })
        self.fields['image'].widget.attrs.update({
            'class': 'form-control',
            'accept': 'image/*'
        })
        self.fields['is_active'].widget.attrs.update({
            'class': 'form-check-input',
        })
    
    class Meta:
        model = Field
        fields = [
            'name', 'category', 'address', 'latitude', 'longitude', 
            'price_per_hour', 'image', 'is_active'
        ]
        widgets = {
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }
        labels = {
            'is_active': 'Aktifkan Lapangan',
            'price_per_hour': 'Harga per Jam (Rp)'
        }
        help_texts = {
            'is_active': 'Nonaktifkan untuk menyembunyikan lapangan dari daftar booking',
        }

    def clean_price_per_hour(self):
        price = self.cleaned_data.get('price_per_hour')
        if price is not None and price <= 0:
            raise ValidationError('Harga harus lebih besar dari 0')
        return price
        
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            validate_image_extension(image)
        return image
        
    def clean(self):
        cleaned_data = super().clean()
        # Validasi tambahan jika diperlukan
        return cleaned_data


class OperationalHourForm(forms.ModelForm):
    """Form untuk mengatur jam operasional harian"""
    
    def __init__(self, *args, **kwargs):
        self.field_instance = kwargs.pop('field', None)
        super().__init__(*args, **kwargs)
        
        # Set placeholder dan class untuk setiap field
        self.fields['open_time'].widget.attrs.update({
            'class': 'form-control timepicker',
            'placeholder': '08:00',
            'autocomplete': 'off'
        })
        self.fields['close_time'].widget.attrs.update({
            'class': 'form-control timepicker',
            'placeholder': '22:00',
            'autocomplete': 'off'
        })
        self.fields['is_closed'].widget.attrs.update({
            'class': 'form-check-input',
        })
        
        # Set label untuk day
        if self.instance and self.instance.day:
            self.fields['day'].label = self.instance.get_day_display()
    
    class Meta:
        model = OperationalHour
        fields = ('day', 'open_time', 'close_time', 'is_closed')
        widgets = {
            'day': forms.HiddenInput(),
        }
    

    
    def clean(self):
        cleaned_data = super().clean()
        is_closed = cleaned_data.get('is_closed')
        open_time = cleaned_data.get('open_time')
        close_time = cleaned_data.get('close_time')
        
        # Skip validasi jika hari libur
        if is_closed:
            return cleaned_data
            
        # Validasi jam buka dan tutup
        if not open_time:
            self.add_error('open_time', 'Jam buka harus diisi')
        if not close_time:
            self.add_error('close_time', 'Jam tutup harus diisi')
            
        # Validasi jam buka < jam tutup
        if open_time and close_time and open_time >= close_time:
            self.add_error('close_time', 'Jam tutup harus lebih lambat dari jam buka')
        
        return cleaned_data


class BaseOperationalHourFormSet(BaseModelFormSet):
    """Base formset untuk jam operasional"""
    def __init__(self, *args, **kwargs):
        self.field = kwargs.pop('field', None)
        super().__init__(*args, **kwargs)
        self.queryset = self.queryset.order_by('day')
    
    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['field'] = self.field
        return kwargs
        
    def clean(self):
        """Validasi tambahan untuk formset"""
        if any(self.errors):
            return
            
        # Validasi jam operasional tidak tumpang tindih
        days = set()
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
                
            day = form.cleaned_data.get('day')
            if day in days:
                form.add_error('day', 'Hari ini sudah ada dalam daftar')
            days.add(day)


# Buat formset untuk jam operasional
OperationalHourFormSet = modelformset_factory(
    OperationalHour,
    form=OperationalHourForm,
    formset=BaseOperationalHourFormSet,
    fields=('day', 'open_time', 'close_time', 'is_closed'),
    extra=0,
    min_num=7,  # Pastikan ada 7 hari
    validate_min=True,
    can_delete=False,
    max_num=7,  # Maksimal 7 hari
)

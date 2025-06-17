from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from .models import FieldSubmission

User = get_user_model()

class FieldSubmissionForm(forms.ModelForm):
    city = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise forms.ValidationError('Username harus diisi.')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Username ini sudah digunakan. Silakan pilih username lain.')
        return username.lower()  # Simpan username dalam lowercase untuk konsistensi
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError('Email harus diisi.')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Email ini sudah terdaftar. Gunakan email lain atau lakukan reset password.')
        return email.lower()  # Simpan email dalam lowercase
        
    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not password:
            raise forms.ValidationError('Password harus diisi.')
        if len(password) < 8:
            raise forms.ValidationError('Password minimal 8 karakter.')
        return password
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Jangan hash password di sini, biarkan dalam bentuk plaintext
        # karena akan di-hash oleh create_user saat approval
        if commit:
            instance.save()
        return instance
    class Meta:
        model = FieldSubmission
        exclude = ['status']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Buat username untuk login'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Buat password untuk login'}),
            'nama_pengelola': forms.TextInput(attrs={'class': 'form-control'}),
            'nik': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'default_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'images': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'agreement_letter': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'ownership_proof': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


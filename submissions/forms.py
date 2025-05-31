from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from .models import FieldSubmission

User = get_user_model()

class FieldSubmissionForm(forms.ModelForm):
    city = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username ini sudah digunakan. Silakan pilih username lain.')
        return username
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Hash password sebelum disimpan
        if 'password' in self.cleaned_data:
            instance.password = make_password(self.cleaned_data['password'])
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


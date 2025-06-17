from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import (
    UserCreationForm, AuthenticationForm, 
    PasswordChangeForm, SetPasswordForm,
    PasswordResetForm, SetPasswordForm as AuthSetPasswordForm
)
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True, 
        label=_("Email"),
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    username = forms.CharField(
        label=_("Username"),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )

    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'password1', 'password2')
        
    def save(self, commit=True):
        user = super().save(commit=False)
        # Pastikan password di-hash dengan benar
        password = self.cleaned_data["password1"]
        user.set_password(password)
        
        if commit:
            user.save()
            
            # Jika perlu, tambahkan logika tambahan di sini
            # Misalnya mengirim email verifikasi
            
        return user


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'class': 'form-control',
            'placeholder': _('Enter your email address'),
            'autofocus': True
        })
    )
    
    def get_users(self, email):
        """
        Given an email, return matching user(s) who should receive a reset.
        """
        active_users = CustomUser._default_manager.filter(
            email__iexact=email,
            is_active=True
        )
        return (u for u in active_users if u.has_usable_password())

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='accounts/emails/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None, html_email_template_name=None,
             extra_email_context=None):
        """
        Generate a one-use only link for resetting password and send it to the
        user.
        """
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        
        email = self.cleaned_data["email"]
        
        # Debug info
        print("\n=== DEBUG PASSWORD RESET REQUEST ===")
        print(f"Requesting password reset for email: {email}")
        
        for user in self.get_users(email):
            if not domain_override:
                current_site = get_current_site(request)
                site_name = current_site.name
                domain = current_site.domain
            else:
                site_name = domain = domain_override
                
            # Generate token
            token = token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            context = {
                'email': user.email,
                'domain': domain,
                'site_name': site_name,
                'uid': uid,
                'user': user,
                'token': token,
                'protocol': 'https' if use_https else 'http',
                **(extra_email_context or {}),
            }
            
            # Debug info
            print(f"User: {user}")
            print(f"User ID: {user.pk}")
            print(f"Generated UID: {uid}")
            print(f"Generated token: {token}")
            
            # Build reset URL
            reset_url = f"{context['protocol']}://{domain}/auth/password-reset-confirm/{uid}/{token}/"
            print(f"Reset URL: {reset_url}")
            
            # Add reset_url to context
            context['reset_url'] = reset_url
            
            # Render email content
            subject = 'Reset Password - SportGateway'
            email_html_message = render_to_string(
                'accounts/emails/password_reset_email.html',
                context
            )
            
            # Send email
            try:
                send_mail(
                    subject,
                    None,  # No plain text message
                    from_email or settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    html_message=email_html_message,
                    fail_silently=False,
                )
                print(f"Password reset email sent to {user.email}")
            except Exception as e:
                print(f"Error sending password reset email: {str(e)}")
                raise


class CustomSetPasswordForm(AuthSetPasswordForm):
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'class': 'form-control',
            'placeholder': _('Enter new password')
        }),
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'class': 'form-control',
            'placeholder': _('Confirm new password')
        }),
    )
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields['new_password1'].widget.attrs['class'] = 'form-control'
        self.fields['new_password2'].widget.attrs['class'] = 'form-control'


import logging
from django.db import models
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomUser

logger = logging.getLogger(__name__)

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label=_("Username or Email"),
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': _('Enter your username or email'),
            'autofocus': True
        })
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': _('Enter your password'),
            'autocomplete': 'current-password'
        }),
    )
    
    def __init__(self, *args, **kwargs):
        logger.debug("Initializing CustomAuthenticationForm")
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'autofocus': True
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'current-password'
        })
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        logger.debug(f"[CLEAN_USERNAME] Input: {username}")
        
        if not username:
            logger.debug("[CLEAN_USERNAME] Username kosong")
            return username
            
        if '@' in username:
            logger.debug("[CLEAN_USERNAME] Format email terdeteksi, mencari berdasarkan email")
            try:
                user = CustomUser.objects.get(email__iexact=username)
                logger.debug(f"[CLEAN_USERNAME] User ditemukan: {user.username}")
                return user.username
            except CustomUser.DoesNotExist:
                logger.debug(f"[CLEAN_USERNAME] User dengan email {username} tidak ditemukan")
                # Biarkan validasi standar yang menangani
                pass
        
        logger.debug(f"[CLEAN_USERNAME] Menggunakan username asli: {username}")
        return username
        
    def clean(self):
        logger.debug("[CLEAN] Memulai proses validasi form")
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if not username or not password:
            logger.debug("[CLEAN] Username atau password kosong")
            return self.cleaned_data
            
        logger.debug(f"[CLEAN] Mencari user: {username}")
        try:
            # Cari user berdasarkan username atau email
            user = CustomUser.objects.get(
                models.Q(username__iexact=username) | 
                models.Q(email__iexact=username)
            )
            logger.debug(f"[CLEAN] User ditemukan: {user.username}")
            
            # Gunakan authenticate() untuk memverifikasi kredensial
            # Ini akan menangani pengecekan password dan backend auth
            self.user_cache = authenticate(
                self.request,
                username=user.get_username(),
                password=password
            )
            
            if self.user_cache is None:
                logger.debug("[CLEAN] Autentikasi gagal - password salah")
                raise forms.ValidationError(
                    "Kata sandi yang Anda masukkan salah. Periksa kembali.",
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )
                
            logger.debug(f"[CLEAN] Autentikasi berhasil untuk user: {self.user_cache.username}")
            self.confirm_login_allowed(self.user_cache)
            
        except CustomUser.DoesNotExist:
            logger.debug("[CLEAN] User tidak ditemukan")
            # Jangan beri tahu user bahwa username/email tidak ditemukan (security best practice)
            raise forms.ValidationError(
                "Kombinasi username/email dan password tidak valid.",
                code='invalid_login',
                params={'username': self.username_field.verbose_name},
            )
        
        return self.cleaned_data
        
    def confirm_login_allowed(self, user):
        """Controls whether the given User may log in."""
        logger.debug(f"Checking if user can login: {user.username}")
        logger.debug(f"User active: {user.is_active}")
        logger.debug(f"Email verified: {getattr(user, 'is_email_verified', 'N/A')}")
        
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {user.username}")
            raise forms.ValidationError(
                _("This account is inactive."),
                code='inactive',
            )
            
        # Panggil parent untuk validasi standar
        super().confirm_login_allowed(user)
        logger.debug(f"User {user.username} is allowed to login")


class ProfileForm(forms.ModelForm):
    """Form for updating user profile (username and email)"""
    email = forms.EmailField(
        label=_("Email"),
        required=True,
        help_text=_("Enter a valid email address.")
    )
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'profile_image')
        help_texts = {
            'username': _('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exclude(id=self.instance.id).exists():
            raise ValidationError(_("This email is already in use."))
        return email


class CustomPasswordChangeForm(PasswordChangeForm):
    """Custom password change form with better styling and validation"""
    error_messages = {
        **PasswordChangeForm.error_messages,
        'password_incorrect': _("Your old password was entered incorrectly. Please enter it again."),
        'password_mismatch': _("The two password fields didn't match."),
    }
    old_password = forms.CharField(
        label=_("Old password"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'class': 'form-control'}),
    )
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'class': 'form-control',
            'placeholder': _('Enter new password')
        }),
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'class': 'form-control'}),
    )


class EmailVerificationForm(forms.Form):
    """Form for email verification"""
    email = forms.EmailField(
        label=_("Email"),
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not CustomUser.objects.filter(email=email).exists():
            raise ValidationError(_("No account is associated with this email address."))
        return email

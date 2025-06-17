import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth import login, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.views.generic import FormView
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib.auth.views import (
    PasswordResetView as AuthPasswordResetView,
    PasswordResetConfirmView as AuthPasswordResetConfirmView,
    PasswordResetDoneView as AuthPasswordResetDoneView,
    PasswordResetCompleteView as AuthPasswordResetCompleteView,
)

from .models import CustomUser, EmailVerificationToken
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm,
    ProfileForm, CustomPasswordChangeForm, EmailVerificationForm,
    CustomPasswordResetForm, CustomSetPasswordForm
)
from .models import EmailVerificationToken

logger = logging.getLogger(__name__)
User = get_user_model()

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Simpan user dengan password yang sudah di-hash
                user = form.save(commit=False)
                user.role = 'user'
                user.save()
                
                # Send verification email
                try:
                    user.send_verification_email(request)
                    messages.info(
                        request, 
                        _('Registration successful! Please check your email to verify your account.')
                    )
                except Exception as e:
                    logger.error(f"Failed to send verification email: {e}", exc_info=True)
                    messages.warning(
                        request, 
                        _('Account created, but failed to send verification email.')
                    )
                
                # Tidak login otomatis setelah registrasi
                # Arahkan ke halaman login dengan pesan sukses
                # messages.success(
                #     request, 
                #     _('Registration successful! Please login with your credentials.')
                # )
                return redirect('accounts:login')
                
            except Exception as e:
                logger.error(f"Error during user registration: {e}", exc_info=True)
                messages.error(
                    request,
                    _('An error occurred during registration. Please try again.')
                )
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

class CustomLoginView(LoginView):
    authentication_form = CustomAuthenticationForm
    template_name = 'accounts/login.html'

    def form_valid(self, form):
        user = form.get_user()
        
        # Debug: Print informasi user
        print(f"\n=== DEBUG LOGIN ===")
        print(f"User mencoba login: {user.username} (ID: {user.id})")
        print(f"Role: {user.role}")
        print(f"Email verified: {user.is_email_verified}")
        print(f"Is active: {user.is_active}")
        print(f"Is staff: {user.is_staff}")
        print(f"Is superuser: {user.is_superuser}")
        
        # Periksa apakah akun aktif
        if not user.is_active:
            messages.error(self.request, 'Akun ini tidak aktif. Silakan hubungi admin.')
            return self.form_invalid(form)
            
        # Periksa verifikasi email
        if not user.is_email_verified:
            print("Akun belum diverifikasi, mengirim ulang email verifikasi...")
            
            # Kirim ulang email verifikasi jika belum diverifikasi
            try:
                # Gunakan metode send_verification_email yang sudah ada di model
                user.send_verification_email(self.request)
                
                messages.warning(
                    self.request,
                    'Akun Anda belum diverifikasi. Kami telah mengirim ulang email verifikasi. ' +
                    'Silakan periksa email Anda dan ikuti tautan verifikasi.'
                )
                print("Email verifikasi berhasil dikirim ulang")
                
            except Exception as e:
                logger.error(f"Gagal mengirim ulang email verifikasi: {e}", exc_info=True)
                messages.error(
                    self.request,
                    'Gagal mengirim ulang email verifikasi. Silakan coba lagi nanti atau hubungi admin.'
                )
            return self.form_invalid(form)
        
        # Jika semua valid, lanjutkan login
        print("Login berhasil, mengarahkan ke dashboard...")
        return super().form_valid(form)
    
    def get_success_url(self):
        # Setelah login berhasil, arahkan ke halaman yang sesuai
        user = self.request.user
        if user.is_superuser:
            return '/admin/'
        elif user.role == 'manager':
            return '/manager/dashboard/'
        elif user.role == 'user':
            return '/booking/'
        return '/'

@login_required
def profile_view(request):
    """View for user profile management"""
    if request.method == 'POST':
        form = ProfileForm(
            request.POST,
            request.FILES,
            instance=request.user
        )
        if form.is_valid():
            user = form.save(commit=False)
            email_changed = 'email' in form.changed_data
            
            if email_changed:
                # If email changed, require verification
                user.is_email_verified = False
                try:
                    user.send_verification_email(request)
                    messages.info(
                        request,
                        _('Profile updated! A verification email has been sent to your new email address.')
                    )
                except Exception as e:
                    logger.error(f"Failed to send verification email: {e}", exc_info=True)
                    messages.error(
                        request,
                        _('Profile updated, but failed to send verification email. Please try again later.')
                    )
            else:
                messages.success(request, _('Profile updated successfully!'))
            
            user.save()
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)
    
    return render(request, 'accounts/profile.html', {
        'form': form,
        'password_form': CustomPasswordChangeForm(user=request.user),
    })

@login_required
@require_POST
def change_password_view(request):
    """Handle password change"""
    form = CustomPasswordChangeForm(user=request.user, data=request.POST)
    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)  # Keep the user logged in
        messages.success(request, _('Your password was successfully updated!'))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
    
    return redirect('accounts:profile')

from django.contrib.auth import login as auth_login
from django.contrib.auth.views import PasswordResetConfirmView as AuthPasswordResetConfirmView
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy

User = get_user_model()

class CustomPasswordResetConfirmView(FormView):
    template_name = 'accounts/password_reset_confirm.html'
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy('accounts:password_reset_complete')
    token_generator = default_token_generator
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user = None
        self.validlink = False
        self._request = None
        self._token = None
        self._uidb64 = None

    def dispatch(self, request, *args, **kwargs):
        self._request = request
        self._uidb64 = kwargs.get('uidb64')
        self._token = kwargs.get('token')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not self._uidb64 or not self._token:
            return self.invalid_link_response()
            
        self.user = self.get_user(self._uidb64)
        
        if not self.user or not self.token_generator.check_token(self.user, self._token):
            return self.invalid_link_response()
            
        self.validlink = True
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        # Handle case when form is submitted without token in URL
        if not self._uidb64 or not self._token:
            return self.invalid_link_response()
            
        # Get user from URL parameters
        self.user = self.get_user(self._uidb64)
        
        # Verify token
        if not self.user or not self.token_generator.check_token(self.user, self._token):
            return self.invalid_link_response()
        
        # Process the form
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
    
    def invalid_link_response(self):
        self.validlink = False
        messages.error(self._request, 'Link reset password tidak valid, sudah kadaluarsa, atau sudah digunakan. Silakan minta link reset password baru.')
        return self.render_to_response(self.get_context_data())

    def get_user(self, uidb64):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            print(f"Decoded UID: {uid}")
            user = User._default_manager.get(pk=uid)
            print(f"Found user: {user}")
            return user
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, ValidationError) as e:
            print(f"Error getting user: {str(e)}")
            return None
            
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.user
        return kwargs
        
    def form_valid(self, form):
        try:
            # Set new password
            self.user.set_password(form.cleaned_data['new_password1'])
            self.user.save()
            
            # Show success message
            messages.success(self._request, 'Password Anda telah berhasil direset. Silakan masuk dengan password baru Anda.')
            
            return super().form_valid(form)
            
        except Exception as e:
            print(f"Error in form_valid: {str(e)}")
            messages.error(self._request, 'Terjadi kesalahan saat menyimpan password baru. Silakan coba lagi.')
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['validlink'] = self.validlink
        return context


def verify_email(request, token):
    """
    View untuk memverifikasi email pengguna berdasarkan token
    """
    print(f"\n=== DEBUG VERIFIKASI EMAIL ===")
    print(f"Token diterima: {token}")
    
    try:
        # Debug: Cek token di database
        print(f"Mencari token di database...")
        verification = EmailVerificationToken.objects.get(token=token, is_used=False)
        print(f"Token ditemukan: ID={verification.id}")
        print(f"User: {verification.user.username} (ID: {verification.user.id})")
        print(f"Email: {verification.user.email}")
        print(f"Dibuat pada: {verification.created_at}")
        print(f"Status: {'Sudah digunakan' if verification.is_used else 'Belum digunakan'}")
        print(f"Valid: 'Ya' if verification.is_valid() else 'Tidak'")
        
        # Cek apakah token masih valid (belum digunakan dan belum kadaluarsa)
        if not verification.is_valid():
            print("Token sudah digunakan atau kadaluarsa")
            return render(request, 'accounts/verification_failed.html', {
                'title': 'Verifikasi Gagal',
                'message': 'Link verifikasi sudah digunakan atau kadaluarsa.',
                'solution': 'Silakan hubungi admin untuk mendapatkan link verifikasi baru.'
            })
        
        # Verifikasi email
        user = verification.user
        print(f"Memverifikasi user: {user.username} (ID: {user.id})")
        
        user.is_email_verified = True
        user.save()
        print("Status verifikasi email diupdate")
        
        # Tandai token sudah digunakan
        verification.is_used = True
        verification.used_at = timezone.now()
        verification.save()
        print("Token ditandai sudah digunakan")
        
        # Login otomatis setelah verifikasi
        try:
            auth_login(request, user)
            print("User berhasil login")
            # Langsung redirect ke halaman beranda setelah login
            return redirect('pages:home')
        except Exception as e:
            print(f"Gagal login otomatis: {str(e)}")
            # Jika gagal login, tetap tampilkan halaman sukses dengan tombol ke beranda
            return render(request, 'accounts/verification_success.html', {
                'title': 'Verifikasi Berhasil',
                'message': 'Email Anda berhasil diverifikasi!',
                'redirect_url': reverse_lazy('pages:home'),
                'redirect_text': 'Ke Beranda'
            })
        
        # Kode ini seharusnya tidak pernah tercapai karena sudah ada return di atas
        return redirect('pages:home')
        
    except EmailVerificationToken.DoesNotExist:
        print("Token tidak ditemukan atau sudah digunakan")
        # Cek apakah token ada tapi sudah digunakan
        try:
            used_token = EmailVerificationToken.objects.get(token=token)
            print(f"Token ditemukan tapi sudah digunakan pada: {used_token.used_at}")
            message = 'Link verifikasi sudah pernah digunakan sebelumnya.'
        except EmailVerificationToken.DoesNotExist:
            print("Token benar-benar tidak ada di database")
            message = 'Link verifikasi tidak valid.'
            
        return render(request, 'accounts/verification_failed.html', {
            'title': 'Verifikasi Gagal',
            'message': message,
            'solution': 'Jika Anda yakin belum melakukan verifikasi, silakan coba login untuk mengirim ulang email verifikasi.'
        })
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"\n=== ERROR VERIFIKASI ===")
        print(f"Tipe Error: {type(e).__name__}")
        print(f"Pesan Error: {str(e)}")
        print(f"Traceback:\n{error_traceback}")
        print("=========================\n")
        
        return render(request, 'accounts/verification_failed.html', {
            'title': 'Terjadi Kesalahan',
            'message': f'Terjadi kesalahan saat memproses verifikasi: {str(e)}',
            'solution': 'Silakan coba beberapa saat lagi atau hubungi admin.'
        })

@login_required
def resend_verification_view(request):
    """Resend verification email"""
    if request.method == 'POST':
        form = EmailVerificationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                if user.is_email_verified:
                    messages.info(request, _('This email is already verified.'))
                    return redirect('accounts:login')
                
                user.send_verification_email(request)
                messages.success(
                    request,
                    _('Verification email has been resent. Please check your inbox.')
                )
                return redirect('accounts:login')
            except User.DoesNotExist:
                messages.error(request, _('No account found with this email.'))
    else:
        form = EmailVerificationForm(initial={'email': request.user.email if request.user.is_authenticated else ''})
    
    return render(request, 'accounts/resend_verification.html', {'form': form})

@require_http_methods(["POST"])
def custom_logout(request):
    """Handle user logout with POST method only"""
    if request.method == 'POST':
        logout(request)
        messages.success(request, _('You have been successfully logged out.'))
        return redirect('pages:home')
    return HttpResponseNotAllowed(['POST'], 'Method not allowed')


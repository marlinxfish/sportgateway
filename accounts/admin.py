from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import action
from .models import CustomUser
import secrets
import string
from django.core.mail import send_mail
from django.contrib import messages

@admin.register(CustomUser)
class CustomUserAdmin(ModelAdmin):
    list_display = ('username', 'email', 'role')  # Tampilkan kolom utama
    @action(
        description="Reset password & kirim ke email (khusus manager)",
        permissions=["auth.change_user"]
    )
    def reset_password_and_email(self, request, queryset):
        for user in queryset:
            if hasattr(user, 'role') and user.role == 'manager' and user.email:
                new_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
                user.set_password(new_password)
                user.save()
                send_mail(
                    subject="Password Baru Akun Manager",
                    message=f"Halo {user.username},\n\nPassword akun Anda telah direset oleh admin.\n\nPassword baru: {new_password}\n\nSilakan login dan segera ganti password Anda.",
                    from_email=None,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
        self.message_user(request, "Password berhasil direset dan dikirim ke email manager terpilih.", messages.SUCCESS)

    def has_reset_password_and_email_permission(self, request, obj=None):
        return request.user.is_superuser
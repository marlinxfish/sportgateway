from django.contrib import admin
from .models import FieldSubmission
from django.utils.html import format_html
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.shortcuts import redirect
from fields.models import Field
from fields.utils import create_default_operational_hours

User = get_user_model()

@admin.register(FieldSubmission)
class FieldSubmissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'category', 'status', 'created_at', 'action_buttons')

    def action_buttons(self, obj):
        if obj.status == 'pending':
            return format_html(
                '<a class="button" href="approve/{}/">✔️ Setujui</a>&nbsp;'
                '<a class="button" href="reject/{}/">❌ Tolak</a>',
                obj.pk, obj.pk
            )
        return '—'
    action_buttons.short_description = 'Aksi'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('approve/<int:pk>/', self.admin_site.admin_view(self.approve_submission), name='approve_submission'),
            path('reject/<int:pk>/', self.admin_site.admin_view(self.reject_submission), name='reject_submission'),
        ]
        return custom_urls + urls

    def approve_submission(self, request, pk):
        submission = FieldSubmission.objects.get(pk=pk)
        if submission.status != 'pending':
            self.message_user(request, "Pengajuan ini sudah diproses.")
            return redirect("..")

        # 1. Buat akun manager dengan username dan password dari form
        try:
            # Cek apakah username sudah digunakan
            if User.objects.filter(username=submission.username).exists():
                self.message_user(request, f"Username {submission.username} sudah digunakan. Silakan gunakan username lain.", level='error')
                return redirect("..")
                
            # Cek apakah email sudah digunakan
            if User.objects.filter(email=submission.email).exists():
                self.message_user(request, f"Email {submission.email} sudah terdaftar. Silakan gunakan email lain.", level='error')
                return redirect("..")
            
            # Buat user baru dengan password yang benar-benar di-hash
            try:
                print(f"Membuat user baru dengan username: {submission.username}")
                print(f"Password sebelum create_user: {submission.password}")
                
                user = User.objects.create_user(
                    username=submission.username,
                    email=submission.email,
                    password=submission.password,  # Akan di-hash otomatis oleh create_user
                    role='manager',
                    first_name=submission.nama_pengelola,
                    is_email_verified=False,  # Manager harus verifikasi email terlebih dahulu
                    is_active=True  # Pastikan akun aktif
                )
                
                print(f"User {user.username} berhasil dibuat dengan ID {user.id}")
                print(f"Email: {user.email}")
                print(f"Role: {user.role}")
                print(f"Status aktif: {user.is_active}")
                print(f"Password hash: {user.password}")
                
            except Exception as e:
                import traceback
                print(f"Error saat membuat user: {str(e)}")
                print(traceback.format_exc())
                self.message_user(request, f"Gagal membuat akun manager: {str(e)}", level='error')
                return redirect("..")
            
            # Debug info
            print(f"User {user.username} berhasil dibuat dengan ID {user.id}")
            print(f"Email: {user.email}")
            print(f"Role: {user.role}")
            print(f"Status aktif: {user.is_active}")
            
        except Exception as e:
            self.message_user(request, f"Gagal membuat akun manager: {str(e)}", level='error')
            return redirect("..")
        
        # Buat token verifikasi email
        from accounts.models import EmailVerificationToken
        verification_token = EmailVerificationToken.objects.create(user=user)
        verification_url = f"http://localhost:8000/auth/verify-email/{verification_token.token}/"

        # 2. Buat objek Field dan simpan ke variabel
        field = Field.objects.create(
            owner=user,
            name=submission.name,
            category=submission.category,
            address=submission.address,
            latitude=submission.latitude,
            longitude=submission.longitude,
            price_per_hour=submission.default_price,
            image=submission.images  # jika ada
        )

        # 3. Buat jam operasional default untuk field tsb
        from fields.utils import create_default_operational_hours
        create_default_operational_hours(field)

        # 4. Update status pengajuan
        submission.status = 'approved'
        submission.save()

        # 5. Kirim email dengan template HTML
        from django.template.loader import render_to_string
        from django.core.mail import EmailMultiAlternatives
        from django.conf import settings
        
        # Render template email
        email_context = {
            'user': user,
            'site_name': 'SportGateway',
            'verification_url': verification_url
        }
        print(f"Email context: {email_context}")  # Debug
        email_html_message = render_to_string('accounts/emails/manager_approval_email.html', email_context)
        
        # Buat dan kirim email
        subject = "Pengajuan Lapangan Anda Disetujui"
        from_email = settings.DEFAULT_FROM_EMAIL or 'noreply@example.com'
        to_email = submission.email
        
        # Kirim email dengan template HTML
        try:
            print(f"Mencoba mengirim email ke: {to_email}")
            print(f"Dari: {from_email}")
            print(f"Subjek: {subject}")
            
            email = EmailMultiAlternatives(
                subject=subject,
                body="""
                Halo,
                
                Pengajuan lapangan Anda telah disetujui. 
                Silakan periksa email ini dalam format HTML untuk detail lebih lanjut.
                
                Terima kasih,
                Tim SportGateway
                """,
                from_email=from_email,
                to=[to_email]
            )
            email.attach_alternative(email_html_message, "text/html")
            
            # Test koneksi email
            import smtplib
            try:
                with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                    server.ehlo()
                    if settings.EMAIL_USE_TLS:
                        server.starttls()
                    print(f"Berhasil terhubung ke server SMTP {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
            except Exception as e:
                print(f"Gagal terhubung ke server SMTP: {e}")
            
            # Coba kirim email
            result = email.send(fail_silently=False)
            print(f"Email berhasil dikirim ke {to_email}. Response: {result}")
            
        except Exception as e:
            import traceback
            print(f"Gagal mengirim email ke {to_email}")
            print(f"Error details: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")

        self.message_user(request, "Pengajuan disetujui, akun manager dibuat, dan lapangan ditambahkan.")
        return redirect("../../")

    
    def reject_submission(self, request, pk):
        submission = FieldSubmission.objects.get(pk=pk)
        if submission.status != 'pending':
            self.message_user(request, "Pengajuan ini sudah diproses.")
            return redirect("..")

        submission.status = 'rejected'
        submission.save()

        send_mail(
            subject="Pengajuan Lapangan Anda Ditolak",
            message=f"""Halo {submission.nama_pengelola},

Maaf, pengajuan lapangan Anda ditolak oleh tim SportGateway.

Silakan hubungi admin jika ada pertanyaan lebih lanjut.

Terima kasih,
Tim SportGateway
""",
            from_email=None,
            recipient_list=[submission.email],
            fail_silently=False,
        )

        self.message_user(request, "Pengajuan ditolak dan notifikasi dikirim.")
        return redirect("../../")

import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('manager', 'Manager'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    profile_image = models.ImageField(upload_to='profile/', blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    email = models.EmailField(unique=True, blank=False, null=False)

    def __str__(self):
        return self.username
    
    def send_verification_email(self, request):
        """Generate and send verification email"""
        from .models import EmailVerificationToken
        
        # Invalidate old tokens
        EmailVerificationToken.objects.filter(user=self, is_used=False).update(is_used=True)
        
        # Create new token
        token = EmailVerificationToken.objects.create(user=self)
        
        # Build verification URL
        verification_url = request.build_absolute_uri(
            reverse('accounts:verify_email', kwargs={'token': str(token.token)})
        )
        
        # Prepare email
        subject = 'Verifikasi Email Anda - Sport Gateway'
        context = {
            'user': self,
            'verification_url': verification_url,
        }
        
        # Render email templates
        html_message = render_to_string('accounts/emails/verification_email.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.email],
            html_message=html_message,
        )


class EmailVerificationToken(models.Model):
    """Model to store email verification tokens"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.token}"
    
    def is_valid(self):
        """Check if token is valid (not used and not expired)"""
        if self.is_used:
            return False
        
        # Token expires after 24 hours
        expiration_time = self.created_at + timezone.timedelta(hours=24)
        return timezone.now() <= expiration_time

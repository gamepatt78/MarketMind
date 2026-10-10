from datetime import date

from django.db import models
from django.conf import settings


class ContactAccount(models.Model):
    CHANNEL_EMAIL = "email"
    CHANNEL_PHONE = "phone"
    CHANNEL_CHOICES = (
        (CHANNEL_EMAIL, "Email"),
        (CHANNEL_PHONE, "Phone"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stock_contact",
    )
    identifier = models.CharField(max_length=254, unique=True)
    channel = models.CharField(max_length=8, choices=CHANNEL_CHOICES)
    full_name = models.CharField(max_length=120, blank=True, default="")
    birth_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def age(self):
        if self.birth_date is None:
            return None
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )

    def __str__(self):
        return self.identifier


class LoginOTP(models.Model):
    PURPOSE_REGISTER = "register"
    PURPOSE_LOGIN = "login"
    PURPOSE_PASSWORD_RESET = "password_reset"
    PURPOSE_CHOICES = (
        (PURPOSE_REGISTER, "Registration"),
        (PURPOSE_LOGIN, "Login"),
        (PURPOSE_PASSWORD_RESET, "Password reset"),
    )

    identifier = models.CharField(max_length=254, db_index=True)
    purpose = models.CharField(max_length=16, choices=PURPOSE_CHOICES)
    code_hash = models.CharField(max_length=128)
    pending_username = models.CharField(max_length=150, blank=True)
    pending_full_name = models.CharField(max_length=120, blank=True)
    pending_birth_date = models.DateField(null=True, blank=True)
    pending_password_hash = models.CharField(max_length=128, blank=True)
    pending_email = models.EmailField(blank=True, default="")
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=("identifier", "purpose", "-created_at")),
        ]

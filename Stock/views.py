import logging
import re
import secrets
import smtplib
import time
import unicodedata
from datetime import datetime, timedelta

import requests
from django.contrib.auth import authenticate, get_user_model, login, logout, password_validation
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone as django_timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from Stock.backend.stockinfo import *
from Stock.models import ContactAccount, LoginOTP

# Defer heavy ML imports to runtime to avoid import-time errors
# (tensorflow, seaborn, etc. may not be available during setup)
# Create your views here.

logger = logging.getLogger(__name__)
OTP_TTL_MINUTES = 5
OTP_RESEND_SECONDS = 60
OTP_MAX_SENDS_PER_HOUR = 5
OTP_MAX_ATTEMPTS = 5


def _normalize_contact(value):
    value = (value or "").strip()
    if "@" in value:
        value = value.lower()
        try:
            validate_email(value)
        except ValidationError:
            return None, None
        return value, ContactAccount.CHANNEL_EMAIL

    phone = re.sub(r"[\s()-]", "", value)
    if phone.isdigit() and len(phone) == 10:
        phone = "+91" + phone
    elif phone.isdigit() and len(phone) == 12 and phone.startswith("91"):
        phone = "+" + phone
    if not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
        return None, None
    return phone, ContactAccount.CHANNEL_PHONE


def _normalize_username(value):
    return "".join(
        character
        for character in (value or "")
        if unicodedata.category(character) != "Cf"
    ).strip()


def _deliver_otp(identifier, channel, code):
    message = "Your Stock Market AI verification code is {}. It expires in 5 minutes.".format(code)
    if channel == ContactAccount.CHANNEL_EMAIL:
        if not (settings.EMAIL_HOST and settings.DEFAULT_FROM_EMAIL):
            raise RuntimeError("Email OTP is not configured. Set the SMTP environment variables.")
        send_mail(
            "Your Stock Market AI verification code",
            message,
            settings.DEFAULT_FROM_EMAIL,
            [identifier],
            fail_silently=False,
        )
        return

    if not (
        settings.TWILIO_ACCOUNT_SID
        and settings.TWILIO_AUTH_TOKEN
        and settings.TWILIO_FROM_PHONE
    ):
        raise RuntimeError("SMS OTP is not configured. Set the Twilio environment variables.")
    response = requests.post(
        "https://api.twilio.com/2010-04-01/Accounts/{}/Messages.json".format(
            settings.TWILIO_ACCOUNT_SID
        ),
        data={"To": identifier, "From": settings.TWILIO_FROM_PHONE, "Body": message},
        auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
        timeout=15,
    )
    response.raise_for_status()


def login_page(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect("/")
    error = ""
    if request.method == "POST":
        username = _normalize_username(request.POST.get("username"))
        password = request.POST.get("password") or ""
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.POST.get("next") or request.GET.get("next", "")
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return HttpResponseRedirect(next_url)
            return HttpResponseRedirect("/")
        error = "The username or password is incorrect."

    return render(request, "auth.html", {
        "mode": "login",
        "registered": request.GET.get("registered") == "1",
        "password_reset": request.GET.get("password_reset") == "1",
        "error": error,
        "next": request.POST.get("next") or request.GET.get("next", ""),
    })


def register_page(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect("/")
    return render(request, "auth.html", {"mode": "register"})


def forgot_password_page(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect("/")
    return render(request, "auth.html", {"mode": "forgot_password"})


@require_POST
def send_password_reset_otp(request):
    email, channel = _normalize_contact(request.POST.get("email"))
    if not email or channel != ContactAccount.CHANNEL_EMAIL:
        return JsonResponse({"error": "Enter a valid email address."}, status=400)

    response_data = {
        "sent": True,
        "message": "If an account uses that email, a password reset code has been sent.",
    }
    account = ContactAccount.objects.select_related("user").filter(
        identifier=email,
        channel=ContactAccount.CHANNEL_EMAIL,
        user__is_active=True,
    ).first()
    if account is None:
        return JsonResponse(response_data)

    now = django_timezone.now()
    recent = LoginOTP.objects.filter(
        identifier=email,
        purpose=LoginOTP.PURPOSE_PASSWORD_RESET,
        created_at__gte=now - timedelta(hours=1),
    )
    if recent.count() >= OTP_MAX_SENDS_PER_HOUR:
        return JsonResponse(
            {"error": "Too many code requests. Try again in an hour."},
            status=429,
        )
    latest = recent.order_by("-created_at").first()
    if latest and latest.created_at > now - timedelta(seconds=OTP_RESEND_SECONDS):
        return JsonResponse(
            {"error": "Please wait a minute before requesting another code."},
            status=429,
        )

    code = "{:06d}".format(secrets.randbelow(1000000))
    otp = LoginOTP.objects.create(
        identifier=email,
        purpose=LoginOTP.PURPOSE_PASSWORD_RESET,
        code_hash=make_password(code),
        expires_at=now + timedelta(minutes=OTP_TTL_MINUTES),
    )
    try:
        _deliver_otp(email, ContactAccount.CHANNEL_EMAIL, code)
    except (RuntimeError, requests.RequestException, OSError, smtplib.SMTPException) as error:
        logger.warning("Password reset email delivery failed: %s", error)
        otp.delete()
        return JsonResponse(
            {"error": "Password reset email could not be sent. Check the email service and try again."},
            status=503,
        )
    return JsonResponse(response_data)


@require_POST
def reset_password_with_otp(request):
    email, channel = _normalize_contact(request.POST.get("email"))
    code = (request.POST.get("code") or "").strip()
    password = request.POST.get("password") or ""
    password_confirm = request.POST.get("password_confirm") or ""
    if not email or channel != ContactAccount.CHANNEL_EMAIL:
        return JsonResponse({"error": "Enter a valid email address."}, status=400)
    if not re.fullmatch(r"\d{6}", code):
        return JsonResponse({"error": "Enter the six-digit email verification code."}, status=400)
    if password != password_confirm:
        return JsonResponse({"error": "The passwords do not match."}, status=400)

    account = ContactAccount.objects.select_related("user").filter(
        identifier=email,
        channel=ContactAccount.CHANNEL_EMAIL,
        user__is_active=True,
    ).first()
    if account is None:
        return JsonResponse({"error": "The code is invalid or expired. Request a new code."}, status=400)
    try:
        password_validation.validate_password(password, account.user)
    except ValidationError as error:
        return JsonResponse({"error": " ".join(error.messages)}, status=400)

    with transaction.atomic():
        otp = LoginOTP.objects.select_for_update().filter(
            identifier=email,
            purpose=LoginOTP.PURPOSE_PASSWORD_RESET,
            expires_at__gt=django_timezone.now(),
            attempts__lt=OTP_MAX_ATTEMPTS,
        ).order_by("-created_at").first()
        if otp is None or not check_password(code, otp.code_hash):
            if otp is not None:
                otp.attempts += 1
                otp.save(update_fields=("attempts",))
            return JsonResponse({"error": "The code is invalid or expired. Request a new code."}, status=400)
        user = get_user_model()._default_manager.select_for_update().get(pk=account.user_id)
        user.set_password(password)
        user.save(update_fields=("password",))
        LoginOTP.objects.filter(
            identifier=email,
            purpose=LoginOTP.PURPOSE_PASSWORD_RESET,
        ).delete()

    return JsonResponse({
        "reset": True,
        "redirect_url": reverse("login") + "?password_reset=1",
        "message": "Your password was changed successfully. Log in with your new password.",
    })


@require_POST
def send_registration_otp(request):
    email, email_channel = _normalize_contact(request.POST.get("email"))
    phone, phone_channel = _normalize_contact(request.POST.get("phone"))
    username = _normalize_username(request.POST.get("username"))
    full_name = " ".join((request.POST.get("full_name") or "").split())
    password = request.POST.get("password") or ""
    password_confirm = request.POST.get("password_confirm") or ""
    birth_date_value = request.POST.get("birth_date") or ""
    if request.POST.get("email", "").strip() and (
        not email or email_channel != ContactAccount.CHANNEL_EMAIL
    ):
        return JsonResponse({"error": "Enter a valid email address or leave it blank."}, status=400)
    if not phone or phone_channel != ContactAccount.CHANNEL_PHONE:
        return JsonResponse({"error": "Enter a valid phone number."}, status=400)
    if not username or len(username) > 150 or not re.fullmatch(r"[\w.@+-]+", username):
        return JsonResponse({"error": "Enter a username using letters, numbers, and @ . + - _."}, status=400)
    if len(full_name) < 2 or len(full_name) > 120:
        return JsonResponse({"error": "Enter your full name (up to 120 characters)."}, status=400)
    if password != password_confirm:
        return JsonResponse({"error": "The passwords do not match."}, status=400)
    User = get_user_model()
    if User._default_manager.filter(username__iexact=username).exists():
        return JsonResponse({"error": "That username is already taken."}, status=409)
    try:
        birth_date = datetime.strptime(birth_date_value, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "Enter a valid date of birth."}, status=400)
    if birth_date >= django_timezone.localdate():
        return JsonResponse({"error": "Date of birth must be in the past."}, status=400)
    candidate_user = User(username=username, email=email)
    try:
        password_validation.validate_password(password, candidate_user)
    except ValidationError as error:
        return JsonResponse({"error": " ".join(error.messages)}, status=400)
    if ContactAccount.objects.filter(identifier=phone).exists():
        return JsonResponse(
            {"error": "An account already uses this phone. Please log in instead."},
            status=409,
        )
    now = django_timezone.now()
    recent = LoginOTP.objects.filter(
        identifier=phone,
        purpose=LoginOTP.PURPOSE_REGISTER,
        created_at__gte=now - timedelta(hours=1),
    )
    if recent.count() >= OTP_MAX_SENDS_PER_HOUR:
        return JsonResponse(
            {"error": "Too many code requests. Try again in an hour."},
            status=429,
        )
    latest = recent.order_by("-created_at").first()
    if latest and latest.created_at > now - timedelta(seconds=OTP_RESEND_SECONDS):
        return JsonResponse(
            {"error": "Please wait a minute before requesting another code."},
            status=429,
        )
    code = "{:06d}".format(secrets.randbelow(1000000))

    with transaction.atomic():
        LoginOTP.objects.filter(
            identifier=phone,
            purpose=LoginOTP.PURPOSE_REGISTER,
        ).delete()
        LoginOTP.objects.create(
            identifier=phone,
            purpose=LoginOTP.PURPOSE_REGISTER,
            code_hash=make_password(code),
            pending_username=username,
            pending_full_name=full_name,
            pending_birth_date=birth_date,
            pending_password_hash=make_password(password),
            pending_email=email or "",
            expires_at=now + timedelta(minutes=OTP_TTL_MINUTES),
        )

    try:
        _deliver_otp(phone, ContactAccount.CHANNEL_PHONE, code)
    except (RuntimeError, requests.RequestException, OSError, smtplib.SMTPException) as error:
        logger.warning("Registration SMS delivery failed: %s", error)
        LoginOTP.objects.filter(
            identifier=phone,
            purpose=LoginOTP.PURPOSE_REGISTER,
        ).delete()
        return JsonResponse(
            {"error": "SMS OTP delivery is unavailable. Check the configured Twilio service and try again."},
            status=503,
        )
    return JsonResponse({
        "sent": True,
        "message": "A six-digit verification code was sent to your phone by SMS.",
    })


@require_POST
def verify_registration_otp(request):
    phone, phone_channel = _normalize_contact(request.POST.get("phone"))
    if (
        not phone
        or phone_channel != ContactAccount.CHANNEL_PHONE
        or not re.fullmatch(r"\d{6}", (request.POST.get("phone_code") or "").strip())
    ):
        return JsonResponse({"error": "Enter the phone number and its six-digit verification code."}, status=400)

    User = get_user_model()
    try:
        with transaction.atomic():
            otp = LoginOTP.objects.select_for_update().filter(
                identifier=phone,
                purpose=LoginOTP.PURPOSE_REGISTER,
                expires_at__gt=django_timezone.now(),
                attempts__lt=OTP_MAX_ATTEMPTS,
            ).order_by("-created_at").first()
            phone_code = (request.POST.get("phone_code") or "").strip()
            if otp is None or not check_password(phone_code, otp.code_hash):
                if otp is not None:
                    otp.attempts += 1
                    otp.save(update_fields=("attempts",))
                return JsonResponse({"error": "The code is invalid or expired. Request a new code."}, status=400)
            if ContactAccount.objects.filter(identifier=phone).exists():
                return JsonResponse({"error": "An account already uses this phone. Please log in."}, status=409)
            if not otp.pending_username or not otp.pending_birth_date or not otp.pending_password_hash:
                return JsonResponse({"error": "Registration details are missing. Please register again."}, status=400)
            if otp.pending_birth_date >= django_timezone.localdate():
                return JsonResponse({"error": "Date of birth must be in the past. Please register again."}, status=400)
            if User._default_manager.filter(username__iexact=otp.pending_username).exists():
                return JsonResponse({"error": "That username is no longer available. Please register again."}, status=409)
            user = User(
                username=otp.pending_username,
                email=otp.pending_email,
                first_name=otp.pending_full_name[:150],
            )
            user.password = otp.pending_password_hash
            user.save()
            ContactAccount.objects.create(
                user=user,
                identifier=phone,
                channel=ContactAccount.CHANNEL_PHONE,
                full_name=otp.pending_full_name,
                birth_date=otp.pending_birth_date,
            )
            otp.delete()
    except IntegrityError:
        return JsonResponse({"error": "An account already uses this phone. Please log in."}, status=409)

    return JsonResponse({"registered": True, "redirect_url": reverse("login") + "?registered=1"})


@require_POST
@require_POST
def logout_user(request):
    logout(request)
    return HttpResponseRedirect(reverse("login"))


def index(request):
    return render(request, "index.html")

def stock(request):
    data = None
    stock = None
    error = ""
    if request.method == "POST":
        sym = request.POST.get("symbol", "").strip().upper()
        if sym not in supported_symbol_tickers:
            return render(
                request,
                "stock.html",
                {
                    "data": None,
                    "symbols": supported_symbols,
                    "stock": None,
                    "error": "Choose a ticker from the symbol list.",
                },
                status=400,
            )
        time = request.POST.get("period", "1d")
        if time not in supported_periods:
            return render(
                request,
                "stock.html",
                {
                    "data": None,
                    "symbols": supported_symbols,
                    "stock": None,
                    "error": "Choose one of the available time periods.",
                },
                status=400,
            )
        if time == "1d":
            data = stock_today(sym)
        else:
            data = get_stock(sym, time)
        stock = get_info(sym)
        if data is None:
            error = (
                "Market data is temporarily unavailable for this stock and period. "
                "Please try again later."
            )
    context = {
        "data": data,
        "symbols": supported_symbols,
        "stock": stock,
        "error": error,
    }
    return render(request, "stock.html", context)

def stock_predict(request, symbol, period, sim, future):
    symbol = symbol.upper()
    if symbol not in supported_symbol_tickers:
        return JsonResponse(
            {"error": "Choose a ticker from the symbol list."},
            status=400,
        )
    if period not in supported_periods or not 1 <= sim <= 10 or not 30 <= future <= 365:
        return JsonResponse(
            {"error": "Select an available period, 1–10 simulations, and 30–365 forecast days."},
            status=400,
        )
    # import here to avoid importing tensorflow at module import time
    from Stock.backend.predict import predict_stock
    try:
        data = predict_stock(symbol, period, sim, future)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse({"data": data})

def predict(request):
    data = None
    sym = ""
    if request.method == "POST":
        sym = request.POST.get("symbol", "").strip().upper()
        if sym not in supported_symbol_tickers:
            return JsonResponse(
                {"error": "Choose a ticker from the symbol list."},
                status=400,
            )
        if request.POST.get("period", "6mo") not in supported_periods:
            return JsonResponse({"error": "Choose one of the available time periods."}, status=400)
        data = request.POST["plot"]
    
    context = {
        "symbols": supported_symbols,
        "data": data,
        "sym": sym
    }
    return render(request, "predict.html", context)

def stock_trade(request, symbol, period, init, skip):
    symbol = symbol.upper()
    if symbol not in supported_symbol_tickers:
        return JsonResponse(
            {"error": "Choose a ticker from the symbol list."},
            status=400,
        )
    if period not in supported_periods or not 1 <= init <= 100000 or not 0 <= skip <= 10:
        return JsonResponse(
            {"error": "Select an available period, a balance from $1 to $100,000, and a delay of 0–10 days."},
            status=400,
        )
    # import here to avoid importing tensorflow/other heavy libs at import time
    from Stock.backend.trade import trade_stock
    try:
        data = trade_stock(symbol, period, init, skip)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse({"data": data})

def trade(request):
    data = None
    sym = ""
    if request.method == "POST":
        sym = request.POST.get("symbol", "").strip().upper()
        if sym not in supported_symbol_tickers:
            return JsonResponse(
                {"error": "Choose a ticker from the symbol list."},
                status=400,
            )
        if request.POST.get("period", "6mo") not in supported_periods:
            return JsonResponse({"error": "Choose one of the available time periods."}, status=400)
        data = request.POST["plot"]

    context = {
        "symbols": supported_symbols,
        "data": data,
        "sym": sym
    }
    return render(request, "trade.html", context)
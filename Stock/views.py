import re
import time
import unicodedata
from datetime import datetime

from django.contrib.auth import authenticate, get_user_model, login, logout, password_validation
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone as django_timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from Stock.backend.stockinfo import *
from Stock.models import ContactAccount

# Defer heavy ML imports to runtime to avoid import-time errors
# (tensorflow, seaborn, etc. may not be available during setup)
# Create your views here.


def _normalize_username(value):
    return "".join(
        character
        for character in (value or "")
        if unicodedata.category(character) != "Cf"
    ).strip()


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
        "error": error,
        "next": request.POST.get("next") or request.GET.get("next", ""),
    })


@require_http_methods(["GET", "POST"])
def register_page(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect("/")
    if request.method == "GET":
        return render(request, "auth.html", {"mode": "register"})

    email = (request.POST.get("email") or "").strip().lower()
    phone_number = (request.POST.get("phone") or "").strip()
    username = _normalize_username(request.POST.get("username"))
    full_name = " ".join((request.POST.get("full_name") or "").split())
    password = request.POST.get("password") or ""
    password_confirm = request.POST.get("password_confirm") or ""
    birth_date_value = request.POST.get("birth_date") or ""
    form_data = {
        "full_name": full_name,
        "username": username,
        "email": email,
        "phone": phone_number,
        "birth_date": request.POST.get("birth_date") or "",
    }

    def invalid_form(message):
        return render(
            request,
            "auth.html",
            {"mode": "register", "error": message, "form_data": form_data},
            status=400,
        )

    try:
        validate_email(email)
    except ValidationError:
        return invalid_form("Enter a valid email address.")
    if not re.fullmatch(r"[6-9]\d{9}", phone_number):
        return invalid_form("Enter a valid 10-digit Indian mobile number.")
    phone = "+91" + phone_number
    if not username or len(username) > 150 or not re.fullmatch(r"[\w.@+-]+", username):
        return invalid_form("Enter a username using letters, numbers, and @ . + - _.")
    if len(full_name) < 2 or len(full_name) > 120:
        return invalid_form("Enter your full name (up to 120 characters).")
    if password != password_confirm:
        return invalid_form("The passwords do not match.")
    User = get_user_model()
    if User._default_manager.filter(username__iexact=username).exists():
        return invalid_form("That username is already taken.")
    try:
        birth_date = datetime.strptime(birth_date_value, "%Y-%m-%d").date()
    except ValueError:
        return invalid_form("Enter a valid date of birth.")
    if birth_date >= django_timezone.localdate():
        return invalid_form("Date of birth must be in the past.")
    candidate_user = User(username=username, email=email)
    try:
        password_validation.validate_password(password, candidate_user)
    except ValidationError as error:
        return invalid_form(" ".join(error.messages))
    if ContactAccount.objects.filter(identifier=email).exists():
        return invalid_form("An account already uses this email. Please log in instead.")
    if ContactAccount.objects.filter(identifier=phone).exists():
        return invalid_form("An account already uses this phone number. Please log in instead.")

    try:
        with transaction.atomic():
            user = User(
                username=username,
                email=email,
                first_name=full_name[:150],
            )
            user.set_password(password)
            user.save()
            ContactAccount.objects.create(
                user=user,
                identifier=email,
                channel=ContactAccount.CHANNEL_EMAIL,
                full_name=full_name,
                birth_date=birth_date,
            )
            ContactAccount.objects.create(
                user=user,
                identifier=phone,
                channel=ContactAccount.CHANNEL_PHONE,
                full_name=full_name,
                birth_date=birth_date,
            )
    except IntegrityError:
        return invalid_form("An account already uses this email or phone number. Please log in.")
    return HttpResponseRedirect(reverse("login") + "?registered=1")


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
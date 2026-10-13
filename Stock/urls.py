from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path("login", views.login_page, name="login"),
    path("register", views.register_page, name="register"),
    path(
        "password/forgot",
        auth_views.PasswordResetView.as_view(
            template_name="password_reset.html",
            email_template_name="password_reset_email.txt",
            subject_template_name="password_reset_subject.txt",
            extra_context={"mode": "password", "stage": "request"},
        ),
        name="password_reset",
    ),
    path(
        "password/forgot/done",
        auth_views.PasswordResetDoneView.as_view(
            template_name="password_reset.html",
            extra_context={"mode": "password", "stage": "sent"},
        ),
        name="password_reset_done",
    ),
    path(
        "password/reset/<uidb64>/<token>",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="password_reset.html",
            extra_context={"mode": "password", "stage": "confirm"},
        ),
        name="password_reset_confirm",
    ),
    path(
        "password/reset/complete",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="password_reset.html",
            extra_context={"mode": "password", "stage": "complete"},
        ),
        name="password_reset_complete",
    ),
    path("logout", views.logout_user, name="logout"),
    path("", views.index, name="index"),
    path("stock", views.stock, name="stock"),
    path("predict", views.predict, name="predict"),
    path("predict_stock/<str:symbol>/<str:period>/<int:sim>/<int:future>", views.stock_predict, name="predict_stock"),
    path("trade", views.trade, name="trade"),
    path("trade_stock/<str:symbol>/<str:period>/<int:init>/<int:skip>", views.stock_trade, name="trade_stock")
]

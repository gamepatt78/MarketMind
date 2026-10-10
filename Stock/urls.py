from django.urls import path

from . import views

urlpatterns = [
    path("login", views.login_page, name="login"),
    path("register", views.register_page, name="register"),
    path("password/forgot", views.forgot_password_page, name="forgot_password"),
    path("password/forgot/send", views.send_password_reset_otp, name="send_password_reset_otp"),
    path("password/forgot/reset", views.reset_password_with_otp, name="reset_password_with_otp"),
    path("logout", views.logout_user, name="logout"),
    path("otp/register/send", views.send_registration_otp, name="send_registration_otp"),
    path("otp/register/verify", views.verify_registration_otp, name="verify_registration_otp"),
    path("", views.index, name="index"),
    path("stock", views.stock, name="stock"),
    path("predict", views.predict, name="predict"),
    path("predict_stock/<str:symbol>/<str:period>/<int:sim>/<int:future>", views.stock_predict, name="predict_stock"),
    path("trade", views.trade, name="trade"),
    path("trade_stock/<str:symbol>/<str:period>/<int:init>/<int:skip>", views.stock_trade, name="trade_stock")
]

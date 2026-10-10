from datetime import date
from types import ModuleType
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from Stock.backend.stockinfo import align_plot_series
from Stock.models import ContactAccount, LoginOTP


class FreeMarketToolsTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="market-tools-user", password="MarketTools!2026")
        self.client.force_login(user)

    def test_ai_pages_are_available_without_payment(self):
        for path in ("/predict", "/trade"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "RELIANCE.NS")
            self.assertContains(response, "AAPL")
            self.assertNotContains(response, "ABB Ltd")

    def test_simulation_results_submit_to_their_own_forms(self):
        for path, form_id in (
            ("/predict", "prediction-form"),
            ("/trade", "trade-form"),
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'<form id="{form_id}"')
                self.assertContains(
                    response,
                    f'document.querySelector("#{form_id}").submit();',
                )

    def test_plot_series_alignment_handles_32_dates_and_31_values(self):
        dates = list(range(32))
        prices = list(range(31))

        aligned_dates, aligned_prices = align_plot_series(dates, prices)

        self.assertEqual(len(aligned_dates), 31)
        self.assertEqual(len(aligned_prices), 31)
        self.assertEqual(aligned_dates[-1], 30)
        self.assertEqual(aligned_prices[-1], 30)

    def test_ai_endpoints_are_available_without_payment(self):
        prediction_module = ModuleType("Stock.backend.predict")
        prediction_module.predict_stock = lambda *args: "prediction chart"
        trade_module = ModuleType("Stock.backend.trade")
        trade_module.trade_stock = lambda *args: "trading chart"

        with patch.dict("sys.modules", {
            "Stock.backend.predict": prediction_module,
            "Stock.backend.trade": trade_module,
        }), patch("Stock.views.time.sleep"):
            prediction = self.client.get("/predict_stock/AAPL/6mo/5/30")
            trading = self.client.get("/trade_stock/AAPL/6mo/10000/2")

        self.assertEqual(prediction.status_code, 200)
        self.assertEqual(prediction.json(), {"data": "prediction chart"})
        self.assertEqual(trading.status_code, 200)
        self.assertEqual(trading.json(), {"data": "trading chart"})

    def test_ai_endpoints_reject_tickers_outside_the_verified_list(self):
        for path in (
            "/predict_stock/AHC/6mo/5/30",
            "/trade_stock/AHC/6mo/10000/2",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 400)
                self.assertIn("ticker from the symbol list", response.json()["error"])

    def test_market_data_form_offers_only_verified_symbols(self):
        response = self.client.get("/stock")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RELIANCE.NS")
        self.assertContains(response, "AAPL")
        self.assertNotContains(response, "ABB Ltd")

    @patch("Stock.views.get_stock", return_value=None)
    @patch("Stock.views.get_info", return_value=None)
    def test_missing_period_data_gets_a_clear_retryable_message(self, get_info, get_stock):
        response = self.client.post(
            "/stock",
            {"symbol": "AAPL", "period": "6mo", "action": "add_card"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Market data is temporarily unavailable")
        get_stock.assert_called_once_with("AAPL", "6mo")
        get_info.assert_called_once_with("AAPL")

    def test_payment_pages_and_endpoints_are_removed(self):
        for path in ("/premium", "/payments/create-order", "/payments/verify"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

@override_settings(
    EMAIL_HOST="smtp.example.test",
    DEFAULT_FROM_EMAIL="noreply@example.test",
    TWILIO_ACCOUNT_SID="ACtest",
    TWILIO_AUTH_TOKEN="test-token",
    TWILIO_FROM_PHONE="+15550000000",
)
class OTPAuthenticationTests(TestCase):
    def test_registration_page_requires_phone_but_not_email_otp(self):
        response = self.client.get("/register")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email address (optional)")
        self.assertContains(response, "SMS verification code")
        self.assertNotContains(response, "Email verification code")

    def test_registration_username_ignores_invisible_format_characters(self):
        with patch("Stock.views._deliver_otp"):
            response = self.client.post(
                "/otp/register/send",
                {
                    "email": "asha@example.com",
                    "phone": "+919876543210",
                    "username": "\u200basha_trader26\u200b",
                    "full_name": "Asha Sharma",
                    "birth_date": "1998-05-12",
                    "password": "Market!Trend2026",
                    "password_confirm": "Market!Trend2026",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            LoginOTP.objects.filter(
                pending_username="asha_trader26",
            ).exists()
        )

    def test_password_reset_email_code_changes_password_and_returns_to_login(self):
        user = get_user_model().objects.create_user(
            username="reset-trader",
            email="reset@example.com",
            password="OldPass987!",
        )
        ContactAccount.objects.create(
            user=user,
            identifier="reset@example.com",
            channel=ContactAccount.CHANNEL_EMAIL,
            full_name="Reset Trader",
        )
        sent = {}

        def capture_otp(identifier, channel, code):
            sent.update(identifier=identifier, channel=channel, code=code)

        with patch("Stock.views._deliver_otp", side_effect=capture_otp):
            send_response = self.client.post(
                "/password/forgot/send",
                {"email": "RESET@example.com"},
            )
            self.assertEqual(send_response.status_code, 200)
            self.assertEqual(sent["identifier"], "reset@example.com")
            self.assertEqual(sent["channel"], ContactAccount.CHANNEL_EMAIL)

            reset_response = self.client.post(
                "/password/forgot/reset",
                {
                    "email": "reset@example.com",
                    "code": sent["code"],
                    "password": "NewStrongPass789!",
                    "password_confirm": "NewStrongPass789!",
                },
            )

        self.assertEqual(reset_response.status_code, 200)
        self.assertEqual(reset_response.json()["redirect_url"], "/login?password_reset=1")
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewStrongPass789!"))
        self.assertEqual(LoginOTP.objects.filter(
            purpose=LoginOTP.PURPOSE_PASSWORD_RESET
        ).count(), 0)
        login_response = self.client.post(
            "/login",
            {"username": "reset-trader", "password": "NewStrongPass789!"},
        )
        self.assertEqual(login_response.status_code, 302)

    def test_password_reset_rejects_wrong_code_and_password_mismatch(self):
        user = get_user_model().objects.create_user(
            username="reset-trader",
            email="reset@example.com",
            password="OldPass987!",
        )
        ContactAccount.objects.create(
            user=user,
            identifier="reset@example.com",
            channel=ContactAccount.CHANNEL_EMAIL,
            full_name="Reset Trader",
        )
        with patch("Stock.views.secrets.randbelow", return_value=123456), patch(
            "Stock.views._deliver_otp"
        ):
            self.client.post("/password/forgot/send", {"email": "reset@example.com"})

        mismatch = self.client.post(
            "/password/forgot/reset",
            {
                "email": "reset@example.com",
                "code": "123456",
                "password": "NewStrongPass789!",
                "password_confirm": "DifferentPass789!",
            },
        )
        invalid_code = self.client.post(
            "/password/forgot/reset",
            {
                "email": "reset@example.com",
                "code": "000000",
                "password": "NewStrongPass789!",
                "password_confirm": "NewStrongPass789!",
            },
        )

        self.assertEqual(mismatch.status_code, 400)
        self.assertEqual(invalid_code.status_code, 400)
        user.refresh_from_db()
        self.assertTrue(user.check_password("OldPass987!"))

    def test_password_reset_request_does_not_disclose_unknown_email(self):
        with patch("Stock.views._deliver_otp") as deliver:
            response = self.client.post(
                "/password/forgot/send",
                {"email": "unknown@example.com"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["message"],
            "If an account uses that email, a password reset code has been sent.",
        )
        deliver.assert_not_called()

    def test_registration_sends_only_phone_otp_then_returns_to_login(self):
        sent = {}

        def capture_otp(identifier, channel, code):
            sent[identifier] = {"channel": channel, "code": code}

        with patch("Stock.views._deliver_otp", side_effect=capture_otp):
            send_response = self.client.post(
                "/otp/register/send",
                {
                    "email": "  NEW.USER@example.com ",
                    "phone": "9876543210",
                    "username": "newtrader",
                    "full_name": "New Trader",
                    "birth_date": "1995-04-12",
                    "password": "SecurePass987!",
                    "password_confirm": "SecurePass987!",
                },
            )
            self.assertEqual(send_response.status_code, 200)
            self.assertEqual(len(sent), 1)
            self.assertEqual(sent["+919876543210"]["channel"], ContactAccount.CHANNEL_PHONE)

            verify_response = self.client.post(
                "/otp/register/verify",
                {
                    "phone": "9876543210",
                    "phone_code": sent["+919876543210"]["code"],
                },
            )

        self.assertEqual(verify_response.status_code, 200)
        self.assertEqual(verify_response.json()["redirect_url"], "/login?registered=1")
        self.assertFalse(self.client.session.get("_auth_user_id"))
        contacts = ContactAccount.objects.filter(identifier="+919876543210")
        self.assertEqual(contacts.count(), 1)
        account = contacts.get(channel=ContactAccount.CHANNEL_PHONE)
        self.assertEqual(account.user.username, "newtrader")
        self.assertEqual(account.user.email, "new.user@example.com")
        self.assertEqual(account.full_name, "New Trader")
        self.assertEqual(account.birth_date.isoformat(), "1995-04-12")
        today = date.today()
        expected_age = today.year - 1995 - (
            (today.month, today.day) < (4, 12)
        )
        self.assertEqual(account.age, expected_age)
        self.assertTrue(account.user.check_password("SecurePass987!"))
        self.assertEqual(LoginOTP.objects.count(), 0)

    def test_login_uses_username_and_password(self):
        user = get_user_model().objects.create_user(
            username="trader",
            password="SecurePass987!",
        )
        response = self.client.post(
            "/login",
            {"username": "trader", "password": "SecurePass987!"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/")
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_invalid_password_does_not_authenticate(self):
        get_user_model().objects.create_user(
            username="trader",
            password="SecurePass987!",
        )
        response = self.client.post(
            "/login",
            {"username": "trader", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "username or password is incorrect")
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_registration_rejects_password_without_mixed_character_types(self):
        response = self.client.post(
            "/otp/register/send",
            {
                "email": "new.user@example.com",
                "phone": "+919876543210",
                "username": "newtrader",
                "full_name": "New Trader",
                "birth_date": "1995-04-12",
                "password": "alllowercase123",
                "password_confirm": "alllowercase123",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("uppercase letter", response.json()["error"])
        self.assertEqual(LoginOTP.objects.count(), 0)

    def test_anonymous_users_are_sent_to_login_before_accessing_the_app(self):
        for path in ("/", "/stock", "/predict_stock/AAPL/6mo/5/30"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/login", response["Location"])

    def test_forgot_password_page_is_public(self):
        response = self.client.get("/password/forgot")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reset your password")
        self.assertContains(response, "Email me a reset code")

    def test_registration_does_not_require_email(self):
        sent = {}

        def capture_otp(identifier, channel, code):
            sent.update(identifier=identifier, channel=channel, code=code)

        with patch("Stock.views._deliver_otp", side_effect=capture_otp):
            send_response = self.client.post(
                "/otp/register/send",
                {
                    "email": "",
                    "phone": "+919876543211",
                    "username": "phoneonly",
                    "full_name": "Phone Only",
                    "birth_date": "1995-04-12",
                    "password": "SecurePass987!",
                    "password_confirm": "SecurePass987!",
                },
            )
            self.assertEqual(send_response.status_code, 200)
            self.assertEqual(sent["identifier"], "+919876543211")
            self.assertEqual(sent["channel"], ContactAccount.CHANNEL_PHONE)

            verify_response = self.client.post(
                "/otp/register/verify",
                {
                    "phone": "+919876543211",
                    "phone_code": sent["code"],
                },
            )

        self.assertEqual(verify_response.status_code, 200)
        user = get_user_model().objects.get(username="phoneonly")
        self.assertEqual(user.email, "")
        self.assertTrue(
            ContactAccount.objects.filter(
                user=user,
                identifier="+919876543211",
                channel=ContactAccount.CHANNEL_PHONE,
            ).exists()
        )

    def test_invalid_phone_code_does_not_create_registration(self):
        with patch("Stock.views.secrets.randbelow", return_value=123456), patch(
            "Stock.views._deliver_otp"
        ):
            self.client.post(
                "/otp/register/send",
                {
                    "phone": "+919876543210",
                    "username": "newtrader",
                    "full_name": "New Trader",
                    "birth_date": "1995-04-12",
                    "password": "SecurePass987!",
                    "password_confirm": "SecurePass987!",
                },
            )

        response = self.client.post(
            "/otp/register/verify",
            {
                "phone": "+919876543210",
                "phone_code": "000000",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ContactAccount.objects.count(), 0)

    def test_missing_sms_delivery_configuration_returns_clear_error(self):
        with override_settings(
            TWILIO_ACCOUNT_SID="",
            TWILIO_AUTH_TOKEN="",
            TWILIO_FROM_PHONE="",
        ):
            response = self.client.post(
                "/otp/register/send",
                {
                    "phone": "+919876543210",
                    "username": "newtrader",
                    "full_name": "New Trader",
                    "birth_date": "1995-04-12",
                    "password": "SecurePass987!",
                    "password_confirm": "SecurePass987!",
                },
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("Twilio", response.json()["error"])

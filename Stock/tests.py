from types import ModuleType
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from Stock.backend.stockinfo import align_plot_series
from Stock.models import ContactAccount


class FreeMarketToolsTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="market-tools-user",
            password="Market!Tools987",
        )
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


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class DirectRegistrationTests(TestCase):
    def registration_data(self, **overrides):
        values = {
            "full_name": "New Trader",
            "username": "newtrader",
            "email": "new.user@example.com",
            "phone": "9876543210",
            "birth_date": "1995-04-12",
            "password": "Market!Trend2026",
            "password_confirm": "Market!Trend2026",
        }
        values.update(overrides)
        return values

    def test_registration_page_has_no_email_verification_step(self):
        response = self.client.get("/register")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email address")
        self.assertContains(response, "This email is saved with your account but is not verified.")
        self.assertContains(response, 'method="post"')
        self.assertContains(response, "Create account")
        self.assertNotContains(response, "verification code")

    def test_registration_saves_user_and_contacts_in_sqlite_without_email_service(self):
        response = self.client.post("/register", self.registration_data())

        self.assertRedirects(response, "/login?registered=1")
        user = get_user_model().objects.get(username="newtrader")
        self.assertEqual(user.email, "new.user@example.com")
        self.assertEqual(user.first_name, "New Trader")
        self.assertTrue(user.check_password("Market!Trend2026"))
        self.assertEqual(
            set(ContactAccount.objects.filter(user=user).values_list("identifier", flat=True)),
            {"new.user@example.com", "+919876543210"},
        )
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_registration_normalizes_username_and_email(self):
        response = self.client.post(
            "/register",
            self.registration_data(
                username="\u200basha_trader26\u200b",
                email="  ASHA@example.com ",
            ),
        )

        self.assertRedirects(response, "/login?registered=1")
        user = get_user_model().objects.get(username="asha_trader26")
        self.assertEqual(user.email, "asha@example.com")

    def test_new_account_can_log_in_with_username_and_password(self):
        self.client.post("/register", self.registration_data())
        response = self.client.post(
            "/login",
            {"username": "newtrader", "password": "Market!Trend2026"},
        )

        self.assertRedirects(response, "/")
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_registration_rejects_invalid_email_phone_and_password_confirmation(self):
        invalid_inputs = (
            {"email": "not-an-email"},
            {"phone": "12345"},
            {"password_confirm": "a different password"},
        )
        for index, changes in enumerate(invalid_inputs):
            with self.subTest(changes=changes):
                data = self.registration_data(
                    username=f"invaliduser{index}",
                    email=f"invalid{index}@example.com",
                    phone=f"987654321{index}",
                )
                data.update(changes)
                response = self.client.post(
                    "/register",
                    data,
                )
                self.assertEqual(response.status_code, 400)
        self.assertEqual(get_user_model().objects.count(), 0)
        self.assertEqual(ContactAccount.objects.count(), 0)

    def test_registration_rejects_duplicate_email_and_phone(self):
        self.client.post("/register", self.registration_data())

        duplicate_email = self.client.post(
            "/register",
            self.registration_data(username="seconduser", phone="9876543211"),
        )
        duplicate_phone = self.client.post(
            "/register",
            self.registration_data(username="thirduser", email="third@example.com"),
        )

        self.assertEqual(duplicate_email.status_code, 400)
        self.assertContains(duplicate_email, "already uses this email", status_code=400)
        self.assertEqual(duplicate_phone.status_code, 400)
        self.assertContains(duplicate_phone, "already uses this phone number", status_code=400)
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_email_otp_routes_remain_removed(self):
        for path in (
            "/otp/register/send",
            "/otp/register/verify",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_login_page_links_to_password_recovery(self):
        response = self.client.get("/login")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/password/forgot"')
        self.assertContains(response, "Forgot password?")

    def test_password_reset_page_uses_root_relative_favicon(self):
        response = self.client.get("/password/forgot")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'rel="icon" href="/static/assets/logo.png"')

    def test_password_reset_sends_token_link_and_changes_password(self):
        user = get_user_model().objects.create_user(
            username="resetuser",
            email="reset@example.com",
            password="Old!MarketPassword2026",
        )

        response = self.client.post(
            "/password/forgot",
            {"email": "reset@example.com"},
            follow=True,
        )

        self.assertRedirects(response, "/password/forgot/done")
        self.assertContains(response, "If an account exists")

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("http://testserver/password/reset/", mail.outbox[0].body)
        reset_path = mail.outbox[0].body.split("http://testserver", 1)[1].split()[0]
        response = self.client.get(reset_path, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create a new password")
        confirm_path = response.wsgi_request.path_info

        response = self.client.post(
            confirm_path,
            {
                "new_password1": "New!MarketPassword2026",
                "new_password2": "New!MarketPassword2026",
            },
        )

        self.assertRedirects(response, "/password/reset/complete")
        user.refresh_from_db()
        self.assertTrue(user.check_password("New!MarketPassword2026"))

    def test_password_reset_response_does_not_disclose_unknown_email(self):
        response = self.client.post(
            "/password/forgot",
            {"email": "unknown@example.com"},
            follow=True,
        )

        self.assertRedirects(response, "/password/forgot/done")
        self.assertContains(response, "If an account exists")

        self.assertEqual(len(mail.outbox), 0)

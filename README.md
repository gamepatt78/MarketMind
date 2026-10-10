# MarketMind

A Django web application for exploring historical stock prices, experimenting
with price forecasts, and testing a simulated trading strategy. MarketMind is
an educational project: it does not place real trades or provide investment
advice.

## Features

- **Market data:** Look up a supported US or Indian stock and view its recent
  summary and historical closing-price chart.
- **Price forecasts:** Generate experimental forecast paths using an LSTM when
  TensorFlow is installed, or a Monte Carlo fallback otherwise.
- **Trading simulator:** Run a historical, simulated trading strategy with a
  configurable starting balance and trading delay.
- **Accounts:** Register with a phone number verified by SMS OTP. Email is
  optional at registration. Password reset uses an email OTP.
- **Interactive charts:** Explore plotted results and point details in the
  browser.
- **Sign-in required:** The application redirects visitors to login before
  showing the market tools.

Supported symbols and periods are defined in
[`Stock/backend/stockinfo.py`](Stock/backend/stockinfo.py). Market data is
retrieved at request time from Yahoo Finance through `yfinance`, so availability
and values depend on that external service.

## Screenshots

### Market overview

<p align="center">
  <img src="assets/Main.PNG" alt="MarketMind overview" width="900">
</p>

### Market data

<p align="center">
  <img src="assets/Info-done.png" alt="Historical market data and chart" width="900">
</p>

### Price forecast

<p align="center">
  <img src="assets/Prediction-done.png" alt="Illustrative forecast chart" width="900">
</p>

### Trading simulation

<p align="center">
  <img src="assets/Agent-done.png" alt="Historical trading simulation chart" width="900">
</p>

Screenshots and chart values are examples from their capture time; they are not
live quotes or reproducible performance benchmarks.

## Run locally

### 1. Prerequisites

- Git
- Python and `pip`
- Network access for downloading market data

The current development environment uses Python 3.12.10 and Django 3.1.13.
Django 3.1 is end-of-life; use this project for local development and update
and test its framework and dependencies before deployment.

### 2. Clone the repository

```bash
git clone https://github.com/gamepatt78/MarketMind.git
cd MarketMind
```

### 3. Create an environment and install application dependencies

**Windows PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install Django==3.1.13 numpy pandas scikit-learn matplotlib mpld3 seaborn tqdm yfinance requests
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install Django==3.1.13 numpy pandas scikit-learn matplotlib mpld3 seaborn tqdm yfinance requests
```

TensorFlow is optional. Install it if you want the LSTM forecast path; without
it, the prediction module uses its Monte Carlo fallback:

```bash
python -m pip install tensorflow
```

The included `requirements.txt` is an old, environment-specific dependency
snapshot rather than a minimal install manifest. The commands above install the
packages used by the application.

### 4. Configure authentication services

Registration sends a phone verification code using Twilio. Set these variables
in the server environment; keep the real values private and never commit them.

```text
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_FROM_PHONE=your-twilio-phone-number
```

Email-based password reset also requires an SMTP service:

```text
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-smtp-username
EMAIL_HOST_PASSWORD=your-smtp-password
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=your-verified-sender@example.com
```

Without valid Twilio settings, SMS registration codes cannot be delivered.
Without valid SMTP settings, email password-reset codes cannot be delivered.
Registration OTPs expire after five minutes and are rate-limited.

### 5. Set up the database and start Django

```bash
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Open <http://127.0.0.1:8000/>. Register an account after configuring SMS
delivery, then sign in to use the market tools.

## Using the application

1. **Market data:** Choose a supported symbol and period, then request its
   historical chart.
2. **AI predictions:** Choose a symbol and historical period, set 1–10
   simulations and a forecast horizon of 30–365 days, then run the prediction.
3. **Trading agent:** Choose a symbol and historical period, set the starting
   balance and a trading delay from 0–10 days, then run the simulation.

Forecasts and strategy results are experiments over historical data. They do
not predict future returns reliably and do not submit orders to a broker.

## Project layout

| Path | Purpose |
| --- | --- |
| `Stock/` | Django application, views, templates, authentication, and migrations |
| `Stock/backend/stockinfo.py` | Supported tickers, market-data retrieval, and charts |
| `Stock/backend/predict.py` | Forecast generation |
| `Stock/backend/trade.py` | Historical trading simulation |
| `Stock/templates/` | Web interface |
| `Stock/static/` | Stylesheets and static assets |
| `StockMarket/` | Django project configuration |
| `assets/` | Application screenshots and diagrams |

Academic report documents and report folders are intentionally not included in
this GitHub repository.

## Security and deployment

This repository is a development prototype, not a production deployment
configuration. The project currently has development settings, including
`DEBUG = True` and an empty `ALLOWED_HOSTS`. Before deploying:

- turn off debug mode and configure allowed hosts and HTTPS;
- set a unique, private `DJANGO_SECRET_KEY` and review all Django production
  security settings;
- configure and protect production database, Twilio, and SMTP credentials;
- use a production WSGI/ASGI server instead of Django's development server;
- review dependencies and add appropriate logging, monitoring, and rate limits.

Never commit passwords, API tokens, real OTPs, private environment files, or a
local database.

## License

See [`LICENSE`](LICENSE).

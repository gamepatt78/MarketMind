# MarketMind

Explore stock-market history, experiment with possible price paths, and see how
a simulated trading strategy behaves. **MarketMind** is a Django web app for
learning and experimentation; it does not place real trades or provide
investment advice.

## At a glance

| | |
| --- | --- |
| Application | Django web application |
| Market data | Yahoo Finance, through `yfinance` |
| Markets in the symbol list | US and India |
| Forecast methods | LSTM when TensorFlow is available; Monte Carlo fallback otherwise |
| Charting | Matplotlib and `mpld3` |
| Default database | SQLite |
| Live trading | Not supported |

## Screenshots

The screenshots below show the current MarketMind interface and example
results. Form values and chart results are illustrative, captured examples;
market prices depend on the data provider and capture time.

### MarketMind overview

<p align="center">
  <img src="assets/Main.PNG" alt="MarketMind overview and its three analysis tools" width="900">
</p>

### Explore historical market data

Choose a listed symbol and time period to view a stock summary and closing-price
chart.

| Choose a symbol and period | Example summary and chart |
| --- | --- |
| <a href="assets/readme-screenshots/market-data-form.png"><img src="assets/readme-screenshots/market-data-form.png" alt="Market data search form" width="500"></a> | <a href="assets/readme-screenshots/market-data-result.png"><img src="assets/readme-screenshots/market-data-result.png" alt="Market data summary and six-month price chart" width="500"></a> |

### Generate experimental price forecasts

Choose a symbol and historical period, then set the number of paths and future
horizon. Forecast charts illustrate model output; they are not guaranteed
predictions or a validated measure of future accuracy.

| Forecast settings | Example forecast chart |
| --- | --- |
| <a href="assets/readme-screenshots/forecast-form.png"><img src="assets/readme-screenshots/forecast-form.png" alt="Forecast settings form" width="500"></a> | <a href="assets/readme-screenshots/forecast-result.png"><img src="assets/readme-screenshots/forecast-result.png" alt="Example forecast paths and historical trend" width="500"></a> |

### Run a historical trading simulation

Choose a symbol and time period, starting balance, and trading delay. The
simulator plots example buy and sell signals against historical prices; it
does not connect to a broker.

| Simulation settings | Example simulation chart |
| --- | --- |
| <a href="assets/readme-screenshots/trading-form.png"><img src="assets/readme-screenshots/trading-form.png" alt="Trading simulation settings form" width="500"></a> | <a href="assets/readme-screenshots/trading-result.png"><img src="assets/readme-screenshots/trading-result.png" alt="Historical price chart with simulated buy and sell signals" width="500"></a> |

## What you can do

### Market data

- Search the application's verified ticker list for US and Indian stocks.
- Request a period from one day through maximum available history.
- Review the returned company summary and an interactive closing-price chart.
- Hover over chart points to inspect available date and price details.

### Price forecasts

- Choose a listed ticker and a supported historical period.
- Run between **1 and 10** simulation paths.
- Select a forecast horizon between **30 and 365 days**.
- Use the LSTM implementation when TensorFlow is installed; otherwise, the
  prediction module uses a Monte Carlo simulation based on historical returns.

The fallback and LSTM results are experimental scenarios, not investment
recommendations. The project does not establish predictive performance through
a rigorous out-of-sample evaluation.

### Trading simulator

- Choose a listed ticker and a supported historical period.
- Set a starting balance from **$1 to $100,000**.
- Set a trading delay from **0 to 10 days**.
- View the historical price series with simulated buy/sell signals and summary
  values.

This is a historical strategy experiment. It does not execute orders, include
a brokerage connection, or guarantee that results would repeat.

### Accounts

- Market pages require a signed-in account.
- Registration saves the username, password hash, name, date of birth, email,
  and phone details to the local SQLite database. Email and phone ownership
  are not verified; registration does not send OTPs or other email.
- Login checks the stored username and password against the SQLite user
  database.
- Email OTP and email-based password-reset flows are not enabled. Forgotten
  passwords require an administrator reset.

## Run locally

### Requirements

- Git
- Python with `pip`
- Network access to retrieve market data

The current development setup uses Python 3.12.10 and Django 3.1.13. **Django
3.1 is no longer supported upstream.** This repository is a development
prototype; update and test the framework and dependencies before using it in a
public deployment.

### 1. Clone the project

```bash
git clone https://github.com/gamepatt78/MarketMind.git
cd MarketMind
```

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If PowerShell blocks activation for this terminal, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 3. Install the application dependencies

```bash
python -m pip install Django==3.1.13 numpy pandas scikit-learn matplotlib mpld3 seaborn tqdm yfinance requests
```

TensorFlow is optional. Install it to enable the LSTM forecast implementation;
without TensorFlow, the forecast module falls back to Monte Carlo simulations.
TensorFlow installation compatibility depends on the selected Python version
and operating system.

```bash
python -m pip install tensorflow
```

`requirements.txt` is an old environment-specific package snapshot and is not
the recommended installation command for a fresh environment.

### 4. Account storage

The development app stores accounts in `db.sqlite3` in the project root.
Registration does not send email or require an OTP. Back up this database if
you need to preserve local accounts.

### 5. Create the database and start the server

```bash
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Visit <http://127.0.0.1:8000/>. Create an account with an email address and a
valid 10-digit Indian mobile number, then sign in with the username and
password you chose.

## Supported symbols and periods

The ticker list is maintained in
[`Stock/backend/stockinfo.py`](Stock/backend/stockinfo.py).

| Market | Symbols |
| --- | --- |
| United States | `AAPL`, `MSFT`, `NVDA`, `GOOGL`, `AMZN`, `META`, `TSLA`, `JPM` |
| India | `RELIANCE.NS`, `TCS.NS`, `HDFCBANK.NS`, `INFY.NS`, `ICICIBANK.NS`, `SBIN.NS`, `BHARTIARTL.NS`, `ITC.NS` |

Available periods are `1d`, `5d`, `1mo`, `6mo`, `1y`, `5y`, and `max`. Data
availability depends on Yahoo Finance and the selected symbol/period.

## How it is structured

1. A Django view validates the requested symbol, period, and form values.
2. Backend modules retrieve price history from Yahoo Finance with `yfinance`.
3. The prediction or simulation module processes the historical series and
   builds a chart.
4. Django renders the result in the browser with interactive chart output.

## Project layout

| Path | Responsibility |
| --- | --- |
| `manage.py` | Django management commands |
| `Stock/` | Application views, account logic, tests, templates, and migrations |
| `Stock/backend/stockinfo.py` | Supported symbols, market-data retrieval, and price charts |
| `Stock/backend/predict.py` | LSTM and Monte Carlo forecast paths |
| `Stock/backend/trade.py` | Historical evolution-strategy trading simulation |
| `Stock/templates/` | Login, registration, market, prediction, and simulator pages |
| `Stock/static/` | Application styles and static assets |
| `StockMarket/` | Django project settings and URL configuration |
| `assets/` | README screenshots and model diagrams |

Academic report documents and report folders, including generated PDF reports,
are intentionally kept out of this repository.

## Tests and checks

Run the Django configuration check and application tests from the activated
virtual environment:

```bash
python manage.py check
python manage.py test Stock
```

## Security and deployment notes

The checked-in settings are for development: `DEBUG` is enabled, `ALLOWED_HOSTS`
is empty, and the default secret key is explicitly development-only. Before
deployment:

- set a unique, private `DJANGO_SECRET_KEY`;
- disable debug mode and configure allowed hosts, HTTPS, and secure cookies;
- use a production database and WSGI/ASGI server;
- keep deployment secrets outside the repository;
- review Django and third-party dependency versions, update unsupported
  software, and test the changes;
- add deployment-appropriate logging, monitoring, backup, and rate-limit
  controls.

Never commit passwords, API tokens, OTPs, `.env` files, session cookies, or a
local database.

## License

See [`LICENSE`](LICENSE).

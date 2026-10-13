# MarketMind

Explore stock-market history, experiment with possible price paths, and see how
a simulated trading strategy behaves. **MarketMind** is a Django web app for
learning and experimentation; it does not place real trades or provide
investment advice.

**Live site:** <https://marketmind-1-iqy8.onrender.com/>

The site is hosted on Render. The free service may take a little time to wake
up after inactivity. Its SQLite database is not persistent, so accounts and
other database data can be lost when the service is replaced or restarted.

## At a glance

| | |
| --- | --- |
| Application | Django web application |
| Market data | Yahoo Finance, through `yfinance` |
| Markets in the symbol list | US and India |
| Forecast methods | LSTM when TensorFlow is available; Monte Carlo fallback otherwise |
| Charting | Matplotlib and `mpld3` |
| Database | SQLite (ephemeral on the hosted service) |
| Live site | [marketmind-1-iqy8.onrender.com](https://marketmind-1-iqy8.onrender.com/) |
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
  and phone details to the configured Django database (SQLite by default).
  Email and phone ownership are not verified; registration does not send OTPs
  or other email.
- Login checks the username and password against Django's user database.
- Email OTP and email-based password-reset flows are not enabled. Forgotten
  passwords require an administrator reset.
- The hosted service uses an ephemeral SQLite file. Accounts and database
  records are not guaranteed to persist through restarts or redeployments.

## Run locally

### Requirements

- Git
- Python with `pip`
- Network access to retrieve market data

The current development setup uses Python 3.12 and Django 5.2 LTS. Review and
test framework and dependency updates before deploying.

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
python -m pip install "Django>=5.2,<5.3" numpy pandas scikit-learn matplotlib mpld3 seaborn tqdm yfinance requests whitenoise
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

### 4. Create the database and start the server

```bash
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Visit <http://127.0.0.1:8000/>. Create an account with an email address and a
valid 10-digit Indian mobile number, then sign in with the username and
password you chose. Registration does not send email or require an OTP. The
local database is `db.sqlite3` in the project root; back it up if you need to
preserve local accounts.

### Run with Docker locally

The Docker image uses Python 3.12 and installs dependencies from `docReq.txt`.
TensorFlow is optional; without it, forecasts use the Monte Carlo fallback.
Static files are collected during the image build and served by WhiteNoise.

```bash
docker build -t marketmind .
docker run --rm -p 8000:8000 marketmind
```

Open <http://127.0.0.1:8000/>. The container applies migrations at startup and
listens on `PORT` if it is set, otherwise on port 8000.

## Deploy on Render

The live site is deployed from this GitHub repository using Render's Docker
runtime. To create or update the service:

1. Push the changes to GitHub:

   ```bash
   git add README.md
   git commit -m "Describe your change"
   git push origin main
   ```

   The Render service should be connected to `gamepatt78/MarketMind` and the
   `main` branch. New pushes can then trigger a deployment automatically; if
   auto-deploy is disabled, choose **Manual Deploy → Deploy latest commit**.
2. In Render, create a **Web Service** from the repository and select **Docker**
   as the runtime. The `Dockerfile` is in the repository root, so leave **Root
   Directory** blank. Use the `main` branch.
3. Add `DJANGO_SECRET_KEY` under **Environment Variables**. Use Render's
   **Generate** control to create a private value; do not commit or share it.
   Keep `DJANGO_DEBUG` unset or set it to `false`.
4. Choose a region and compute plan, then deploy. The service should start with
   the port Render supplies in `PORT`.
5. Check the deploy logs. A successful build installs packages, runs
   `collectstatic`, then starts the container. At startup, the container runs
   database migrations before starting Django. Open the `onrender.com` URL
   shown on the service page.

The Django settings automatically allow Render's `RENDER_EXTERNAL_HOSTNAME`,
trust the service's HTTPS origin for CSRF, and recognize Render's forwarded
HTTPS scheme. You normally do not need to set `ALLOWED_HOSTS` or
`CSRF_TRUSTED_ORIGINS` for the Render-provided URL. Set those variables only
when adding another hostname or deploying on another platform.

### What happens during deployment

1. Render checks out the selected GitHub commit and builds the root
   `Dockerfile`.
2. Docker installs the Python dependencies from `docReq.txt`, copies the
   application, and runs `python manage.py collectstatic --noinput`.
   WhiteNoise serves the collected CSS, images, and other static assets.
3. When the container starts, it runs `python manage.py migrate` and then
   starts Django on Render's assigned port.
4. Django serves the pages and APIs. Market data is fetched on demand from
   Yahoo Finance; it is not included in the deployment image.

### Hosting notes

- The free service may spin down while idle, so the first request after a
  period of inactivity can be slow.
- The app uses SQLite at `db.sqlite3`. Render's default container filesystem
  is ephemeral, and the free plan does not support persistent disks. Accounts
  and database records may be lost when the service restarts or is redeployed.
- The Docker command currently uses Django's built-in development server.
  For a production deployment, use a production WSGI server and persistent
  database, and review the security settings.
- The app does not trade, connect to a broker, or guarantee forecast or
  simulation results.

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

1. A visitor registers with a username, password, email address, phone number,
   name, and date of birth. Django stores a password hash in its user table and
   contact details in the app's account table.
2. After login, Django's authentication middleware protects the market pages.
3. Views validate requested symbols, periods, and form values. Backend modules
   fetch market history from Yahoo Finance with `yfinance`.
4. Forecast and simulation modules process the returned history and build
   charts. Forecasting uses LSTM when TensorFlow is installed, otherwise it
   falls back to Monte Carlo simulation.
5. Django renders the pages and returns interactive chart output. WhiteNoise
   serves static assets in the Docker deployment.

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

`DEBUG` is off by default, but the current container starts Django's built-in
development server. Before a production deployment:

- set a unique, private `DJANGO_SECRET_KEY`;
- use a production WSGI/ASGI server and a persistent database;
- configure allowed hosts, HTTPS, CSRF trusted origins, and secure cookies for
  the hosting platform;
- keep deployment secrets outside the repository;
- add deployment-appropriate logging, monitoring, backups, and rate limits.

For Render's provided hostname, the project reads `RENDER_EXTERNAL_HOSTNAME`,
recognizes the forwarded HTTPS scheme, and trusts that HTTPS origin for CSRF.
For other hosting platforms, set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` as
comma-separated environment-variable lists and configure proxy HTTPS handling
in Django settings.

Never commit passwords, API tokens, OTPs, `.env` files, session cookies, or a
local database.

## License

See [`LICENSE`](LICENSE).

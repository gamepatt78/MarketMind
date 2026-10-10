import yfinance as yf
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime, timedelta
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mpld3
import numpy as np


indian_symbols = [
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries Limited"},
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services Limited"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank Limited"},
    {"symbol": "INFY.NS", "name": "Infosys Limited"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank Limited"},
    {"symbol": "SBIN.NS", "name": "State Bank of India"},
    {"symbol": "BHARTIARTL.NS", "name": "Bharti Airtel Limited"},
    {"symbol": "ITC.NS", "name": "ITC Limited"},
]
us_symbols = [
    {"symbol": "AAPL", "name": "Apple Inc."},
    {"symbol": "MSFT", "name": "Microsoft Corporation"},
    {"symbol": "NVDA", "name": "NVIDIA Corporation"},
    {"symbol": "GOOGL", "name": "Alphabet Inc."},
    {"symbol": "AMZN", "name": "Amazon.com, Inc."},
    {"symbol": "META", "name": "Meta Platforms, Inc."},
    {"symbol": "TSLA", "name": "Tesla, Inc."},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co."},
]
supported_symbols = us_symbols + indian_symbols
supported_symbol_tickers = frozenset(item["symbol"] for item in supported_symbols)
supported_periods = frozenset(("1d", "5d", "1mo", "6mo", "1y", "5y", "max"))


def align_plot_series(x_values, y_values):
    """Keep chart coordinates paired when data preparation changes either series length."""
    length = min(len(x_values), len(y_values))
    return x_values[:length], y_values[:length]


def get_stock_data(symbol, period="1d", interval=None):
    """Fetch stock data from Yahoo Finance."""
    try:
        interval = interval or "1d"
        df = yf.download(symbol, period=period, interval=interval)
        return None if df is None or df.empty else df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {str(e)}")
        return None


def process_stock_data(df, period):
    """Process stock data for plotting."""
    if df is None or df.empty:
        return None, None

    close_data = df["Close"]
    if isinstance(close_data, pd.DataFrame):
        close_data = close_data.iloc[:, 0]
    close = close_data.dropna().round(2).tolist()
    if not close:
        return None, None
    date_ori = pd.to_datetime(df.index).strftime("%Y-%m-%d %H:%M")

    # Resample data for different periods
    if period == "1y":
        df_resampled = df.resample("5D").last()
    elif period == "5y":
        df_resampled = df.resample("20D").last()
    elif period == "max":
        df_resampled = df.resample("60D").last()
    else:
        df_resampled = df

    close_data = df_resampled["Close"]
    if isinstance(close_data, pd.DataFrame):
        close_data = close_data.iloc[:, 0]
    close_resampled = close_data.dropna().round(2).tolist()
    if not close_resampled:
        return None, None
    date_resampled = pd.to_datetime(df_resampled.index).strftime("%Y-%m-%d %H:%M")

    return date_resampled, close_resampled


def create_tooltip_labels(dates, values):
    """Create HTML labels for tooltips."""
    labels = []
    for date, value in zip(dates, values):
        label = f"""
        <table style="border: 1px solid black; font-weight:bold; font-size:larger; background-color:white">
        <tr style="border: 1px solid black;">
        <th style="border: 1px solid black;">Date:</th>
        <td style="border: 1px solid black;">{date}</td>
        </tr>
        <tr style="border: 1px solid black;">
        <th style="border: 1px solid black;">Close:</th>
        <td style="border: 1px solid black;">{value}</td>
        </tr>
        </table>
        """
        labels.append(label)
    return labels


def plot_stock(date_ori, close, symbol, period=None, title=None):
    """Create interactive stock plot with tooltips."""
    date_ori, close = align_plot_series(date_ori, close)
    if len(date_ori) == 0 or len(close) == 0:
        return None
    fig, ax = plt.subplots(figsize=(11, 5))
    lines = plt.plot(
        date_ori, close, marker="*", mec="w", mfc="blue", label="Close", c="lightblue"
    )
    plt.legend()
    plt.locator_params(axis="y", nbins=6)
    if title:
        plt.title(title)
    plt.tight_layout()
    ax.grid(False)
    ax.set_facecolor("white")
    plt.fill_between(date_ori, close, min(close), color="#0083f2")

    # Add tooltips
    labels = create_tooltip_labels(date_ori, close)
    tooltips = mpld3.plugins.PointHTMLTooltip(
        lines[0], labels=labels, voffset=10, hoffset=10
    )
    mpld3.plugins.connect(plt.gcf(), tooltips)

    html = mpld3.fig_to_html(fig)
    plt.close(fig)
    return html


def stock_today(symbol):
    """Plot the latest available daily trading session."""
    df = get_stock_data(symbol, period="1d", interval="1d")
    if df is None:
        return None

    # Access the 'Close' prices for the specific ticker
    close_data = df["Close"]
    if isinstance(close_data, pd.DataFrame):
        close_data = close_data.iloc[:, 0]
    close = close_data.dropna().round(2).tolist()
    if not close:
        return None
    date_ori = pd.to_datetime(df.index).strftime("%Y-%m-%d %H:%M")

    title = f"Stock: {symbol} Latest Trading Session: {date_ori[-1]}"
    return plot_stock(date_ori, close, symbol, title=title)


def get_stock(symbol, period):
    """Get historical stock data and plot."""
    df = get_stock_data(symbol, period=period)
    if df is None:
        return None

    date_ori, close = process_stock_data(df, period)
    if date_ori is None:
        return None

    title = f"Stock: {symbol} Period: {period}"
    return plot_stock(date_ori, close, symbol, title=title)


def get_info(symbol):
    """Get basic stock information."""
    try:
        tick = yf.Ticker(symbol)
        hist = tick.history(period="2d")
        if hist.empty:
            return None

        stock_info = {
            "symbol": symbol,
            "currency": "₹" if symbol.endswith(".NS") else "$",
            "name": next(
                (item["name"] for item in supported_symbols if item["symbol"] == symbol),
                "Unknown",
            ),
            "close": round(hist["Close"].iloc[-1], 2),
            "open": round(hist["Open"].iloc[-1], 2),
            "change": round(hist["Close"].iloc[-1] - hist["Close"].iloc[0], 2),
            "pchange": round(
                (hist["Close"].iloc[-1] - hist["Close"].iloc[0])
                / hist["Close"].iloc[0]
                * 100,
                2,
            ),
            "color": (
                "#00d600" if hist["Close"].iloc[-1] > hist["Close"].iloc[0] else "red"
            ),
            "volume": hist["Volume"].iloc[-1],
        }
        return stock_info
    except Exception as e:
        print(f"Error getting info for {symbol}: {str(e)}")
        return None

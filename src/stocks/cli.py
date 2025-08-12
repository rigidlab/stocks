"""
stocks CLI tool for downloading and plotting stock data.

Features:
- Download daily (1d) data from Yahoo Finance.
- Save data to ~/stocks_ws or path specified by STOCKS_WS.
- Merge new data with existing data (append missing, overwrite overlap).
- Optionally save point-in-time snapshot files.
- Plot OHLC data with Bokeh.

All dates are interpreted as US/Eastern timezone.
"""

import os
import glob
import logging
import click
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from bokeh.plotting import figure, show, output_file

import pytz

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

US_EASTERN = pytz.timezone('US/Eastern')


def parse_date(date_str):
    """Parse absolute or relative date string into datetime (US/Eastern)."""
    now = datetime.now(US_EASTERN)
    if date_str == 'now':
        return now
    
    elif date_str.startswith(('_', '+')):
        sign = -1 if date_str.startswith('_') else 1
        value_part = date_str[1:-1]
        unit = date_str[-1]

        try:
            value = int(value_part)
        except ValueError:
            raise click.BadParameter(f"Invalid relative date value: {date_str}")

        if unit == 'd':
            delta = timedelta(days=value * sign)
        elif unit == 'm':
            delta = timedelta(days=value * 30 * sign)
        elif unit == 'y':
            delta = timedelta(days=value * 365 * sign)
        else:
            raise click.BadParameter(f"Invalid relative date unit: {unit}")

        return now + delta
    
    else:
        return US_EASTERN.localize(datetime.strptime(date_str, '%Y-%m-%d'))


def get_workspace():
    """Get workspace directory from env var or default to ~/stocks_ws."""
    ws = os.environ.get('STOCKS_WS', '~/stocks_ws')
    return os.path.expanduser(ws)


@click.group()
def cli():
    """stocks CLI tool to download and plot stock data."""
    pass


@cli.command()
@click.option('-t', '--ticker', required=True, help='Ticker(s) as comma-separated list or CSV file with Symbol column')
@click.option('-s', '--start', default='_6d', help='Start date')
@click.option('-e', '--end', default='+1d', help='End date')
@click.option('-i', '--interval', default='1d',
              type=click.Choice(['1d', '60m', '15m', '5m', '2m', '1m'], case_sensitive=False),
              help='Interval (e.g. 1d, 60m)')
@click.option('--snapshot', is_flag=True, help='Save point-in-time snapshot')
def download(ticker, start, end, interval, snapshot):
    """Download stocks data from Yahoo and save as CSV (file or comma-separated tickers)."""
    ws = get_workspace()
    save_dir = os.path.join(ws, 'data', interval)
    os.makedirs(save_dir, exist_ok=True)

    # Resolve tickers
    if os.path.isdir(ticker):
        # Collect tickers from all CSV files in the directory
        ticker_list = []
        csv_files = glob.glob(os.path.join(ticker, '*.csv'))
        for file in csv_files:
            df = pd.read_csv(file)
            symbols = df['Symbol'].dropna().astype(str).str.upper().tolist()
            ticker_list.extend(symbols)
        ticker_list = list(set(ticker_list))  # Deduplicate
        logging.info(f"Collected {len(ticker_list)} tickers from directory {ticker}")
    elif os.path.isfile(ticker):
        # Existing file logic
        df = pd.read_csv(ticker)
        ticker_list = df['Symbol'].dropna().astype(str).str.upper().tolist()
        logging.info(f"Loaded {len(ticker_list)} tickers from file {ticker}")
    else:
        # Comma-separated list
        ticker_list = [t.strip().upper() for t in ticker.split(',')]
        logging.info(f"Using tickers: {ticker_list}")

    start_dt = parse_date(start).astimezone(pytz.utc)
    end_dt = parse_date(end).astimezone(pytz.utc)

    i = 0
    chunk_size = 100  # safer than 500

    while i < len(ticker_list):
        chunk = ticker_list[i:i + chunk_size]
        logging.info(f"Downloading chunk: {chunk}")

        df_chunk = yf.download(
            tickers=chunk,
            start=start_dt.date(),
            end=end_dt.date(),
            interval=interval,
            auto_adjust=False
        )

        if df_chunk.empty:
            logging.warning(f"No data downloaded for chunk {chunk}")
            i += chunk_size
            continue

        # Flatten MultiIndex columns
        if isinstance(df_chunk.columns, pd.MultiIndex):
            df_chunk.columns = [f"{col[0]}_{col[1]}" for col in df_chunk.columns.values]

        df_chunk.reset_index(inplace=True)
        if 'Datetime' in df_chunk.columns:
            df_chunk.rename(columns={'Datetime': 'Date'}, inplace=True)
        elif 'index' in df_chunk.columns:
            df_chunk.rename(columns={'index': 'Date'}, inplace=True)

        # Process each ticker
        for symbol in chunk:
            cols = ['Date'] + [c for c in df_chunk.columns if c.endswith(f"_{symbol}")]
            df_symbol = df_chunk[cols].copy()

            rename_map = {
                f"Open_{symbol}": "Open",
                f"High_{symbol}": "High",
                f"Low_{symbol}": "Low",
                f"Close_{symbol}": "Close",
                f"Adj Close_{symbol}": "Adj Close",
                f"Adj_Close_{symbol}": "Adj Close",
                f"Volume_{symbol}": "Volume"
            }
            df_symbol.rename(columns=rename_map, inplace=True)
            
            # ✅ Insert rounding here:
            '''
            price_cols = ['Open', 'High', 'Low', 'Close', 'Adj Close']
            for col in price_cols:
                if col in df_symbol.columns:
                    df_symbol[col] = df_symbol[col].round(2)
            '''
            ordered = ['Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
            available = [col for col in ordered if col in df_symbol.columns]
            df_symbol = df_symbol[available]
            
            safe_symbol = symbol.replace('/', '_').replace('\\', '_').replace(':', '_')
            save_path = os.path.join(save_dir, f'{safe_symbol}.csv')
            #df_symbol.to_csv(save_path, index=False)
            if os.path.isfile(save_path):
                logging.info(f'{save_path} exists. Append to file and dedup')
                df_old = pd.read_csv(save_path, parse_dates=['Date'])
                df = pd.concat([df_old, df_symbol], ignore_index=True)
                df.drop_duplicates(subset=['Date'], keep='last', inplace=True)
                df.sort_values(by='Date', inplace=True)
            else:
                df = df_symbol

            df.to_csv(save_path, index=False)
            logging.info(f"Saved updated data to {save_path}")

        i += chunk_size

@cli.command()
@click.option('-t', '--ticker', required=True, help='Ticker symbol')
@click.option('-s', '--start', required=True, help='Start date')
@click.option('-e', '--end', required=True, help='End date')
def plot(ticker, start, end):
    """Plot OHLC daily stock data."""
    ws = get_workspace()
    save_path = os.path.join(ws, 'data', '1d', f'{ticker}.csv')
    if not os.path.isfile(save_path):
        logging.error(f'No data found at {save_path}. Please download first.')
        return

    df = pd.read_csv(save_path, parse_dates=['Date'])
    start_dt = parse_date(start)
    end_dt = parse_date(end)
    df = df[(df['Date'] >= start_dt) & (df['Date'] <= end_dt)]

    if df.empty:
        logging.warning('No data in specified range.')
        return

    p = figure(x_axis_type='datetime', title=f'{ticker} OHLC', width=800, height=400)
    p.line(df['Date'], df['Close'], line_width=2)
    output_file(os.path.join(ws, f'{ticker}_plot.html'))
    show(p)

def get_cli():
    commands=[download,plot]
    for command in commands:
        cli.add_command(command)
    return cli

def main():
    cli=get_cli()
    cli()


if __name__ == '__main__':
    cli()

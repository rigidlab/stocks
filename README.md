# stocks
A tool to download, plot and analyze stocks data from yfinance

## TODO
```
Point In Time Database. YF auto adjust the Close price, even when auto_adjust is False
https://github.com/ranaroussi/yfinance/blob/0713d9386769b168926d3959efd8310b56a33096/yfinance/utils.py#L445-L462
DB -> Bootstrap date --> daily download
Info: .info
Dividends,Stock Split .actions
Option Chain .option_chain
Earnings
```

## Install
```
pip install -r requirements.txt
pip3 install .
```

## Test
```
python stocks/test.py
```

## Usage
### Note
- Default workspace is ~/stocks_ws. Data will be saved to a sqlite database stocks.db in the workspace
- Interval: start <= Date < end

### Download
```
# Default is 1d interval
stocks download -t AAPL -s _14d -e now
# Only 60d is allowed for 15m interval
stocks download -t AAPL -s _14d -e now -i 15m
# Download from a text file
stocks download -t portfolio.txt
```

### Plot
```
stocks plot -t AAPL -s _14d -e now --show
```

### Strategies
```
stocks backtest -s trategy1.py

where strategy1.py:


```

### Tips
```
1m - 7 days
2m,5m,15m,30m - 60 days
1h - 730 days
1d - All
Close Value in yfinance match with Thinkorswim. Open,Volume data does not
```


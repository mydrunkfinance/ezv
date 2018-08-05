# Swiss currency exchange rates from EZV

This repo contains a scrape of the official currency exchange rates relevant
for swiss tax purposes as provided by:
  * http://www.pwebapps.ezv.admin.ch/apps/rates/
  * https://www.ictax.admin.ch/

Data is broken up by symbol into `<symbol>.csv` files with schema:
  * date: YYYY-MM-DD
  * symbol: currency code, three letters
  * price: price of a single unit of this currency in swiss franks (decimal)
  * currency: price unit, always CHF

Note: the rate for a particular date is effective for tax purposes for transactions on
the *next* day, i.e. make sure to shift the dates after reading.

## Joined data

For convenience, joined data is also provided, both in long (ezv.long.csv) and
wide format (ezv.wide.csv). Wide format also contains some additional derived
columns: GBX=GBP/100, CHF=1.

Sample code to read the data:

```
import pandas as pd
import decimal

# Read wide format as floats:
df = pd.read_csv('ezv.wide.csv', parse_dates=['date'], index_col=['date'])

# Read long format as decimals:
df = pd.read_csv('ezv.long.csv', converters={'price': decimal.Decimal},  parse_dates=['date'])

# Pivot to wide:
df = df.pivot('date', 'symbol', 'price')
```

## Downloader

Use `./fetch.py` to download latest updates, merge them into .csv's and
regenerate joined files.

Edit currencies.csv to specify which currencies should get fetched or
pass `--all` flag to download all available currencies.

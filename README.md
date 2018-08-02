# Swiss currency exchange rates from EZV

This repo contains the official currency exchange rates relevant for swiss tax purposes
as provided by [Eidgenössische Zollverwaltung](http://www.pwebapps.ezv.admin.ch/apps/rates/).

Schema:
  * date: YYYY-MM-DD
  * symbol: currency code, three letters
  * price: price of a single unit of this currency in swiss franks (decimal)
  * currency: price unit, always CHF

Note: the rate for a particular date is effective for tax purposes for transactions on
the *next* day, i.e. make sure to shift the dates after reading.

Data is broken up by symbol into <symbol>.csv files.

## Downloader

Use `./fetch.py` to download latest update and merge them into .csv's.

Edit currencies.csv to specify which currencies should get fetches or
pass `--all` flag to download all available.

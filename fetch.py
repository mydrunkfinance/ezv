#!/usr/bin/env python3
"""
Fetches official currency exchange rates relevant for swiss tax purposes from
[Eidgenössische Zollverwaltung](http://www.pwebapps.ezv.admin.ch/apps/rates/)

Note: the rate recorded in .csv for a particular date is effective for tax
purposes for transactions on the *next* day, i.e. make sure to shift the dates
after reading.

Usage: ./fetch.py [--all]

Read currencies.csv, fetches new data for the currencies marked there
for fetching (or all with --all flag) and merges it into <code>.csv files.
"""

import datetime
import os
import re
import sys
import time
import pandas as pd

from dateutil import relativedelta
from decimal import Decimal
from urllib.request import urlopen
from xml.etree import ElementTree

# Directory for storing .csv's with fetched datapoints
OUTPUT_DIR = os.path.abspath(os.path.dirname(__file__))

# Month to start scraping historical data from.
# EZV has data from 2010/07 for all currencies at the moment.
START_MONTH = '2010-07-01'


def to_month(date):
  if type(date) is str:
    date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
  return datetime.date(date.year, date.month, 1)


def fetch_daily_data(date : datetime.date):
  """Fetches EZV data for given date."""

  url = 'http://www.pwebapps.ezv.admin.ch/apps/rates/rate/getxml?activeSearchType=userDefinedDay&d=%s' % date.strftime('%Y%m%d')
  xmldata = urlopen(url).read()
  xmldata = re.sub(' xmlns=[^>]+>', '>', xmldata.decode('utf-8'))
  try:
    root = ElementTree.fromstring(xmldata)
  except:
    sys.stderr.write('Failed to parse %s as XML:\n%s\n' % (url, xmldata))
    raise

  rows = []
  for el in root.iter('devise'):
    units, code = el.findtext('waehrung').split()
    assert code == el.attrib.get('code').upper()
    date = datetime.datetime.strptime(root.findtext('datum'), '%Y-%m-%d').date()
    price = Decimal(el.findtext('kurs')) / Decimal(units)
    country = el.findtext('land_en')
    rows.append([date.strftime('%Y-%m-%d'), code, country, price, 'CHF'])

  return pd.DataFrame(rows, columns=['date', 'symbol', 'country', 'price', 'currency'])


def fetch_monthly_data(symbol : str, date : datetime.date):
  url = 'http://www.pwebapps.ezv.admin.ch/apps/rates/rate/getxml?activeSearchType=month&d=%s&w=%s' % (date.strftime('%Y%m'), symbol.lower())
  xmldata = urlopen(url).read()
  xmldata = re.sub(' xmlns=[^>]+>', '>', xmldata.decode('utf-8'))
  try:
    root = ElementTree.fromstring(xmldata)
  except:
    sys.stderr.write('Failed to parse %s as XML:\n%s\n' % (url, xmldata))
    raise
  root = ElementTree.fromstring(xmldata)
  rows = []

  for el in root.iter('kurs'):
    units, code = el.findtext('waehrung').split()
    date = datetime.datetime.strptime(el.findtext('datum'), '%Y-%m-%d').date()
    price = Decimal(el.findtext('wert')) / Decimal(units)
    rows.append([date.strftime('%Y-%m-%d'), code, price, 'CHF'])

  return pd.DataFrame(rows, columns=['date', 'symbol', 'price', 'currency'])


def fetch_currency(symbol, filename=None):
  """Fetches latest EZV data updates for a particular currency,
     merges with data from local .csv file and overwrites the .csv.

     Returns merged data as a pandas dataframe."""

  if filename is None:
    filename = os.path.join(OUTPUT_DIR, '%s.csv' % symbol.upper())

  data = None
  prev_months = set()

  if os.path.exists(filename):
    data = pd.read_csv(filename, converters={'price': Decimal})
    prev_months = set([to_month(d) for d in data['date']])

  yesterday = datetime.date.today() - datetime.timedelta(days=1)
  cur_month = to_month(datetime.date.today())
  month = to_month(START_MONTH)
  all_months = []

  while month <= cur_month:
    all_months.append(month)
    month += relativedelta.relativedelta(months=1)

  for month in all_months:
    # Skip previously downloaded months except the last one
    # which might contain partial data and need an update
    if month in prev_months and month != max(prev_months):
      continue

    sys.stdout.write('%s %s: ' % (symbol, month.strftime('%Y/%m')))
    sys.stdout.flush()

    if (month == cur_month and
        data['date'].max() == yesterday.strftime('%Y-%m-%d')):
      sys.stdout.write('already up to date\n')
      continue

    mdata = fetch_monthly_data(symbol, month)
    if month < cur_month and len(mdata) < 18:
      raise Exception('Fetched bad data for %s %s: too few datapoints (%d)' %
                      (month.strftime('%Y/%m'), len(mdata)))

    # Merge after each successful download to not lose data on future errors
    if data is None:
      merged = mdata
    else:
      merged = pd.concat([data, mdata], axis=0).groupby('date').last()
      merged = merged.reset_index().sort_values('date').reset_index(drop=True)
      if merged.equals(data):
        sys.stdout.write('no new data\n')
        continue

    merged.to_csv(filename + '.tmp', index=False)
    os.rename(filename + '.tmp', filename)
    sys.stdout.write('OK\n')
    data = merged

    # Ratelimit ourselves if downloading multiple months
    if month < cur_month:
      time.sleep(0.5)

  return data


def main():
  if not os.path.exists(OUTPUT_DIR):
    print('Creating cache directory %s' % OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

  # Fetch list of currencies if first time only
  currencies_csv = os.path.join(OUTPUT_DIR, 'currencies.csv')
  if not os.path.exists(currencies_csv):
    print('Fetching list of available currencies into %s' % currencies_csv)
    df = fetch_daily_data(datetime.date.today())
    df['fetch'] = '1'
    df[['symbol', 'fetch', 'country']].to_csv(currencies_csv, index=False)

  currencies = pd.read_csv(currencies_csv)
  if currencies['fetch'].sum() == 0:
    print('Please edit %s and mark which currencies to fetch' % currencies_csv)
    sys.exit(1)

  to_fetch = currencies[currencies.fetch == 1]['symbol']
  if sys.argv[1:] == ['--all']:
    to_fetch = currencies['symbol']

  for symbol in to_fetch:
    fetch_currency(symbol)

  # Merge all data
  all_data = []
  for symbol in currencies.symbol:
    filename = os.path.join(OUTPUT_DIR, '%s.csv' % symbol.upper())
    if os.path.exists(filename):
      all_data.append(pd.read_csv(filename, converters={'price': Decimal}, parse_dates=['date']))

  all_data = pd.concat(all_data, axis=0).sort_values(['date', 'symbol']).reset_index(drop=True)
  all_data.to_csv(os.path.join(OUTPUT_DIR, 'ezv.long.csv'), index=False)

  wide = all_data.pivot('date', 'symbol', 'price')
  wide['CHF'] = Decimal('1.0')
  wide['GBX'] = wide['GBP'] / 100
  wide.to_csv('ezv.wide.csv')


if __name__ == '__main__':
  main()

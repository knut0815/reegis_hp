# http://data.open-power-system-data.org/time_series/2016-10-28/time_series_60min_singleindex.csv

import os
import logging
import requests
import pandas as pd
import datetime
from oemof.tools import logger


BASICPATH = os.path.join('data', 'basic')
DEMAND = os.path.join('data', 'demand')
PREPARED = os.path.join('data', 'demand', 'prepared')
PREPFILE = os.path.join(PREPARED, 'entsoe_DE_load.csv')
SHARE = os.path.join('data', 'basic', 'de21_demand_share.csv')


def read_original_file():
    """Read file if exists."""

    orig_csv_file = os.path.join(DEMAND, 'original',
                                 'time_series_60min_singleindex.csv')
    info_file = os.path.join(DEMAND,
                             'time_series_60min_singleindex.info.csv')
    readme = os.path.join(DEMAND, 'original', 'README.md')
    json = os.path.join(DEMAND, 'original', 'datapackage.json')

    if not os.path.isdir(DEMAND):
        os.makedirs(DEMAND)
    if not os.path.isdir(os.path.join(DEMAND, 'original')):
        os.makedirs(os.path.join(DEMAND, 'original'))
    if not os.path.isdir(PREPARED):
        os.makedirs(PREPARED)

    if not os.path.isfile(orig_csv_file):
        csv = pd.read_csv(info_file, squeeze=True, index_col=[0])
        req = requests.get(csv.download)
        logging.warning("File not found. Try to download it from server.")
        logging.warning("Check URL if download does not work.")
        with open(orig_csv_file, 'wb') as fout:
            fout.write(req.content)
        logging.warning("Downloaded from {0} and copied to '{1}'.".format(
            csv.download, orig_csv_file))
        logging.warning("This script is tested with the file of {0}.".format(
            csv.date))
        req = requests.get(csv.readme)
        with open(readme, 'wb') as fout:
            fout.write(req.content)
        req = requests.get(csv.json)
        with open(json, 'wb') as fout:
            fout.write(req.content)

    return pd.read_csv(orig_csv_file)


def prepare_demand_file():
    """Convert demand file. CET index and Germany's load only."""
    if not os.path.isfile(PREPFILE):
        load = read_original_file()

        load['cet'] = (
            pd.to_datetime(load.cet_cest_timestamp) +
            datetime.timedelta(hours=1))

        load = load.set_index('cet')

        load[['utc_timestamp', 'cet_cest_timestamp', 'DE_load_']
             ].to_csv(PREPFILE)


def get_time_period(load, region_code, start_cet, end_cet):

    if region_code == 'DE':
        share = 1
    else:
        share = pd.read_csv(
            SHARE, index_col='region_code', squeeze=True)[region_code]

    return load.ix[start_cet:end_cet].DE_load_.multiply(float(share))


def get_demand_by_region(year):
    if not os.path.isfile(PREPFILE):
        prepare_demand_file()

    start = datetime.datetime(year, 1, 1, 0, 0)
    end = datetime.datetime(year, 12, 31, 23, 0)

    entsoe = pd.read_csv(PREPFILE, index_col='cet', parse_dates=True)

    load_profile = pd.DataFrame(get_time_period(entsoe, 'DE', start, end))
    for i in range(21):
        region = 'DE{:02.0f}'.format(i + 1)
        load_profile[region] = get_time_period(entsoe, region, start, end)

    del load_profile['DE_load_']
    logging.info("Retrieving load profiles for Germany ({0}).".format(year))
    return load_profile


if __name__ == "__main__":
    logger.define_logging()
    get_demand_by_region(2013)

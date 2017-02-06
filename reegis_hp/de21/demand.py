# http://data.open-power-system-data.org/time_series/2016-10-28/time_series_60min_singleindex.csv

import os
import logging
import requests
import pandas as pd
import datetime
from matplotlib import pyplot as plt

FIXED = False
FILEPATH = os.path.join('data', 'entsoe_DE_load.csv')


def read_original_file():
    """Read file if exists."""

    orig_csv_file = os.path.join('data_original',
                                 'time_series_60min_singleindex.csv')
    info_file = os.path.join('data_basic',
                             'time_series_60min_singleindex.info.csv')

    if not os.path.isdir('data_original'):
        os.makedirs('data_original')

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

    return pd.read_csv(orig_csv_file)


def prepare_demand_file():
    """Convert demand file. CET index and Germany's load only."""
    load = read_original_file()

    load['cet'] = (
        pd.to_datetime(load.cet_cest_timestamp) + datetime.timedelta(hours=1))

    load = load.set_index('cet')

    load[['utc_timestamp', 'cet_cest_timestamp', 'comment', 'load_DE_load']
         ].to_csv(FILEPATH)


def get_time_period(region_code, start_cet, end_cet):
    load = pd.read_csv(FILEPATH, index_col='cet',
                       parse_dates=True)

    if region_code == 'DE':
        share = 1
    else:
        share = pd.read_csv(os.path.join('data_basic', 'de21_demand_share.csv'),
                            index_col='region_code', squeeze=True)[region_code]

    return load.ix[start_cet:end_cet].load_DE_load.multiply(float(share))


if not os.path.isfile(FILEPATH):
    prepare_demand_file()

start = datetime.datetime(2014, 1, 1, 0, 0)
end = datetime.datetime(2014, 12, 31, 23, 0)

load_profile = pd.DataFrame(get_time_period('DE', start, end))

for i in range(21):
    region = 'DE{:02.0f}'.format(i + 1)
    load_profile[region] = get_time_period(region, start, end)

print(load_profile.sum())

del load_profile['load_DE_load']

load_profile.plot()
plt.show()

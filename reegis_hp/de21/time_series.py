# http://data.open-power-system-data.org/time_series/2016-10-28/time_series_60min_singleindex.csv

import os
import logging
import requests
import pandas as pd
import datetime
import configuration as config
from oemof.tools import logger


def read_original_timeseries_file(c, overwrite=False):
    """Read file if exists."""

    orig_csv_file = os.path.join(c.paths['time_series'],
                                 c.files['time_series_original'])
    readme = os.path.join(c.paths['time_series'], c.files['time_series_readme'])
    json = os.path.join(c.paths['time_series'], c.files['time_series_json'])

    if not os.path.isfile(orig_csv_file) or overwrite:
        req = requests.get(c.url['time_series_data'])
        logging.warning("File not found. Try to download it from server.")
        logging.warning("Check URL if download does not work.")
        with open(orig_csv_file, 'wb') as fout:
            fout.write(req.content)
        logging.warning("Downloaded from {0} and copied to '{1}'.".format(
            c.url['time_series_data'], orig_csv_file))
        req = requests.get(c.url['time_series_readme'])
        with open(readme, 'wb') as fout:
            fout.write(req.content)
        req = requests.get(c.url['time_series_json'])
        with open(json, 'wb') as fout:
            fout.write(req.content)

    orig = pd.read_csv(orig_csv_file, index_col=[0], parse_dates=True)
    orig = orig.tz_localize('UTC').tz_convert('Europe/Berlin')
    return orig


def prepare_de_file(c, overwrite=False):
    """Convert demand file. CET index and Germany's load only."""
    de_file = os.path.join(c.paths['time_series'], c.files['time_series_de'])
    if not os.path.isfile(de_file) or overwrite:
        ts = read_original_timeseries_file(c, overwrite)
        for col in ts.columns:
            if 'DE' not in col:
                ts.drop(col, 1, inplace=True)

        ts.to_csv(de_file)


def split_timeseries_file(c, overwrite=False):
    path_pattern = os.path.join(c.paths['time_series'], '{0}')
    de_file = path_pattern.format(c.files['time_series_de'])

    if not os.path.isfile(de_file) or overwrite:
        prepare_de_file(c, overwrite)
    de_ts = pd.read_csv(de_file, index_col='cet')

    load = pd.DataFrame(de_ts[pd.notnull(de_ts['DE_load_'])]['DE_load_'],
                        columns=['DE_load_'])

    re_columns = [
        'DE_solar_capacity', 'DE_solar_generation', 'DE_solar_profile',
        'DE_wind_capacity', 'DE_wind_generation', 'DE_wind_profile',
        'DE_wind_offshore_capacity', 'DE_wind_offshore_generation',
        'DE_wind_offshore_profile', 'DE_wind_onshore_capacity',
        'DE_wind_onshore_generation', 'DE_wind_onshore_profile']
    re_subset = [
        'DE_solar_capacity', 'DE_solar_generation', 'DE_solar_profile',
        'DE_wind_capacity', 'DE_wind_generation', 'DE_wind_profile']

    renewables = de_ts.dropna(subset=re_subset, how='any')[re_columns]

    load_file = path_pattern.format(c.files['load_time_series'])
    if not os.path.isfile(load_file) or overwrite:
        load.to_csv(load_file)

    re_file = path_pattern.format(c.files['renewables_time_series'])
    if not os.path.isfile(re_file) or overwrite:
        renewables.to_csv(re_file)


def get_timeseries(c, overwrite=False):
    split_timeseries_file(c, overwrite)


if __name__ == "__main__":
    logger.define_logging()
    conf = config.get_configuration()
    split_timeseries_file(conf)

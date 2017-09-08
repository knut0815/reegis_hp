# http://data.open-power-system-data.org/time_series/2016-10-28/time_series_60min_singleindex.csv

import os
import logging
import requests
import datetime
import pytz
import dateutil
import pandas as pd
from reegis_hp.de21 import config as cfg
from oemof.tools import logger


def read_original_timeseries_file(overwrite=False):
    """Read file if exists."""

    orig_csv_file = os.path.join(cfg.get('paths', 'time_series'),
                                 cfg.get('time_series', 'original_file'))
    readme = os.path.join(cfg.get('paths', 'time_series'),
                          cfg.get('time_series', 'readme_file'))
    json = os.path.join(cfg.get('paths', 'time_series'),
                        cfg.get('time_series', 'json_file'))

    if not os.path.isfile(orig_csv_file) or overwrite:
        req = requests.get(cfg.get('download', 'url_timeseries_data'))
        if not overwrite:
            logging.warning("File not found. Try to download it from server.")
        else:
            logging.warning("Will download file from server and overwrite"
                            "existing ones")
        logging.warning("Check URL if download does not work.")
        with open(orig_csv_file, 'wb') as fout:
            fout.write(req.content)
        logging.warning("Downloaded from {0} and copied to '{1}'.".format(
            cfg.get('download', 'url_timeseries_data'), orig_csv_file))
        req = requests.get(cfg.get('download', 'url_timeseries_readme'))
        with open(readme, 'wb') as fout:
            fout.write(req.content)
        req = requests.get(cfg.get('download', 'url_timeseries_json'))
        with open(json, 'wb') as fout:
            fout.write(req.content)

    orig = pd.read_csv(orig_csv_file, index_col=[0], parse_dates=True)
    orig = orig.tz_localize('UTC').tz_convert('Europe/Berlin')
    return orig


def prepare_de_file(overwrite=False):
    """Convert demand file. CET index and Germany's load only."""
    de_file = os.path.join(cfg.get('paths', 'time_series'),
                           cfg.get('time_series', 'de_file'))
    if not os.path.isfile(de_file) or overwrite:
        ts = read_original_timeseries_file(overwrite)
        for col in ts.columns:
            if 'DE' not in col:
                ts.drop(col, 1, inplace=True)

        ts.to_csv(de_file)


def split_timeseries_file(overwrite=False):
    logging.info("Splitting time series.")
    path_pattern = os.path.join(cfg.get('paths', 'time_series'), '{0}')
    de_file = path_pattern.format(cfg.get('time_series', 'de_file'))

    if not os.path.isfile(de_file) or overwrite:
        prepare_de_file(overwrite)

    de_ts = pd.read_csv(de_file, index_col='utc_timestamp', parse_dates=True,
                        date_parser=dateutil.parser.parse)

    berlin = pytz.timezone('Europe/Berlin')
    end_date = berlin.localize(datetime.datetime(2015, 1, 1, 0, 0, 0))

    de_ts.loc[de_ts.index < end_date, 'DE_load_'] = (
        de_ts.loc[de_ts.index < end_date, 'DE_load_old'])
    de_ts.loc[de_ts.index >= end_date, 'DE_load_'] = (
        de_ts.loc[de_ts.index >= end_date, 'DE_load_new'])

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

    load_file = path_pattern.format(cfg.get('time_series', 'load_file'))
    if not os.path.isfile(load_file) or overwrite:
        load.to_csv(load_file)

    re_file = path_pattern.format(cfg.get('time_series', 'renewables_file'))
    if not os.path.isfile(re_file) or overwrite:
        renewables.to_csv(re_file)


def get_timeseries(overwrite=False):
    split_timeseries_file(overwrite)


if __name__ == "__main__":
    logger.define_logging()
    split_timeseries_file()

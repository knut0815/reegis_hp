# http://data.open-power-system-data.org/time_series/2016-10-28/time_series_60min_singleindex.csv

import os
import logging
import time_series
import pandas as pd
import datetime
import configuration as config
from oemof.tools import logger


def get_time_period(c, load, region_code, start_cet, end_cet):
    demand_share = os.path.join(c.paths['static'], c.files['demand_share'])
    if region_code == 'DE':
        share = 1
    else:
        share = pd.read_csv(
            demand_share, index_col='region_code', squeeze=True)[region_code]

    return load.ix[start_cet:end_cet].DE_load_.multiply(float(share))


def get_demand_by_region(year, c, overwrite=False):
    load_file = os.path.join(c.paths['time_series'],
                             c.files['load_time_series'])

    if not os.path.isfile(load_file) or overwrite:
        time_series.split_timeseries_file(c, overwrite)

    start = datetime.datetime(year, 1, 1, 0, 0)
    end = datetime.datetime(year, 12, 31, 23, 0)

    entsoe = pd.read_csv(load_file, index_col='cet', parse_dates=True)

    load_profile = pd.DataFrame(get_time_period(c, entsoe, 'DE', start, end))
    for i in range(21):
        region = 'DE{:02.0f}'.format(i + 1)
        load_profile[region] = get_time_period(c, entsoe, region, start, end)

    del load_profile['DE_load_']
    logging.info("Retrieving load profiles for Germany ({0}).".format(year))
    return load_profile


if __name__ == "__main__":
    logger.define_logging()
    conf = config.get_configuration()
    from matplotlib import pyplot as plt
    get_demand_by_region(2013, conf).plot()
    plt.plot()
    plt.show()

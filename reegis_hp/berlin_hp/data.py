# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 14:35:28 2016

@author: uwe
"""
import logging
import os
import pandas as pd

import oemof.db as db
from oemof.tools import logger
from oemof.tools import helpers


logger.define_logging()
conn = db.connection()


def query2df(sql, columns=None):
    """
    Passes an sql-query to a database and returns the result as a DataFrame.
    The column names of the data base will be the column names of the DataFrame
    if no names are passed to this function.
    """
    logging.info("SQL query: {0}".format(sql))
    logging.info("Retrieving data from db...")
    results = (conn.execute(sql))
    if columns is None:
        columns = results.keys()
    return pd.DataFrame(results.fetchall(), columns=columns)


def electricity_by_region():
    """
    Returns a DataFrame with the electricity usage of Berlin 2012 by region
    """
    sql = 'SELECT distinct name FROM berlin.stromdaten;'
    regions = list(conn.execute(sql).fetchall())

    data = pd.DataFrame()
    n = 0
    total = len(regions)
    for region in regions:
        n += 1
        sql = """
            SELECT usage FROM berlin.stromdaten
            WHERE name = '{0}' order by id;
            """.format(region[0])

        # Fetch data from the data base
        data[region[0]] = query2df(sql).usage

        # Convert column to float
        data[region[0]] = data[region[0]].astype(float)
        logging.info("{0} regions remaining".format(total - n))

    # Add one hour (4 values) that is missing due to change from summer to
    # winter time on October the 28th (Only valid for 2012!!)
    # The hour before the missing hour is copied.
    first = data.query("index < 28900")
    middle = data.query("index > 28900-5 and index < 28900")
    second = data.query("index >= 28900")
    data = pd.concat([first, middle, second], ignore_index=True)

    # Create time index for 2012
    data.index = pd.date_range(pd.datetime(2012, 1, 1, 0), periods=8784*4,
                               freq='15Min')

    # Resample to hourly values
    return data.resample('H').mean()


def get_electricity_usage(fullpath=None):
    if fullpath is None:
        fullpath = os.path.join(helpers.extend_basic_path('reegis_hp'),
                                'berlin_electricity_2012.csv')
    try:
        tmp_df = pd.read_csv(fullpath, index_col='Unnamed: 0')
    except OSError:
        tmp_df = electricity_by_region().sum(axis=1)
        tmp_df.name = 'berlin'
        tmp_df = pd.DataFrame(tmp_df)
        tmp_df.to_csv(fullpath)
    return tmp_df.berlin

def heat_demand():
    pass

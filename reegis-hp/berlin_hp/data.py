# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 14:35:28 2016

@author: uwe
"""
import logging
import time
import pandas as pd
import numpy as np

from oemof import db
from oemof.tools import logger


logger.define_logging()
conn = db.connection()
start = time.time()


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
    regions = ['Pankow', 'Lichtenberg', 'Marzahn-Hellersdorf',
               'Treptow-Koepenick', 'Neukölln', 'Friedrichshain-Kreuzberg',
               'Mitte', 'Tempelhof-Schöneberg', 'Steglitz-Zehlendorf',
               'Charlottenburg-Wilmersdorf', 'Reinickendorf', 'Spandau',
               'Tempelhof-Schöneberg']

    # Create empty DataFrame to collect the results
    data = pd.DataFrame()

    for region in regions:
        sql = """
            SELECT usage FROM berlin.stromdaten
            WHERE name = '{0}' order by id;
            """.format(region)

        # Fetch data from the data base
        data[region] = query2df(sql).usage

        # Convert colum to float
        data[region] = data[region].astype(float)

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

    # Convert power kWh
    data = data * 0.25

    # Resample to hourly values (sum? or mean?)
    return data.resample('H').agg({'usage': np.sum})

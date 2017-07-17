# -*- coding: utf-8 -*-

import logging
import pandas as pd
import os

from oemof.tools import helpers


def query2df(conn, sql, columns=None):
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


class DemandElec:
    def __init__(self, datetime_index, datapath=None, filename=None):
        self.datetime_index = datetime_index
        self.datapath = datapath
        self.filename = filename
        self.usage = self.electricity_usage()

    def electricity_by_district_from_db(self):
        """
        Returns a DataFrame with the electricity usage of Berlin 2012 by region
        """
        import oemof.db as db
        conn = db.connection()
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
            data[region[0]] = query2df(conn, sql).usage

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

        # Create time index
        periods = len(self.datetime_index) * 4 * (
            self.datetime_index.freq.nanos / 3.6e12)
        data.index = pd.date_range(pd.datetime(self.year, 1, 1, 0),
                                   periods=periods, freq='15Min')

        return data

    def electricity_usage(self):
        if self.filename is None:
            self.filename = 'berlin_electricity_load_district_{0}.csv'.format(
                self.year)
        if self.datapath is None:
            self.datapath = helpers.extend_basic_path('reegis_hp')

        fullpath = os.path.join(self.datapath, self.filename)
        try:
            tmp_df = pd.read_csv(fullpath, index_col='Unnamed: 0',
                                 parse_dates=True)
        except OSError:
            tmp_df = self.electricity_by_district_from_db()
            tmp_df.to_csv(fullpath)
        return tmp_df

    def solph_sink(self, total=True, resample=None, reduce=None):
        if total:
            tmp_df = self.usage.sum(axis=1)
        else:
            tmp_df = self.usage

        tmp_df *= 10e+5

        if resample is not None:
            tmp_df = tmp_df.resample(resample).mean()
        if reduce is not None:
            tmp_df -= reduce
        print('to_csv')
        tmp_df.to_csv('/home/uwe/elec.csv')
        max_value = tmp_df.max()
        normalised_values = tmp_df.div(max_value)
        return normalised_values, max_value

    @property
    def year(self):
        return self.datetime_index.year[0]

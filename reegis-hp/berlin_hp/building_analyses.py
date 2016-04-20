# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 14:35:28 2016

@author: uwe
"""
import logging
import time
import pandas as pd

from oemof import db
from oemof.tools import logger


logger.define_logging()
conn = db.connection()
start = time.time()
filename = "/home/uwe/haus.csv"


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


sql = "SELECT DISTINCT gebaeude_1 FROM berlin.alkis_gebaeude"
types = query2df(sql)
buildings = pd.DataFrame()

for typ in types.gebaeude_1:
    sql = """SELECT SUM(st_area(st_transform(geom, 3068)) * anzahldero * 0.8)
        FROM berlin.alkis_gebaeude WHERE gebaeude_1='{0}';""".format(typ)
    data = query2df(sql)
    data['typ'] = typ
    buildings = pd.concat([buildings, data], ignore_index=True)

logging.info("Store results to {0}".format(filename))
buildings.to_csv(filename)
logging.info("Elapsed time: {0}".format(time.time() - start))

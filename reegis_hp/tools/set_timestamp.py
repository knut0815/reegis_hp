# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 14:35:28 2016

@author: uwe
"""
import logging
import time
import pandas as pd

import oemof.db as db
from oemof.tools import logger


logger.define_logging()
conn = db.connection()
start = time.time()

sql = "SELECT DISTINCT name FROM berlin.stromdaten;"

logging.info("SQL query: {0}".format(sql))
logging.info("Retrieving data from db...")
results = (conn.execute(sql))
columns = results.keys()

data = pd.DataFrame(results.fetchall(), columns=columns)

timestamp = pd.date_range('1/1/2012', periods=35136, freq='15min')

for name in data.name:
    n = 0
    sql = "SELECT DISTINCT id FROM berlin.stromdaten WHERE name='{0}';".format(
        name)
    results = (conn.execute(sql))
    columns = results.keys()
    data = pd.DataFrame(results.fetchall(), columns=columns).sort_values('id')
    print(name)
    for db_id in data.id:
        sql = "update berlin.stromdaten set timestamp='{0}' ".format(
            timestamp[n])
        sql += "WHERE id={0} and name='{1}';".format(db_id, name)
        n += 1
    conn.execute(sql)


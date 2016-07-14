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

filename = "/home/uwe/chiba/RLI/data/stadtnutzung_erweitert.csv"

sql = "SELECT * FROM berlin.stadtnutzung;"

logging.info("SQL query: {0}".format(sql))
logging.info("Retrieving data from db...")
results = (conn.execute(sql))
columns = results.keys()

data = pd.DataFrame(results.fetchall(), columns=columns)

print(data.ew.sum())

# Store results to csv file
logging.info("Store results to {0}".format(filename))
data.to_csv(filename)
logging.info("Elapsed time: {0}".format(time.time() - start))

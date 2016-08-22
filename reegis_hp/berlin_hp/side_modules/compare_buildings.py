import pandas as pd
import time
import logging

from oemof.tools import logger

logger.define_logging()
start = time.time()

logging.info("Starting...")
data = pd.read_csv('/home/uwe/haus_berlin.csv')
logging.info("Query...")
print(data.keys())
subset = data.query("gebaeudefu == 1010")
logging.info("Sum...")
print(subset.total_loss_contemp.sum() / subset.living_area.sum())
print(subset.total_loss_pres.sum() / subset.living_area.sum())


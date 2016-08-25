# import logging
# import pandas as pd
# import os
#
# from oemof.tools import helpers


class DemandHeat:
    def __init__(self, datetime_index, datapath=None, filename=None):
        self.datetime_index = datetime_index
        self.datapath = datapath
        self.filename = filename
        self.demand = None

import logging
import pandas as pd
import os
# import demandlib

#
# from oemof.tools import helpers


class DemandHeat:
    def __init__(self, datetime_index, method='oeq', **kwargs):
        self.datetime_index = datetime_index
        self.method = method
        self.datapath = kwargs.get('datapath', os.path.join(
            os.path.expanduser("~"), '.reegis_hp', 'heat_demand'))
        self.filename = kwargs.get('filename')
        self.data = None
        if self.data is None:
            self.load_data()
        self.annual_demand = None

    def load_data(self):
        if self.method == 'oeq':
            if not self.filename:
                self.filename = 'eQuarter_berlin.hdf'
            self.data = pd.HDFStore(os.path.join(self.datapath, self.filename))

        elif self.method == 'wt':
            if not self.filename:
                self.filename = 'waermetool_berlin.hdf'
            self.data = pd.HDFStore(os.path.join(self.datapath, self.filename))
        else:
            logging.warning('No data file found.')
        if self.data:
            self.data.close()

    def get_data(self, table):
        self.data.open()
        tmp = self.data[table]
        self.data.close()
        return tmp

    def dissolve(self, level, column='total'):
        """

        Parameters
        ----------
        level : integer or string
            1 = district, 2 = prognoseraum, 3 = bezirksregion, 4 = planungsraum
        column : string
            Name of the column of the main DataFrame

        Returns
        -------
        pandas.Series
            Dissolved Column.

        """
        error_level = level
        if isinstance(level, str):
            trans_dict = {'bezirk': 1,
                          'prognoseraum': 2,
                          'bezirksregion': 3,
                          'planungsraum': 4}
            level = trans_dict.get(level)

        if level is None:
            logging.error("Wrong level: {0}".format(error_level))

        self.data.open()
        level *= 2
        results = self.data[self.method].groupby(
            self.data[self.method].plr_key.str[:level])[column].sum()
        self.data.close()
        self.annual_demand = results
        return results


my = DemandHeat(1, method='oeq')
my.data.open()
from matplotlib import pyplot as plt
cmap = plt.get_cmap('seismic')
c = ['#000000', '#234000', '#000000', '#000000']
asd = my.data.oeq.groupby('floors').area.sum()
c = list()
for a in asd:
    c.append(cmap(a / asd.max()))
print(c)
asd.plot(kind='bar', color=c)
plt.show()
my.data.close()
exit(0)
berlin_by_district = my.dissolve('bezirk', 'total')

print(berlin_by_district)
print(my.data.close())

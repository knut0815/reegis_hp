import logging
import pandas as pd
import os
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
        self.load_data()

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

    def dissolve(self, level, column):
        """

        Parameters
        ----------
        level : integer or string
            1 = district, 2 = prognoseraum, 3 = bezirksregion, 4 = planungsraum
        column

        Returns
        -------

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
        results = self.data.oeq.groupby(
            self.data.oeq.plr_key.str[:level])[column].sum()
        self.data.close()
        return results


my = DemandHeat(1)
print(my.dissolve('bezirk', 'total_loss_pres'))

print(my.data.close())

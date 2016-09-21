import logging
import pandas as pd
import os
import numpy as np
from matplotlib import pyplot as plt
# from oemof.tools import helpers


class DemandHeat:
    def __init__(self, datetime_index=None, method='oeq', **kwargs):
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

    def demand_by(self, demand_column, heating_systems=None,
                  building_types=None, remove_string='',
                  percentage=False):
        """
        Adds a new table to the hdf-file where the demand is divided by
        building types and/or heating systems.

        Parameters
        ----------
        demand_column : string
            Name of the column with the overall demand
        heating_systems : list of strings
            List of column names. The columns should contain the
             fraction of each heating system. The sum of all these
             columns should be 1 (or 100) for each row. If the sum is
             100 the percentage parameter (prz) must be set to True
        building_types : dictionary
            All building types with their condition.
        remove_string : string
            Part of the column names of the heating systems that
             should be removed to name the results. If the column is
             name "fraction_of_distirct_heating" the string could be
             "fraction_of_" to use just "district_heating" for the name
             of the result column.
        percentage : boolean
            True if the fraction of the heating system columns sums up
            to hundred instead of one.
        Returns
        -------

        """
        if percentage:
            prz = 100
        else:
            prz = 1

        self.data.open()
        if building_types is None:
            building_types = {'all': '{0} == {0}'.format(demand_column)}
        demand_by_building = pd.DataFrame(
            index=self.data[self.method].index)
        for btype, condition in building_types.items():
            demand_by_building.loc[self.data[self.method].query(
                condition).index, btype] = (
                self.data[self.method][demand_column][self.data[
                    self.method].query(condition).index])

        demand = pd.DataFrame(index=self.data[self.method].index)
        loop_list = demand_by_building.keys()
        if heating_systems is None:
            loop_list = []
        for btype in loop_list:
            rename_dict = {
                col: 'demand_' + btype + '_' + col.replace(
                    remove_string, '')
                for col in heating_systems}
            demand = demand.combine_first(
                self.data[self.method][heating_systems].multiply(
                    demand_by_building[btype], axis='index').div(prz))
            demand = demand.rename(columns=rename_dict)

        demand['plr_key'] = self.data[self.method].plr_key
        self.data['demand_by'] = demand
        self.data['building_types'] = pd.Series(building_types)
        self.data.close()

    def dissolve(self, level, table, column=None):
        """

        Parameters
        ----------
        level : integer or string
            1 = district, 2 = prognoseraum, 3 = bezirksregion, 4 = planungsraum
        table : string
            Name of the table in the defined hdf5 data file.
        column : string or list
            Name of the column in the given table.

        Returns
        -------
        pandas.Series
            Dissolved Column.

        """
        self.data.open()
        if column is None:
            column = list(self.data[table].columns)

        error_level = level
        if isinstance(level, str):
            trans_dict = {'bezirk': 1,
                          'prognoseraum': 2,
                          'bezirksregion': 3,
                          'planungsraum': 4}
            level = trans_dict.get(level)

        if level is None:
            logging.error("Wrong level: {0}".format(error_level))

        level *= 2
        results = self.data[table].groupby(
            self.data[table].plr_key.str[:level])[column].sum()
        self.data.close()
        self.annual_demand = results
        return results

    def print(self):
        self.data.open()
        print(self.data)
        self.data.close()

    def delete(self, table):
        self.data.open()
        del self.data[table]
        self.data.close()

    def get(self, table=None, columns=None):
        self.data.open()
        if table is None:
            table = self.method
        if columns is None:
            tmp = self.data[table].copy()
        else:
            tmp = self.data[table][columns].copy()
        self.data.close()
        return tmp

if __name__ == "__main__":
    my = DemandHeat()

    bt_dict1 = {
        'efh': 'floors < 2',
        'mfh': 'floors > 1',
    }
    heating_systems1 = [s for s in my.get().columns if "frac_" in s]
    remove_string1 = 'frac_'
    my.demand_by('total_loss_pres', heating_systems1, bt_dict1,
                 remove_string1)

    # my.data['demand'] = demand
    # gasheat = my.data.oeq.frac_natural_gas_heating
    # bins = np.arange(-10, 110, 10)
    # bins[11] = 101
    # bins[1] = 1
    # print(bins)
    # ind = np.digitize(gasheat, bins)
    # res = gasheat.groupby(ind).count()
    # print(res.sum())
    # print(my.data.oeq.index)
    # my.data.close()
    # my.data.open()
    # print(my.data)
    # print(my.data.oeq.total_loss_pres.sum())
    # print(my.data.demand.columns)
    # print(my.data.demand)
    print(my.dissolve('bezirk', 'demand_by').sum())
    print(my.get('building_types'))

    my.print()

    my.dissolve('bezirk', 'demand_by').plot(kind='bar')
    plt.show()
    print()

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

import pandas as pd
import os.path as path

GROUPED = path.join('data', 'powerplants', 'grouped', '{0}_cap.csv')


class PowerPlantsDE21:

    def __init__(self):
        self.cpp = pd.read_csv(GROUPED.format('conventional'),
                               index_col=[0, 1, 2])
        self.repp = pd.read_csv(GROUPED.format('renewable'),
                                index_col=[0, 1, 2, 3])

    def fuels(self):
        return list(self.cpp.index.get_level_values(0).unique())

    def cpp_region_fuel(self, year):
        return self.cpp.groupby(level=(1, 2, 0)).sum().loc[year]

    def repp_region_fuel(self, year):
        return self.repp.groupby(level=(1, 2, 0)).sum().loc[year]

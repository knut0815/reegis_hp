# -*- coding: utf-8 -*-
"""Creating heat demand profiles using the bdew method.
"""

import pandas as pd
import demandlib.bdew as bdew
from matplotlib import pyplot as plt
import datetime
import os
from oemof.outputlib import ResultsDataFrame

# read example temperature series
datapath = os.path.join(os.path.dirname(__file__), 'Temp_RE15_corr.csv')
temperature = pd.read_csv(datapath)["temp_air"]

def heat_example():
    holidays = {
        datetime.date(2013, 5, 24): 'Whit Monday',
        datetime.date(2013, 4, 5): 'Easter Monday',
        datetime.date(2013, 5, 13): 'Ascension Thursday',
        datetime.date(2013, 1, 1): 'New year',
        datetime.date(2013, 10, 3): 'Day of German Unity',
        datetime.date(2013, 12, 25): 'Christmas Day',
        datetime.date(2013, 5, 1): 'Labour Day',
        datetime.date(2013, 4, 2): 'Good Friday',
        datetime.date(2013, 12, 26): 'Second Christmas Day'}

    # Create DataFrame for 2013
    demand = pd.DataFrame(
        index=pd.date_range(pd.datetime(2013, 1, 1, 0), periods=8760, freq='H'))

    demand['efh'] = bdew.HeatBuilding(
        demand.index, holidays=holidays, temperature=temperature,
        shlp_type='EFH',
        building_class=3, wind_class=1, annual_heat_demand=2269.342,
        name='EFH').get_bdew_profile()

    demand['mfh'] = bdew.HeatBuilding(
        demand.index, holidays=holidays, temperature=temperature,
        shlp_type='MFH',
        building_class=3, wind_class=1, annual_heat_demand=2940.776,
        name='MFH').get_bdew_profile()

    demand['ghd'] = bdew.HeatBuilding(
        demand.index, holidays=holidays, temperature=temperature,
        shlp_type='ghd', wind_class=1, annual_heat_demand=1971.499,
        name='ghd').get_bdew_profile()

    # Plot demand of building
    ax = demand.plot()
    ax.set_xlabel("Date")
    ax.set_ylabel("Heat demand in MWh/1000EW")
    plt.show()

    date = str(datetime.datetime.now().strftime("%Y_%m_%d %H_%M_%S"))
    # file_name = ('scenario_' + nodes_flows.replace('.csv', '_') + date + '_' +
    #             'results_complete.csv')
    results_path = 'results'
    file_name = ("RE15_NRW"+"_"+ date + ".csv")
    os.path.join(results_path, file_name)
    demand.to_csv(os.path.join(results_path, file_name))

if __name__ == '__main__':
    heat_example()

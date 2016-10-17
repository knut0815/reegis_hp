import logging
from oemof import outputlib
from matplotlib import pyplot as plt
import oemof.solph as solph
import pandas as pd


def test_plots(berlin_e_system):
    logging.info('Plot the results')

    cdict = {'wind': '#5b5bae',
             'pv': '#ffde32',
             'storage': '#42c77a',
             'pp_gas': '#636f6b',
             'elec_demand': '#ce4aff',
             'slack_bus_el': '#42c77a',
             'excess_bus_el': '#555555',
             'wp': '#5b5bae',
             'slack_bus_wp': '#ffde32',
             'demand_wp': '#ce4aff'}

    # Plotting the input flows of the electricity bus for January
    myplot = outputlib.DataFramePlot(energy_system=berlin_e_system)
    myplot.slice_unstacked(bus_label="bus_el", type="to_bus")
    # colorlist = myplot.color_from_dict(cdict)
    myplot.plot(linewidth=2, title="January 2012")
    myplot.ax.legend(loc='upper right')
    myplot.ax.set_ylabel('Power in MW')
    myplot.ax.set_xlabel('Date')
    myplot.set_datetime_ticks(date_format='%d-%m-%Y', tick_distance=24*7)

    # Plotting the output flows of the electricity bus for January
    myplot.slice_unstacked(bus_label="bus_el", type="from_bus")
    myplot.plot(title="Year 2016", colormap='Spectral', linewidth=2)
    myplot.ax.legend(loc='upper right')
    myplot.ax.set_ylabel('Power in MW')
    myplot.ax.set_xlabel('Date')
    myplot.set_datetime_ticks()

    plt.show()

    # Plotting a combined stacked plot
    # fig = plt.figure()
    # plt.rc('legend', **{'fontsize': 19})
    # plt.rcParams.update({'font.size': 19})
    plt.style.use('grayscale')

    handles, labels = myplot.io_plot(
        bus_label='bus_el',
        cdict=cdict,
        # barorder=['pv', 'wind', 'pp_gas', 'storage'],
        # lineorder=['demand', 'storage', 'excess_bel'],
        line_kwa={'linewidth': 4},
        # ax=fig.add_subplot(1, 1, 1),
        date_from="2012-06-01 00:00:00",
        date_to="2012-06-8 00:00:00",
        )
    myplot.ax.set_ylabel('Power in MW')
    myplot.ax.set_xlabel('Date')
    myplot.ax.set_title("Electricity bus")
    myplot.set_datetime_ticks(tick_distance=24*30, date_format='%d-%m-%Y')
    myplot.outside_legend(handles=handles, labels=labels)

    plt.show()


def get_result_dict(energysystem):
    logging.info('Check the results')
    myresults = outputlib.DataFramePlot(energy_system=energysystem)

    pp_gas = myresults.slice_by(bus_label='bus_district_z', type='to_bus')
    pp_gas.unstack(level='obj_label').plot()
    plt.show()

    return pp_gas


def initialise_energy_system():
    logging.info("Creating energy system object.")
    time_index = pd.date_range('1/1/2012', periods=8784, freq='H')

    return solph.EnergySystem(time_idx=time_index, groupings=solph.GROUPINGS)


if __name__ == "__main__":
    berlin_e_sys = initialise_energy_system()
    berlin_e_sys.restore('/home/uwe/')
    get_result_dict(berlin_e_sys)
    # test_plots(berlin_e_sys)


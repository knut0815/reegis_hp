import logging
from oemof import outputlib
from matplotlib import pyplot as plt
import oemof.solph as solph
import pandas as pd
import pickle


def test_plots(results):
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
    myplot = outputlib.plot.ViewPlot(results)

    # colorlist = myplot.color_from_dict(cdict)
    myplot.plot('bus_el', linewidth=2, title="January 2012")
    myplot.ax.legend(loc='upper right')
    myplot.ax.set_ylabel('Power in MW')
    myplot.ax.set_xlabel('Date')
    myplot.set_datetime_ticks(date_format='%d-%m-%Y', tick_distance=24*30)

    # # Plotting the output flows of the electricity bus for January
    # myplot.slice_unstacked(bus_label="bus_el", type="from_bus")
    # myplot.plot(title="Year 2016", colormap='Spectral', linewidth=2)
    # myplot.ax.legend(loc='upper right')
    # myplot.ax.set_ylabel('Power in MW')
    # myplot.ax.set_xlabel('Date')
    # myplot.set_datetime_ticks()

    plt.show()

    # Plotting a combined stacked plot
    # fig = plt.figure()
    # plt.rc('legend', **{'fontsize': 19})
    # plt.rcParams.update({'font.size': 19})
    # plt.style.use('grayscale')
    myplot = outputlib.plot.ViewPlot(results, 'bus_el')
    myplot.slice_results(date_from=pd.datetime(2012, 6, 1),
                         date_to=pd.datetime(2012, 6, 8))

    myplot.io_plot(
        # cdict=cdict,
        # barorder=['pv', 'wind', 'pp_gas', 'storage'],
        # lineorder=['demand', 'storage', 'excess_bel'],
        line_kwa={'linewidth': 4}, smooth=True,
        # ax=fig.add_subplot(1, 1, 1),b
        )
    myplot.ax.set_ylabel('Power in MW')
    myplot.ax.set_xlabel('Date')
    myplot.ax.set_title("Electricity bus")
    myplot.set_datetime_ticks(tick_distance=24*2, date_format='%d-%m-%Y')
    myplot.outside_legend()

    plt.show()


def get_results():
    logging.info('Get the results')
    return pickle.load(open('data.pkl', 'rb'))


if __name__ == "__main__":
    res = get_results()
    test_plots(res)

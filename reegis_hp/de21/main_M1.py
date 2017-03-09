# -*- coding: utf-8 -*-

import os
import logging
import pandas as pd

import datetime
from datetime import datetime
from oemof.tools import logger
from oemof.solph import OperationalModel, EnergySystem
from oemof.solph import NodesFromCSV
from oemof.outputlib import ResultsDataFrame
import oemof.solph as solph
import matplotlib.pyplot as plt
from oemof import outputlib

scenario_RE = "RE15"
scenario_special = "_H&El"
comb_name_csv = (scenario_RE + scenario_special + ".csv")
comb_name_csv_seq = (scenario_RE + scenario_special+"_seq" + ".csv")
comb_name_results = (scenario_RE + scenario_special + "_res")
plot_data_start = "2013-03-10 00:00:00"
plot_data_finish = "2013-03-25 00:00:00"


def stopwatch():
    if not hasattr(stopwatch, 'now'):
        stopwatch.now = datetime.now()
        return None
    last = stopwatch.now
    stopwatch.now = datetime.now()
    return str(stopwatch.now-last)[0:-4]


def main(date_from, date_to, scenario_path, nodes_flows, nodes_flows_sequences):
    logger.define_logging()
    datetime_index = pd.date_range(date_from, date_to, freq='60min')

    es = EnergySystem(timeindex=datetime_index)

    NodesFromCSV(file_nodes_flows=os.path.join(scenario_path, nodes_flows),
                 file_nodes_flows_sequences=os.path.join(
                     scenario_path, nodes_flows_sequences), delimiter=',')
    stopwatch()

    om = OperationalModel(es)

    logging.info('OM creation time: ' + stopwatch())

    om.receive_duals()

    om.solve(solver='cbc', solve_kwargs={'tee': True})

    logging.info('Optimisation done.')

    logging.info('Optimisation time: ' + stopwatch())

    results = ResultsDataFrame(energy_system=es)

    if not os.path.isdir('results'):
        os.mkdir('results')

    date = str(datetime.now().strftime("%Y_%m_%d %H_%M"))
    file_name = (comb_name_results + date +
                '.csv')

    results_path = 'results'
    logging.info("Results stored to {0}".format(
        os.path.join(results_path, file_name)))
    results.to_csv(os.path.join(results_path, file_name))

    myplot = outputlib.DataFramePlot(energy_system=es)
    #Plot 1
    myplot.slice_unstacked(bus_label="B_DE150_hhg", type="to_bus",
                       date_from= plot_data_start,
                       date_to= plot_data_finish)
    myplot.plot(linewidth=2, title="January 2013")
    #Plot 2
    myplot.slice_unstacked(bus_label="B_DE150_hhg", type="from_bus",
                       date_from=plot_data_start,
                       date_to= plot_data_finish)
    myplot.plot(linewidth=2, title="January 2013")
    #Plot 3
    myplot.slice_unstacked(bus_label="B_DENI_hhg", type="to_bus",
                       date_from=plot_data_start,
                       date_to= plot_data_finish)
    myplot.plot(linewidth=2, title="January 2013")
    #Plot 4
    myplot.slice_unstacked(bus_label="B_DENRW_hhg", type="to_bus",
                       date_from=plot_data_start,
                       date_to= plot_data_finish)
    myplot.plot(linewidth=2, title="January 2013")
    #Plot 5
    myplot.slice_unstacked(bus_label="B_DE15_el", type="to_bus",
                       date_from=plot_data_start,
                       date_to= plot_data_finish)
    myplot.plot(linewidth=2, title="January 2013")
    #Plot 6
    myplot.slice_unstacked(bus_label="B_DE15_el", type="from_bus",
                       date_from=plot_data_start,
                       date_to= plot_data_finish)
    myplot.plot(linewidth=2, title="January 2013")

    plt.show()


if __name__ == "__main__":
    config = {'scenario_path': 'scenarios/',
              'date_from': '2013-03-01 00:00:00',
              'date_to': '2013-03-30 23:00:00',
              'nodes_flows':comb_name_csv,
              'nodes_flows_sequences':comb_name_csv_seq}

    main(**config)

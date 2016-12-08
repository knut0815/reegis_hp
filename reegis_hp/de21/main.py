# -*- coding: utf-8 -*-

import os
import logging
import pandas as pd

from datetime import datetime
from oemof.tools import logger
from oemof.solph import OperationalModel, EnergySystem
from oemof.solph import NodesFromCSV
from oemof.outputlib import ResultsDataFrame


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

    om.solve(solver='gurobi', solve_kwargs={'tee': True})

    logging.info('Optimisation done.')

    logging.info('Optimisation time: ' + stopwatch())

    results = ResultsDataFrame(energy_system=es)

    if not os.path.isdir('results'):
        os.mkdir('results')

    date = str(datetime.now())
    file_name = ('scenario_' + nodes_flows.replace('.csv', '_') + date + '_' +
                 'results_complete.csv')

    results_path = 'results'

    results.to_csv(os.path.join(results_path, file_name))
    logging.info("Results stored to {0}".format(
        os.path.join(results_path, file_name)))


if __name__ == "__main__":
    config = {'scenario_path': 'scenarios/',
              'date_from': '2015-01-01 00:00:00',
              'date_to': '2015-12-31 23:00:00',
              'nodes_flows': 'reegis_de_21_test.csv',
              'nodes_flows_sequences': 'reegis_de_21_test_seq.csv'}

    main(**config)

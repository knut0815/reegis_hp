import pandas as pd
import scenario_tools as sc
import os
import logging
from oemof.tools import logger
from reegis_hp.de21 import config as cfg
from oemof.solph import OperationalModel
from oemof.outputlib import ResultsDataFrame
# from shapely.wkt import loads as wkt_loads
# import powerplants as pp


def commodity_sources(round_nominal_value=True):
    """

    Parameters
    ----------
    round_nominal_value : boolean
        Will round the nominal_value entry to integer. Should be set to False
        if the nominal_values are small.

    Returns
    -------
    list : List of local commodity sources
    """
    # variable_costs = {
    #     'biomass_and_biogas': 27.73476,
    #     'hard_coal': 45.86634,
    #     'hydro': 0.0000,
    #     'lignite': 27.5949,
    #     'natural_gas': 54.05328,
    #     'nuclear': 5.961744,
    #     'oil': 86.86674,
    #     'other_fossil_fuels': 27.24696,
    #     'waste': 30.0000,
    # }
    commoditybuses = dict()

    def add_commodity_sources(fuel_type, reg, val):
        fuel_type = fuel_type.lower().replace(" ", "_")
        label = '{0}_resodurce_{1}'.format(reg, fuel_type)
        source = '{0}_resource_{1}'.format(reg, fuel_type)
        target_bus = '{0}_bus_{1}'.format(reg, fuel_type)
        idx = ('Source', label, source, target_bus)
        columns = ['nominal_value', 'summed_max', 'variable_costs',
                   'sort_index']
        if val.limit == float('inf'):
            val.limit = ''
            val.summed_max = ''
        else:
            if round_nominal_value:
                val.limit = round(float(val.limit))
            val.summed_max = 1.0

        values = [val.limit, val.summed_max, val.costs, '{0}_1'.format(region)]
        de21.add_parameters(idx, columns, values)

    # global commodity sources
    globalfile = os.path.join(cfg.get('paths', 'scenario_path'),
                              'commodity_sources_global.csv')
    if os.path.isfile(globalfile):
        global_sources = pd.read_csv(globalfile, index_col=[0])
        region = 'DE00'
        for fuel, value in global_sources.iterrows():
            add_commodity_sources(fuel, region, value)
        commoditybuses['global'] = [
            x.lower().replace(" ", "_") for x in global_sources.index]
    else:
        commoditybuses['global'] = list()

    # local commodity sources
    localfile = os.path.join(cfg.get('paths', 'scenario_path'),
                             'commodity_sources_local.csv')
    if os.path.isfile(localfile):
        local_sources = pd.read_csv(localfile, index_col=[0], header=[0, 1])
        local_fuel_types = local_sources.columns.get_level_values(0).unique()
        for fuel in local_fuel_types:
            for region, value in local_sources[fuel].iterrows():
                add_commodity_sources(fuel, region, value)
        local_sources.columns.get_level_values(0).unique()

        commoditybuses['local'] = [
            x.lower().replace(" ", "_") for x in local_fuel_types]
    else:
        commoditybuses['local'] = list()

    return commoditybuses


def transformer(com_buses, round_nominal_value=True):
    """
    Add transformer and connect them to their source bus.

    Use local_bus=True to connect the transformers to local buses. If you
    want to connect some transformers to local buses and some to global buses
    you have to call this function twice with different subsets of your
    DataFrame.
    """
    transf = pd.read_csv(os.path.join(cfg.get('paths', 'scenario_path'),
                                      'transformer.csv'),
                         index_col=[0], header=[0, 1])

    for fuel in transf.columns.get_level_values(0).unique():
        for reg, values in transf[fuel].iterrows():
            fuel_type = fuel.lower().replace(" ", "_")
            if fuel_type in com_buses['local']:
                busid = reg
            else:
                busid = 'DE00'
            label = '{0}_pp_{1}'.format(reg, fuel_type)
            source_bus = '{0}_bus_{1}'.format(busid, fuel_type)
            target_bus = '{0}_bus_el'.format(reg)
            idx1 = ('LinearTransformer', label, label, target_bus)
            idx2 = ('LinearTransformer', label, source_bus, label)
            cols1 = ['conversion_factors', 'nominal_value', 'sort_index']
            cols2 = ['sort_index']
            if round_nominal_value:
                values['capacity'] = round(values['capacity'])
            values1 = [round(values['efficiency'], 2),
                       values['capacity'],
                       '{0}_1_{1}a'.format(reg, fuel_type[:5])]
            values2 = '{0}_1_{1}b'.format(reg, fuel_type[:5])
            if values['capacity'] > 0:
                de21.add_parameters(idx1, cols1, values1)
                de21.add_parameters(idx2, cols2, values2)


def renewable_sources(round_nominal_value=True):
    """
    Add renewable sources.

    You have to pass the capacities (region, type) and the normalised feedin
    series (type, region)
    """
    seq = pd.read_csv(os.path.join(cfg.get('paths', 'scenario_path'),
                                   'sources_timeseries.csv'),
                      index_col=[0], header=[0, 1], parse_dates=True)
    seq.index = seq.index.tz_localize('UTC').tz_convert('Europe/Berlin')

    cap = pd.read_csv(os.path.join(cfg.get('paths', 'scenario_path'),
                                   'sources_capacity.csv'),
                      index_col=[0])

    for reg in cap.index:
        for vtype in cap.columns:
            vtype = vtype.lower().replace(" ", "_")
            capacity = float(cap.loc[reg, vtype])
            if round_nominal_value:
                capacity = round(capacity)
            label = '{0}_{1}'.format(reg, vtype)
            target = '{0}_bus_el'.format(reg)
            idx = ('Source', label, label, target)
            cols = ['nominal_value', 'actual_value', 'fixed', 'sort_index']
            values = [capacity, 'seq', 1, '{0}_2'.format(reg)]
            if capacity > 0:
                de21.add_parameters(idx, cols, values)
                idx = ['Source', label, label, target, 'actual_value']
                de21.add_sequences(idx, seq[reg, vtype])


def demand_sinks(round_nominal_value=True):
    """
    Add demand sinks.

    You have to pass the the time series for each region.
    """
    df = pd.read_csv(os.path.join(cfg.get('paths', 'scenario_path'),
                                  'demand.csv'),
                     index_col=[0], parse_dates=True)
    df.index = df.index.tz_localize('UTC').tz_convert('Europe/Berlin')

    for reg in df.columns:
        max_demand = df[reg].max()
        if round_nominal_value:
            max_demand = round(max_demand)
        label = '{0}_{1}'.format(reg, 'load')
        source = '{0}_bus_el'.format(reg)
        idx = ('Sink', label, source, label)
        cols = ['nominal_value', 'actual_value', 'fixed', 'sort_index']
        values = [max_demand, 'seq', 1, '{0}_3'.format(reg)]
        if max_demand > 0:
            de21.add_parameters(idx, cols, values)
            idx = ['Sink', label, source, label, 'actual_value']
            de21.add_sequences(idx, df[reg] / max_demand)


def storages(round_nominal_value=True):
    """Storages """
    df = pd.read_csv(os.path.join(cfg.get('paths', 'scenario_path'),
                                  'storages.csv'),
                     index_col=[0], parse_dates=True)
    for reg, values in df.iterrows():
        label = '{0}_storage'.format(reg)
        bus = '{0}_bus_el'.format(reg)
        idx1 = ('Storage', label, label, bus)
        idx2 = ('Storage', label, bus, label)
        cols1 = ['nominal_value', 'nominal_capacity',
                 'inflow_conversion_factor',
                 'outflow_conversion_factor', 'sort_index']
        cols2 = ['nominal_value', 'sort_index']
        if round_nominal_value:
            values['capacity'] = round(values['capacity'])
            values['max_in'] = round(values['max_in'])
            values['max_out'] = round(values['max_out'])
        values1 = [values.max_in, values.capacity,
                   round(values.efficiency_in, 2),
                   round(values.efficiency_out, 2),
                   '{0}_4a'.format(reg)]
        values2 = [values.max_out, '{0}_4b'.format(reg)]
        if values.capacity > 0:
            de21.add_parameters(idx1, cols1, values1)
            de21.add_parameters(idx2, cols2, values2)


def shortage_sources(shortage_regions, var_costs=1000):
    """Shortage sources"""
    for reg in shortage_regions:
        label = '{0}_{1}'.format(reg, 'shortage')
        idx = ('Source', label, label, '{0}_bus_el'.format(reg))
        cols = ['variable_costs', 'sort_index']
        values = [var_costs, '{0}_5a'.format(reg)]
        de21.add_parameters(idx, cols, values)


def excess_sinks(excess_regions):
    """Shortage sources"""
    for reg in excess_regions:
        label = '{0}_{1}'.format(reg, 'excess')
        idx = ('Sink', label, '{0}_bus_el'.format(reg), label)
        cols = ['sort_index']
        values = '{0}_5b'.format(reg)
        de21.add_parameters(idx, cols, values)


def powerlines(round_nominal_value=True):
    """Grid"""
    powerlinefile = os.path.join(cfg.get('paths', 'scenario_path'),
                                 'transmission.csv')

    if os.path.isfile(powerlinefile):
        df = pd.read_csv(powerlinefile, index_col=[0])

        de21.add_comment_line('POWERLINES', 'P_DE00_DE00_0')
        for line, value in df.iterrows():
            if round_nominal_value:
                value['capacity'] = round(value['capacity'])
            reg1, reg2 = line.split('-')
            connections = [(reg1, reg2), (reg2, reg1)]
            for from_reg, to_reg in connections:
                label = '{0}_{1}_powerline'.format(from_reg, to_reg)
                source_bus = '{0}_bus_el'.format(from_reg)
                target_bus = '{0}_bus_el'.format(to_reg)
                idx1 = ('LinearTransformer', label, label, target_bus)
                idx2 = ('LinearTransformer', label, source_bus, label)
                cols1 = ['conversion_factors', 'nominal_value', 'sort_index']
                cols2 = ['sort_index']
                values1 = [round(value.efficiency, 3),
                           value['capacity'],
                           'P_{0}_1a'.format(line)]
                values2 = 'P_{0}_1b'.format(line)
                if value['capacity'] > 0:
                    de21.add_parameters(idx1, cols1, values1)
                    de21.add_parameters(idx2, cols2, values2)


def create_objects_from_dataframe_collection():
    # Add objects to scenario tables
    de21.create_tables()
    logging.info("Add objects to scenario tables.")

    # Add comment lines to get a better overview
    de21.add_comment_line('GLOBAL RESOURCES', '0000_0')
    for r in regions:  # One comment line for every region
        de21.add_comment_line('{0}'.format(r), '{0}_0'.format(r))

    # Add objects
    commodity_buses = commodity_sources()
    transformer(commodity_buses)
    renewable_sources()
    demand_sinks()
    storages()
    shortage_sources(regions)
    excess_sinks(regions)
    powerlines()
    # Sort table and store it.
    logging.info("Sort and store files.")
    if write_table:
        de21.write_tables()


# Define default logger
logger.define_logging()
read_only = cfg.get('csv', 'read_only')
write_table = cfg.get('csv', 'write_table')
solver = cfg.get('general', 'solver')

cfg.set('paths', 'scenario_path', os.path.join(
    cfg.get('paths', 'scenario_data'),
    cfg.get('general', 'name').replace(' ', '_').lower()))

# Set path name and year for the basic scenario
my_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                       'my_scenarios')

my_name = 'de21_basic_uwe'
year = cfg.get('general', 'year')
datetime_index = pd.date_range('{0}-01-01 00:00:00'.format(year),
                               '{0}-12-31 23:00:00'.format(year),
                               freq='60min', tz='Europe/Berlin')
logging.info("Creating basic scenario '{0}' for {1} in {2}".format(
    my_name, year, my_path))

# Get list of regions from csv-file
regions = pd.read_csv(os.path.join(
    cfg.get('paths', 'geometry'),
    cfg.get('geometry', 'region_polygon_simple'))).gid

# Initialise scenario add empty tables
de21 = sc.SolphScenario(path=my_path, name=my_name, timeindex=datetime_index)

if read_only:
    logging.info("Reading scenario tables.")
else:
    create_objects_from_dataframe_collection()

logging.info("Creating nodes.")

de21.create_nodes()

logging.info("Creating OperationalModel")

om = OperationalModel(de21)

logging.info('OM created. Starting optimisation using {0}'.format(solver))

om.receive_duals()

om.solve(solver=solver, solve_kwargs={'tee': True})

logging.info('Optimisation done.')

results = ResultsDataFrame(energy_system=de21)

if not os.path.isdir('results'):
    os.mkdir('results')
date = '2017_03_21'
file_name = ('scenario_' + de21.name + date + '_' +
             'results_complete.csv')

results_path = 'results'

results.to_csv(os.path.join(results_path, file_name))
logging.info("Results stored to {0}".format(
    os.path.join(results_path, file_name)))
logging.info("Done")

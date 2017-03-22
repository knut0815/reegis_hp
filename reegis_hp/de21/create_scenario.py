import pandas as pd
import scenario_tools as sc
import os.path as path
import os
import demand
import feedin as feed
import logging
from oemof.tools import logger
import powerplants as pwrp
import grid
from oemof.solph import OperationalModel
from oemof.outputlib import ResultsDataFrame


def global_resources(fuel_list):
    """Add unlimited global resources."""
    variable_costs = {
        'biomass_and_biogas': 27.73476,
        'hard_coal': 45.86634,
        'hydro': 0.0000,
        'lignite': 27.5949,
        'natural_gas': 54.05328,
        'nuclear': 5.961744,
        'oil': 86.86674,
        'other_fossil_fuels': 27.24696,
        'waste': 30.0000,
    }
    for fuel in fuel_list:
        fuel_type = fuel.lower().replace(" ", "_")
        label = 'GL_resource_{0}'.format(fuel_type)
        source = 'GL_resource_{0}'.format(fuel_type)
        target_bus = 'GL_bus_{0}'.format(fuel_type)
        idx = ('Source', label, source, target_bus)
        columns = ['variable_costs', 'sort_index']
        values = [variable_costs[fuel_type], '0000_1']
        de21.add_parameters(idx, columns, values)


def transformer(df, local_bus=False):
    """
    Add transformer and connect them to their source bus.

    Use local_bus=True to connect the transformers to local buses. If you
    want to connect some transformers to local buses and some to global buses
    you have to call this function twice with different subsets of your
    DataFrame.
    """
    busid = 'GL'
    for reg in df.index.get_level_values(0).unique():
        if local_bus:
            busid = reg
        sub = df.loc[reg]
        for fuel, values in sub.iterrows():
            fuel_type = fuel.lower().replace(" ", "_")
            label = '{0}_pp_{1}'.format(reg, fuel_type)
            source_bus = '{0}_bus_{1}'.format(busid, fuel_type)
            target_bus = '{0}_bus_el'.format(reg)
            idx1 = ('LinearTransformer', label, label, target_bus)
            idx2 = ('LinearTransformer', label, source_bus, label)
            cols1 = ['conversion_factors', 'nominal_value', 'sort_index']
            cols2 = ['sort_index']
            values1 = [round(values['efficiency'], 2),
                       round(values['capacity']),
                       '{0}_1_{1}a'.format(reg, fuel_type[:5])]
            values2 = '{0}_1_{1}b'.format(reg, fuel_type[:5])
            if round(values['capacity']) > 0:
                de21.add_parameters(idx1, cols1, values1)
                de21.add_parameters(idx2, cols2, values2)


def renewable_sources(df, time_series):
    """
    Add renewable sources.

    You have to pass the capacities (region, type) and the normalised feedin
    series (type, region)
    """
    # TODO Das ist ja doof! Entweder beide region,type oder beide type,region!
    re_grouped = df.sortlevel()
    for reg in df.index.get_level_values(0).unique():
        for vtype in ['Solar', 'Wind']:
            if vtype in re_grouped.loc[reg].index:
                capacity = float(re_grouped.loc[(reg, vtype)].sum())
                label = '{0}_{1}'.format(reg, vtype.lower())
                target = '{0}_bus_el'.format(reg)
                idx = ('Source', label, label, target)
                cols = ['nominal_value', 'actual_value', 'fixed', 'sort_index']
                values = [round(capacity), 'seq', 1, '{0}_2'.format(reg)]
                if round(capacity) > 0:
                    de21.add_parameters(idx, cols, values)
                    idx = ['Source', label, label, target, 'actual_value']
                    de21.add_sequences(
                        idx, list(time_series[(vtype.lower(), reg)]))


def demand_sinks(df):
    """
    Add demand sinks.

    You have to pass the the time series for each region.
    """
    for reg in df.columns:
        max_demand = df[reg].max()
        label = '{0}_{1}'.format(reg, 'load')
        source = '{0}_bus_el'.format(reg)
        idx = ('Sink', label, source, label)
        cols = ['nominal_value', 'actual_value', 'fixed', 'sort_index']
        values = [round(max_demand), 'seq', 1, '{0}_3'.format(reg)]
        if round(max_demand) > 0:
            de21.add_parameters(idx, cols, values)
            de21.add_sequences(['Sink', label, source, label, 'actual_value'],
                               list(df[reg] / max_demand))


def shortage_sources(shortage_regions, var_costs=1000):
    """Shortage sources"""
    for reg in shortage_regions:
        label = '{0}_{1}'.format(reg, 'shortage')
        idx = ('Source', label, label, '{0}_bus_el'.format(reg))
        cols = ['variable_costs', 'sort_index']
        values = [var_costs, '{0}_4'.format(reg)]
        de21.add_parameters(idx, cols, values)


def excess_sinks(excess_regions):
    """Shortage sources"""
    for reg in excess_regions:
        label = '{0}_{1}'.format(reg, 'excess')
        idx = ('Sink', label, '{0}_bus_el'.format(reg), label)
        cols = ['sort_index']
        values = '{0}_5'.format(reg)
        de21.add_parameters(idx, cols, values)


def powerlines(df, efficiency=0.97):
    """Grid"""
    de21.add_comment_line('POWERLINES', 'P_DE00_DE00_0')
    for line, values in df.iterrows():
        line = line.replace('-', '_')
        from_reg, to_reg = line.split('_')
        label = '{0}_{1}_powerline'.format(from_reg, to_reg)
        source_bus = '{0}_bus_el'.format(from_reg)
        target_bus = '{0}_bus_el'.format(to_reg)
        idx1 = ('LinearTransformer', label, label, target_bus)
        idx2 = ('LinearTransformer', label, source_bus, label)
        cols1 = ['conversion_factors', 'nominal_value', 'sort_index']
        cols2 = ['sort_index']
        values1 = [round(efficiency, 2),
                   round(values['capacity']),
                   'P_{0}_1a'.format(line)]
        values2 = 'P_{0}_1b'.format(line)
        if round(values['capacity']) > 0:
            de21.add_parameters(idx1, cols1, values1)
            de21.add_parameters(idx2, cols2, values2)


# Define default logger
logger.define_logging()

# Set path name and year for the basic scenario
my_path = path.join(path.dirname(path.realpath(__file__)), 'my_scenarios')
my_name = 'de21_basic_uwe'
year = 2013
datetime_index = pd.date_range('{0}-01-01 00:00:00'.format(year),
                               '{0}-12-31 23:00:00'.format(year), freq='60min')
logging.info("Creating basic scenario '{0}' for {1} in {2}".format(
    my_name, year, my_path))

# Get list of regions from csv-file
regions = pd.read_csv(path.join(
    my_path, path.pardir, 'data', 'geometries', 'polygons_de21_simple.csv')).gid

# Initialise scenario add empty tables
de21 = sc.SolphScenario(path=my_path, name=my_name, timeindex=datetime_index)
de21.create_tables()

# Initialise power plants
pp = pwrp.PowerPlantsDE21()

# Add objects to scenario tables
logging.info("Add objects to scenario tables.")

# Add comment lines to get a better overview
de21.add_comment_line('GLOBAL RESOURCES', '0000_0')
for r in regions:  # One comment line for every region
    de21.add_comment_line('{0}'.format(r), '{0}_0'.format(r))

# Add objects
global_resources(pp.fuels())  # Todo: year?
transformer(pp.cpp_region_fuel(year), local_bus=False)
renewable_sources(pp.repp_region_fuel(year), feed.feedin_source_region(year))
demand_sinks(demand.get_demand_by_region(year))
shortage_sources(regions)
excess_sinks(regions)
powerlines(grid.get_grid())  # Todo: year?

# Sort table and store it.
logging.info("Sort and store files.")
de21.write_tables()

logging.info("Creating nodes.")

de21.create_nodes()

logging.info("Creating OperationalModel")

om = OperationalModel(de21)

logging.info('OM created.')

om.receive_duals()

om.solve(solver='gurobi', solve_kwargs={'tee': True})

logging.info('Optimisation done.')

results = ResultsDataFrame(energy_system=de21)

if not path.isdir('results'):
    os.mkdir('results')
date = '2017_03_21'
file_name = ('scenario_' + de21.name + date + '_' +
             'results_complete.csv')

results_path = 'results'

results.to_csv(os.path.join(results_path, file_name))
logging.info("Results stored to {0}".format(
    os.path.join(results_path, file_name)))
logging.info("Done")

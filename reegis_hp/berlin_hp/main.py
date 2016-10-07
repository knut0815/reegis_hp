# -*- coding: utf-8 -*-
"""
Created on Mon Apr 18 13:42:14 2016

@author: uwe
"""
import pandas as pd
import logging
# from matplotlib import pyplot as plt

# Default logger of oemof
from oemof.tools import logger
from oemof.tools import helpers

# import oemof base classes to create energy system objects
import oemof.solph as solph
import reegis_hp.berlin_hp.electricity as electricity
import reegis_hp.berlin_hp.heat as heat
import reegis_hp.berlin_hp.preferences as preferences
import reegis_hp.berlin_hp.create_objects as create_objects
import reegis_hp.berlin_hp.plot as plot

import os

# Define logger
logger.define_logging()


def initialise_energy_system():
    logging.info("Creating energy system object.")
    time_index = pd.date_range('1/1/2012', periods=8784, freq='H')

    return solph.EnergySystem(time_idx=time_index, groupings=solph.GROUPINGS)


def berlin_model(berlin_e_system):
    time_index = berlin_e_system.time_idx
    p = preferences.Basic()
    d = preferences.Data()

    logging.info("Adding objects to the energy system...")

    # Electricity
    bel = solph.Bus(label='bus_el')

    # Create sinks
    # Get normalise demand and maximum value of electricity usage
    electricity_usage = electricity.DemandElec(time_index)
    normalised_demand, max_demand = electricity_usage.solph_sink(resample='H')

    solph.Sink(label='elec_demand', inputs={bel: solph.Flow(
        actual_value=normalised_demand, fixed=True,
        nominal_value=max_demand * 10e+6)})

    heat_demand = heat.DemandHeat(time_index)

    heating_systems = [s for s in heat_demand.get().columns if "frac_" in s]
    remove_string = 'frac_'
    heat_demand.demand_by('total_loss_pres', heating_systems, d.bt_dict,
                          remove_string)

    heat_demand.df = heat_demand.dissolve('bezirk', 'demand_by', index=True)

    heat_demand.df = heat_demand.df.rename(
        columns={k: k.replace('frac_', '')
                 for k in heat_demand.df.columns.get_level_values(1)})

    for t in p.types:
        heat_demand.df[t] = (
            heat_demand.df[t].multiply(
                d.sanierungsanteil[t] * d.sanierungsreduktion[t]) +
            heat_demand.df[t].multiply(1 - d.sanierungsanteil[t]))

    # Add heating systems
    sum_wp = 25e+9
    sum_bhkw = 30e+9
    sum_existing = heat_demand.df.sum().sum()
    reduction = (sum_existing - (sum_wp + sum_bhkw)) / sum_existing
    frac_mfh = heat_demand.df.mfh.sum().sum() / heat_demand.df.sum().sum()
    new = {'efh': {'wp': sum_wp * (1 - frac_mfh),
                   'bhkw': sum_bhkw * (1 - frac_mfh)},
           'mfh': {'wp': sum_wp * frac_mfh,
                   'bhkw': sum_bhkw * frac_mfh}}
    heat_demand.df *= reduction

    # Join some categories
    ol = d.other_demand.pop('oil_light')
    oh = d.other_demand.pop('oil_heavy')
    oo = d.other_demand.pop('oil_other')
    for c in ['ghd', 'i']:
        d.other_demand['oil_heating'][c] = ol[c] + oh[c] + oo[c]
        d.other_demand['natural_gas_heating'][c] += d.other_demand[
            'liquid_gas'][c]
    d.other_demand.pop('liquid_gas')

    heat_demand.df.sortlevel(axis='columns', inplace=True)
    district_z = heat_demand.df.loc[:, (
        slice(None), 'district_heating')].multiply(d.fw_verteilung, axis=0).sum()
    district_dz = heat_demand.df.loc[:, (
        slice(None), 'district_heating')].multiply(d.fw_verteilung, axis=0).sum()

    dsum = heat_demand.df.sum()

    for b in ['efh', 'mfh']:
        dsum[b, 'district_dz'] = district_dz[b]['district_heating']
        dsum[b, 'district_z'] = district_z[b]['district_heating']
        dsum[b, 'bhkw'] = new[b]['bhkw']
        dsum[b, 'wp'] = new[b]['wp']

    dsum.drop('district_heating', 0, 'second', True)
    dsum.sort_index(inplace=True)

    dfull = d.other_demand

    for b in dsum.keys().levels[0]:
        for h in dsum[b].keys():
            split_h = '_'.join(h.split('_')[:-1])
            if h in dfull.keys():
                dfull[h][b] = dsum[b][h]
            elif split_h in dfull.keys():
                dfull[split_h][b] = dsum[b][h]
            else:
                dfull[h] = dict()
                dfull[h][b] = dsum[b][h]

    create_objects.heating_systems(berlin_e_system, dfull, p)

    mylist = list(berlin_e_system.groups.items())
    # Add excess and slack for every BUS

    for k, g in mylist:
        if isinstance(g, solph.Bus):
            solph.Sink(label='excess_{0}'.format(k),
                       inputs={g: solph.Flow(variable_costs=9000)})
            solph.Source(label='slack_{0}'.format(k),
                         outputs={g: solph.Flow(variable_costs=9000)})

    # sources
    source_costs = {'lignite': 90,
                    'natural_gas': 120,
                    'fuel_bio': 150,
                    'solar_thermal': 0,
                    'biomass': 140,
                    'oil': 130,
                    'coal': 100}

    for src in source_costs:
        if 'bus_' + src in berlin_e_system.groups:
            solph.Source(label=src, outputs={
                berlin_e_system.groups['bus_' + src]: solph.Flow(
                    variable_costs=source_costs[src])})
        else:
            logging.warning("No need for a {0} source.".format(src))

    # import pprint as pp
    # pp.pprint(berlin_e_system.groups)

    logging.info('Optimise the energy system')

    om = solph.OperationalModel(berlin_e_system)

    filename = os.path.join(
        helpers.extend_basic_path('lp_files'), 'storage_invest.lp')
    logging.info('Store lp-file in {0}.'.format(filename))
    om.write(filename, io_options={'symbolic_solver_labels': True})

    logging.info('Solve the optimization problem')
    om.solve(solver='gurobi', solve_kwargs={'tee': True})

    berlin_e_system.dump('/home/uwe/')
    return berlin_e_system

# **********************************
restore = True

if not restore:
    berlin_e_sys = berlin_model(initialise_energy_system())
else:
    berlin_e_sys = initialise_energy_system()
    berlin_e_sys.restore('/home/uwe/')

plot.test_plots(berlin_e_sys)

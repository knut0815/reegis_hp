# -*- coding: utf-8 -*-
"""
Reegis hp main app.
"""
import pandas as pd
import logging
# from matplotlib import pyplot as plt

# Default logger of oemof
from oemof.tools import logger
from oemof.tools import helpers
from oemof import solph
from oemof import outputlib

# import oemof base classes to create energy system objects
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

    return solph.EnergySystem(timeindex=time_index, groupings=solph.GROUPINGS)


def berlin_model(berlin_e_system):
    """

    Parameters
    ----------
    berlin_e_system : solph.EnergySystem

    Returns
    -------

    """
    time_index = berlin_e_system.timeindex
    p = preferences.Basic()
    d = preferences.Data()

    logging.info("Adding objects to the energy system...")

    # Electricity Bus
    solph.Bus(label='bus_el')

    heat_demand = heat.DemandHeat(time_index)
    heating_systems = [s for s in heat_demand.get().columns if "frac_" in s]

    remove_string = 'frac_'
    heat_demand.demand_by('total_loss_pres', heating_systems, d.bt_dict,
                          remove_string, percentage=True)
    heat_demand.print(table='oeq')
    heat_demand.df = heat_demand.dissolve('bezirk', 'demand_by', index=True)
    print(heat_demand.df)
    exit()
    heat_demand.df = heat_demand.df.rename(
        columns={k: k.replace('frac_', '')
                 for k in heat_demand.df.columns.get_level_values(1)})

    for t in p.types:
        heat_demand.df[t] = (
            heat_demand.df[t].multiply(
                d.sanierungsanteil[t] * d.sanierungsreduktion[t]) +
            heat_demand.df[t].multiply(1 - d.sanierungsanteil[t])) * 1000

    ep = dict()
    ep['basic'] = pd.read_csv('/home/uwe/e_p.csv', ';')
    ep['stromanteil'] = pd.read_csv('/home/uwe/stromanteil_e_p.csv', ';')

    fraction_heating_system_saniert = {
        'off-peak_electricity_heating': 0,
        'district_heating': 0.6,
        'natural_gas_heating': 0.4,
        'oil_heating': 0.4,
        'coal_stove': 0,
        'wp': 1,
    }

    fraction_electrical_dhw = {
        'off-peak_electricity_heating': 1,
        'district_heating': 0.11,
        'natural_gas_heating': 0.09,
        'oil_heating': 0.58,
        'coal_stove': 1,
        'wp': 0,
    }
    ep_mix = dict()
    for e in ep.keys():
        ep_mix[e] = dict()
        for b in p.types:
            ep_mix[e][b] = dict()
            cols = [x.replace('_int_DHW', '') for x in ep[e].columns]
            cols = set([x.replace('_el_DHW', '') for x in cols])
            cols.remove('gtype')
            cols.remove('building')
            cols.remove('heating_system')
            for h in cols:
                tmp = dict()
                for bs in ['saniert', 'unsaniert']:
                    tmp[bs] = dict()
                    for hs in ['saniert', 'unsaniert']:
                        qu = 'gtype=="{0}"'.format(b.upper())
                        qu += ' and building=="{0}"'.format(bs)
                        qu += ' and heating_system=="{0}"'.format(hs)
                        # Mix internal DHW and electrical DHW
                        ep[e].ix[(ep[e].gtype == b.upper()) &
                                 (ep[e].building == bs) &
                                 (ep[e].heating_system == hs), h] = (
                            ep[e].query(qu)[h + '_int_DHW'] *
                            (1 - fraction_electrical_dhw[h]) +
                            ep[e].query(qu)[h + '_el_DHW'] *
                            fraction_electrical_dhw[h])
                        tmp[bs][hs] = ep[e].query(qu)[h]
                ep_mix[e][b][h] = (
                    float(tmp['saniert']['saniert']) *
                    d.sanierungsanteil[b] *
                    fraction_heating_system_saniert[h] +
                    float(tmp['saniert']['unsaniert']) *
                    d.sanierungsanteil[b] *
                    (1 - fraction_heating_system_saniert[h]) +
                    float(tmp['unsaniert']['saniert']) *
                    (1 - d.sanierungsanteil[b]) *
                    fraction_heating_system_saniert[h] +
                    float(tmp['unsaniert']['unsaniert']) *
                    (1 - d.sanierungsanteil[b]) *
                    (1 - fraction_heating_system_saniert[h]))

    add_dict = {
        'district_dz': 'district_heating',
        'district_z': 'district_heating',
        'bhkw': 'district_heating',
    }

    for e in ep_mix.keys():
        for b in ep_mix[e].keys():
            for new_key in add_dict.keys():
                ep_mix[e][b][new_key] = ep_mix[e][b][add_dict[new_key]]

    # Add heating systems
    sum_wp = 6.42e+10  # Bei 2000 Volllaststunden
    sum_bhkw = 6.75e+11  # Bei 2000 Volllaststunden
    # sum_wp = 50e+9
    # sum_bhkw = 50e+9
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
    # noinspection PyTypeChecker
    district_z = heat_demand.df.loc[:, (
        slice(None), 'district_heating')].multiply(
        d.fw_verteilung, axis=0).sum()
    # noinspection PyTypeChecker
    district_dz = heat_demand.df.loc[:, (
        slice(None), 'district_heating')].multiply(
        (1 - d.fw_verteilung), axis=0).sum()

    dsum = heat_demand.df.sum()

    for b in ['efh', 'mfh']:
        dsum[b, 'district_dz'] = district_dz[b]['district_heating']
        dsum[b, 'district_z'] = district_z[b]['district_heating']
        dsum[b, 'bhkw'] = new[b]['bhkw']
        dsum[b, 'wp'] = new[b]['wp']

    dsum.drop('district_heating', 0, 'second', True)
    dsum.sort_index(inplace=True)

    ew = pd.read_csv('/home/uwe/chiba/RLI/data/stadtnutzung_erweitert.csv')[
        ['ew', 'schluessel_planungsraum']]
    grp = ew.schluessel_planungsraum.astype(str).str[:-8]
    grp = grp.apply(lambda x: '{0:0>2}'.format(x))
    ew = ew.groupby(grp).sum().drop('schluessel_planungsraum', 1)
    # dhw_profile = pd.read_csv('/home/uwe/dhw_demand.csv')
    # *ew.sum() * 657
    dhw = ew.sum() * 657000  # 657000 Wh pro EW

    dhw_factor = (dsum.sum().sum() + float(dhw)) / dsum.sum().sum()
    dsum *= dhw_factor

    dfull = d.other_demand
    aux_elec = dict()
    sum_aux = 0
    print(ep_mix)
    for b in dsum.keys().levels[0]:
        for h in dsum[b].keys():
            dfull.setdefault(h, dict())
            aux_elec.setdefault(h, dict())
            aux_elec[h][b] = (dsum[b][h] * ep_mix['basic'][b][h] *
                              ep_mix['stromanteil'][b][h] / 100)
            print("{:.2E}".format(aux_elec[h][b]))
            sum_aux += aux_elec[h][b]
            dfull[h][b] = dsum[b][h] * ep_mix['basic'][b][h] - aux_elec[h][b]
    # print(dfull)
    # e = 0
    # for a in dfull.keys():
    #     for b in dfull[a].keys():
    #         if b in ['i']:
    #             print(a, b, dfull[a][b])
    #             e += dfull[a][b]
    # print(e)
    # exit(0)
    create_objects.heating_systems(berlin_e_system, dfull, aux_elec, p)

    mylist = list(berlin_e_system.groups.items())
    # Add excess and slack for every BUS

    for k, g in mylist:
        if isinstance(g, solph.Bus):
            solph.Sink(label='excess_{0}'.format(k),
                       inputs={g: solph.Flow(variable_costs=9000)})
            solph.Source(label='slack_{0}'.format(k),
                         outputs={g: solph.Flow(variable_costs=9000)})
    # slacks = ['bus_el', 'bus_district_z', 'bus_district_dz']
    # for s in slacks:
    #     obj = berlin_e_system.groups[s]
    #     solph.Source(label='slack_{0}'.format(s),
    #                  outputs={obj: solph.Flow(variable_costs=9000)})

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

    om = solph.Model(berlin_e_system)

    filename = os.path.join(
        helpers.extend_basic_path('lp_files'), 'storage_invest.lp')
    logging.info('Store lp-file in {0}.'.format(filename))
    om.write(filename, io_options={'symbolic_solver_labels': True})

    logging.info('Solve the optimization problem')
    om.solve(solver='cbc', solve_kwargs={'tee': True})

    berlin_e_system.dump('/home/uwe/')
    return om

# **********************************


import pickle

plot_only = False

if not plot_only:
    opmodel = berlin_model(initialise_energy_system())
    results = outputlib.processing.results(opmodel)
    pickle.dump(results, open('data.pkl', 'wb'), -1)
else:
    results = pickle.load(open('data.pkl', 'rb'))

plot.test_plots(results)

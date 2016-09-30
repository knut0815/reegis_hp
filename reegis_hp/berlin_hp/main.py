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

# Demandlib
import demandlib.bdew as bdew

# import oemof base classes to create energy system objects
import oemof.solph as solph
import reegis_hp.berlin_hp.electricity as electricity
import reegis_hp.berlin_hp.heat as heat

import oemof.db as db

# Define logger
logger.define_logging()

# Dictionaries
heating2resource = {
    'natural_gas_heating': 'natural_gas',
    'off-peak_electricity_heating': 'bel',
    'district_heating': '',
    'oil_heating': 'oil',
    'coal_stove': 'lignite',
    }

# parameter
number_of_district_heating_systems = 2

# Define energy system
logging.info("Creating energy system object.")
time_index = pd.date_range('1/1/2012', periods=8784, freq='H')
berlin_e_system = solph.EnergySystem(time_idx=time_index)

logging.info("Adding objects to the energy system...")

# Electricity
bel = solph.Bus(label='bel')

# Natural gas
solph.Bus(label='natural_gas')

# Oil
solph.Bus(label='oil')

# Coal
solph.Bus(label='coal')

# Lignite
solph.Bus(label='lignite')

# Biomass
solph.Bus(label='biomass')

# Create sinks
# # Get normalise demand and maximum value of electricity usage
# electricity_usage = electricity.DemandElec(time_index)
# normalised_demand, max_demand = electricity_usage.solph_sink(resample='H')
# solph.Sink(label='elec_demand', inputs={bel: solph.Flow(
#     actual_value=normalised_demand, fixed=True,
#     nominal_value=max_demand)})

heat_demand = heat.DemandHeat(time_index)

types = ['mfh', 'efh']

bt_dict = {
        'efh': 'floors < 2',
        'mfh': 'floors > 1',
    }

sanierungsanteil = {'efh': 0.2,
                    'mfh': 0.2}

sanierungsreduktion = {'efh': 0.5,
                       'mfh': 0.5}

# tmp = heat_demand.get(columns=['total_trans_loss_pres',
#                                'air_change_heat_loss'])
# transmission_reduced = (
#     tmp.total_trans_loss_pres * sanierungsanteil * sanierungsreduktion +
#     tmp.total_trans_loss_pres * (1 - sanierungsanteil))
#
# heat_demand.set(transmission_reduced + tmp.air_change_heat_loss, 'total')
# from matplotlib import pyplot as plt
# heat_demand.get(columns='total').plot()
# plt.show()
# print(heat_demand.get(columns='total'))

heating_systems = [s for s in heat_demand.get().columns if "frac_" in s]
remove_string = 'frac_'
heat_demand.demand_by('total_loss_pres', heating_systems, bt_dict,
                      remove_string)

dby = heat_demand.dissolve('bezirk', 'demand_by')

for t in types:
    print('t', t)
    c = [x for x in dby.columns if t in x]
    dby[c] = (
        dby[c].multiply(sanierungsanteil[t] * sanierungsreduktion[t]) +
        dby[c].multiply(1 - sanierungsanteil[t]))

temperature_path = '/home/uwe/rli-lokal/git_home/demandlib/examples'
temperature_file = temperature_path + '/example_data.csv'
temperature = pd.read_csv(temperature_file)['temperature']
sli = pd.Series(list(temperature.loc[:23]), index=list(range(8760, 8784)))
temperature = temperature.append(sli)

heating_systems.remove('frac_district_heating')
heatbus = dict()
hd = dict()
for hstype in heating_systems:
    hstype = hstype.replace('frac_', '')
    hd[hstype] = 0

    for key in bt_dict.keys():
        column = '_'.join(['demand', key, hstype])
        hd[hstype] += bdew.HeatBuilding(
            time_index, temperature=temperature, shlp_type=key,
            building_class=1, wind_class=1,
            annual_heat_demand=heat_demand_by[column], name=key
        ).get_bdew_profile()

    # print(hd[hstype].max())
    # from matplotlib import pyplot as plt
    # hd[hstype].div(hd[hstype].max()).plot()
    # plt.show()
    heatbus[hstype] = solph.Bus(label='bus_' + hstype)

    solph.Sink(label='sink_' + hstype, inputs={heatbus[hstype]: solph.Flow(
        actual_value=hd[hstype].div(hd[hstype].max()), fixed=True,
        nominal_value=hd[hstype].max())})

    solph.LinearTransformer(
            label=hstype,
            inputs={berlin_e_system.groups[heating2resource[hstype]]:
                    solph.Flow()},
            outputs={heatbus[hstype]: solph.Flow(
                nominal_value=10e10,
                variable_costs=0)},
            conversion_factors={bel: 0.58})

for n in range(number_of_district_heating_systems):
    hstype = 'district_heating_' + str(n)
    hd[hstype] = 0

    heatbus[hstype] = solph.Bus(label='bus_' + hstype)

    for key in bt_dict.keys():
        column = '_'.join(['demand', key, 'district_heating'])
        hd[hstype] += bdew.HeatBuilding(
            time_index, temperature=temperature, shlp_type=key,
            building_class=1, wind_class=1,
            annual_heat_demand=(heat_demand_by[column]
                                / number_of_district_heating_systems),
            name=key
        ).get_bdew_profile()

    solph.Sink(label='sink_' + hstype, inputs={heatbus[hstype]: solph.Flow(
        actual_value=hd[hstype].div(hd[hstype].max()), fixed=True,
        nominal_value=hd[hstype].max())})

    solph.LinearTransformer(
        label='pp_chp',
        inputs={berlin_e_system.groups['natural_gas']: solph.Flow()},
        outputs={bel: solph.Flow(nominal_value=30, variable_costs=42),
                 heatbus[hstype]: solph.Flow(nominal_value=40)},
        conversion_factors={bel: 0.3,
                            heatbus[hstype]: 0.4})

# Create sources

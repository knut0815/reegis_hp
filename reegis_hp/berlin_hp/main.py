# -*- coding: utf-8 -*-
"""
Created on Mon Apr 18 13:42:14 2016

@author: uwe
"""
import pandas as pd
import logging
from matplotlib import pyplot as plt

# Default logger of oemof
from oemof.tools import logger

# import oemof base classes to create energy system objects
import oemof.solph as solph
import reegis_hp.berlin_hp.data as data

# Define logger
logger.define_logging()

# parameter
number_of_district_heating_systems = 5

# Define energy system
logging.info("Creating energy system object.")
time_index = pd.date_range('1/1/2012', periods=8760, freq='H')
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

# Create district heat buses
for n in range(number_of_district_heating_systems):
    solph.Bus(label='distr' + str(n + 1))

# Create sinks
demand = data.get_electricity_usage()
max_demand = demand.max()
demand = demand.div(max_demand)
solph.Sink(label='elec_demand', inputs={bel: solph.Flow(
    actual_value=demand, fixed=True, nominal_value=max_demand)})

# Create sources

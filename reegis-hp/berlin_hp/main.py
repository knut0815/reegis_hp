# -*- coding: utf-8 -*-
"""
Created on Mon Apr 18 13:42:14 2016

@author: uwe
"""

# Outputlib
from oemof.outputlib import to_pandas as tpd

# Default logger of oemof
from oemof.tools import logger

# import oemof base classes to create energy system objects
import logging
import pandas as pd
import matplotlib.pyplot as plt
from oemof.core import energy_system as core_es
import oemof.solph as solph
from oemof.solph import (Bus, Source, Sink, Flow, LinearTransformer, Storage)
from oemof.solph.network import Investment
from oemof.solph import OperationalModel


# Define logger
logger.define_logging()

# parameter
number_of_district_heating_systems = 5

# Define energy system
logging.info("Creating energy system object.")
time_index = pd.date_range('1/1/2012', periods=8760, freq='H')
simulation = es.Simulation(
    timesteps=range(len(time_index)), verbose=True, solver='glpk',
    objective_options={'function': predefined_objectives.minimize_cost})
berlin_e_system = es.EnergySystem(time_idx=time_index, simulation=simulation)

logging.info("Adding objects to the energy system...")

# Create buses
es_dict = {'bus': {}}

# Electricity
es_dict['bus']['el'] = bel = Bus(label="electricity")

# Natural gas
es_dict['bus']['ngas'] = Bus(label="natural_gas")

# Oil
es_dict['bus']['oil'] = Bus(label='oil')

# Coal
es_dict['bus']['coal'] = Bus(label='coal')

# Lignite
es_dict['bus']['lignite'] = Bus(label='lignite')

# Biomass
es_dict['bus']['biom'] = Bus(label='biomass')

# Create district heat buses
for n in range(number_of_district_heating_systems):
    label_string = 'distr' + str(n + 1)
    es_dict['bus'][label_string] = Bus(label=label_string)

# Create sources

# Create sinks

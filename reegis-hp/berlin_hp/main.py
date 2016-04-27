# -*- coding: utf-8 -*-
"""
Created on Mon Apr 18 13:42:14 2016

@author: uwe
"""

import pandas as pd
import logging

# import solph module to create/process optimization model instance
from oemof.solph import predefined_objectives as predefined_objectives

# Default logger of oemof
from oemof.tools import logger

# import oemof base classes to create energy system objects
from oemof.core import energy_system as es
from oemof.core.network.entities import Bus as bus
from oemof.core.network.entities.components import sinks as sink
from oemof.core.network.entities.components import sources as source
from oemof.core.network.entities.components import transformers as transformer


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

es_dict = {}

# Create buses
es_dict['bus'] = {}

# Electricity
es_dict['bus']['el'] = bus(uid='bel', type='el')

# Natural gas
es_dict['bus']['ngas'] = bus(uid='bngas', type='ngas')

# Oil
es_dict['bus']['oil'] = bus(uid='boil', type='oil')

# Coal
es_dict['bus']['coal'] = bus(uid='bcoaloil', type='coal')

# Lignite
es_dict['bus']['lignite'] = bus(uid='blignite', type='lignite')

# Biomass
es_dict['bus']['biom'] = bus(uid='bbiom', type='biomass')

# Create district heat buses
for n in range(number_of_district_heating_systems):
    uid = 'distr' + str(n + 1)
    es_dict['bus'][uid] = bus(uid='b' + uid, type='heat')

# Create sources

# Create sinks

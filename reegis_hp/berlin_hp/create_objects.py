# -*- coding: utf-8 -*-

# Demandlib
import logging

import oemof.solph as solph

import pandas as pd

import demandlib.bdew as bdew
import demandlib.particular_profiles as pprofiles
import reegis_hp.berlin_hp.prepare_data as prepare_data


def heating_systems(esystem, dfull, p):
    power_plants = prepare_data.chp_berlin(p)

    time_index = esystem.time_idx
    temperature_path = '/home/uwe/rli-lokal/git_home/demandlib/examples'
    temperature_file = temperature_path + '/example_data.csv'
    temperature = pd.read_csv(temperature_file)['temperature']
    sli = pd.Series(list(temperature.loc[:23]), index=list(range(8760, 8784)))
    temperature = temperature.append(sli)

    temperature = temperature.iloc[0:len(time_index)]
    heatbus = dict()
    hd = dict()

    for h in dfull.keys():
        hd.setdefault(h, 0)
        lsink = 'demand_{0}'.format(h)
        lbus = 'bus_{0}'.format(h)
        ltransf = '{0}'.format(h)
        lres_bus = 'bus_{0}'.format(p.heating2resource[h])

        for b in dfull[h].keys():
            if b.upper() in p.bdew_types:
                bc = 0
                if b.upper() in ['EFH', 'MFH']:
                    bc = 1
                hd[h] += bdew.HeatBuilding(
                    time_index, temperature=temperature, shlp_type=b,
                    building_class=bc, wind_class=1,
                    annual_heat_demand=dfull[h][b], name=h
                ).get_bdew_profile()
            elif b in ['i', ]:
                hd[h] += pprofiles.IndustrialLoadProfile(
                    time_index).simple_profile(annual_demand=dfull[h][b])
            else:
                logging.error('Demandlib typ "{0}" not found.'.format(b))
        heatbus[h] = solph.Bus(label=lbus)

        solph.Sink(label=lsink, inputs={heatbus[h]: solph.Flow(
            actual_value=hd[h].div(hd[h].max()), fixed=True,
            nominal_value=hd[h].max())})

        if 'district' not in h:
            if lres_bus not in esystem.groups:
                solph.Bus(label=lres_bus)
            solph.LinearTransformer(
                label=ltransf,
                inputs={esystem.groups[lres_bus]: solph.Flow()},
                outputs={heatbus[h]: solph.Flow(
                    nominal_value=hd[h].max(),
                    variable_costs=0)},
                conversion_factors={heatbus[h]: 1})
        else:
            for pp in power_plants[h].index:
                lres_bus = 'bus_' + pp
                if lres_bus not in esystem.groups:
                    solph.Bus(label=lres_bus)
                solph.LinearTransformer(
                    label='pp_chp_{0}_{1}'.format(h, pp),
                    inputs={esystem.groups[lres_bus]: solph.Flow()},
                    outputs={
                        esystem.groups['bus_el']: solph.Flow(
                            nominal_value=power_plants[h]['power_el'][pp]),
                        heatbus[h]: solph.Flow(
                            nominal_value=power_plants[h]['power_th'][pp])},
                    conversion_factors={esystem.groups['bus_el']: 0.3,
                                        heatbus[h]: 0.4})

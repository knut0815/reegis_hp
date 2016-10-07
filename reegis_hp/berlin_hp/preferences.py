# -*- coding: utf-8 -*-

import pandas as pd


class Basic:
    def __init__(self):
        self.types = ['mfh', 'efh']

        self.bdew_types = ['GMF', 'GPD', 'GHD', 'GWA', 'GGB', 'EFH', 'GKO',
                           'MFH', 'GBD', 'GBA', 'GMK', 'GBH', 'GGA', 'GHA']

        self.heating2resource = {
            'natural_gas_heating': 'natural_gas',
            'off-peak_electricity_heating': 'el',
            'district_heating': '',
            'oil_heating': 'oil',
            'coal_stove': 'lignite',
            'wp': 'el',
            'bhkw': 'natural_gas',
            'district_z': 'main_heat_network',
            'district_dz': 'sub_heat_network',
            'fuel_bio_heating': 'fuel_bio',
            'biomass_heating': 'biomass',
            'solar_thermal_heating': 'solar_thermal',
            'lignite_heating': 'lignite',
            }

        self.trans = {
            'Erdgas': 'natural_gas',
            'erdgas': 'natural_gas',
            'Holz': 'biomass',
            'Steinkohle': 'coal',
            'braunkohle': 'lignite',
            'heizoel': 'oil',
            'steinkohle': 'coal',
            'biogas': 'biomass',
            'biomasse': 'biomass',
            'strom': 'el',
            'öl': 'oil',
        }


class Data:
    def __init__(self):
        self.fw_verteilung = pd.Series({
            '01': 100,
            '02': 100,
            '03': 30,
            '04': 100,
            '05': 100,
            '06': 90,
            '07': 100,
            '08': 0,
            '09': 40,
            '10': 100,
            '11': 100,
            '12': 0
        }).div(100)

        self.other_demand = {
            'coal_stove': {'ghd': 177.7792, 'i': 0},
            'lignite_heating': {'ghd': 42578.1184, 'i': 22902.961},
            'oil_light': {'ghd': 2680921.4472, 'i': 668199.79},
            'oil_heavy': {'ghd': 0, 'i': 236.113},
            'oil_other': {'ghd': 553.33776, 'i': 0},
            'oil_heating': dict(),
            'liquid_gas': {'ghd': 0, 'i': 944.452},
            'natural_gas_heating': {'ghd': 11129622.3696, 'i': 983174.532},
            'solar_thermal_heating': {'ghd': 10200.0816, 'i': 0},
            'biomass_heating': {'ghd': 0, 'i': 216279.508},
            'fuel_bio_heating': {'ghd': 29041.899, 'i': 0},
            'district_z': {'ghd': 205557.2, 'i': 243779.728},
        }

        self.bt_dict = {
            'efh': 'floors < 2',
            'mfh': 'floors > 1',
        }

        self.sanierungsanteil = {'efh': 0.2,
                                 'mfh': 0.2}

        self.sanierungsreduktion = {'efh': 0.5,
                                    'mfh': 0.5}

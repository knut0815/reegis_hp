import pandas as pd
import geopandas as gpd
import datetime
import logging
import os

import reegis_hp.berlin_hp.config as cfg
import reegis_hp.de21.demand as de21_demand
import oemof.tools.logger as logger


def create():
    year = 2013
    start = datetime.datetime.now()
    logging.info("Starting...")

    # Get filenames for needed file from config file

    # allocation of district heating systems (map) to groups (model)
    district_heating_groups = cfg.get_dict('district_heating_systems')

    # heat demand for each building from open_equarter
    filename_oeq_results = os.path.join(cfg.get('paths', 'oeq'),
                                        cfg.get('oeq', 'results'))
    data_oeq = pd.read_hdf(filename_oeq_results, 'oeq')

    # A file with a heat factor for each building type of the alkis
    # classification. Buildings like garages etc get the heat-factor 0. It is
    # possible to define building factors between 0 and 1.
    filename_heat_factor = os.path.join(cfg.get('paths', 'static'),
                                        'heat_factor_by_building_type.csv')
    heat_factor = pd.read_csv(filename_heat_factor, index_col=[0])

    # Heat demand from energy balance (de21)
    heat_reference = de21_demand.heat_demand(year).loc['BE'].sum().sum() / 3.6

    # TODO: Hier muss noch eine Ort her
    # Read map with areas of district heating systems in Berlin
    path = '/home/uwe/chiba/Promotion/Statstik/Fernwaerme/Fernwaerme_2007'
    fw_map = gpd.read_file(os.path.join(path, 'district_heat_blocks.shp'))

    # Create translation Series with STIFT (numeric) and KLASSENNAM (text)
    stift2name = fw_map.groupby(['STIFT', 'KLASSENNAM']).size().reset_index(
        level='KLASSENNAM')['KLASSENNAM']
    stift2name[0] = 'unknown'  # add description 'unknown' to STIFT 0

    # Replace alphanumeric code from block id
    fw_map['gml_id'] = fw_map['gml_id'].str.replace('s_ISU5_2015_UA.', '')

    # Every building has a block id from the block the building is located.
    # Every block that touches a district heating area has the STIFT (number) of
    # this district heating system. By merging this information every building
    # gets the STIFT (number) of the district heating area.
    data = data_oeq.merge(fw_map[['gml_id', 'STIFT']], left_on='block',
                          right_on='gml_id', how='left')

    # cols = ['air_change_heat_loss', 'total_trans_loss_pres',
    #         'total_trans_loss_contemp', 'total_loss_pres',
    #         'total_loss_contemp', 'HLAC', 'HLAP', 'AHDC', 'AHDP', 'total']

    frac_cols = [x for x in data.columns if 'frac_' in x]

    data['check'] = data[frac_cols].sum(axis=1)

    data.loc[data['check'] > 95, frac_cols] = (
        data.loc[data['check'] > 95, frac_cols].multiply(
            (100 / data.loc[data['check'] > 95, 'check']), axis=0))
    data['check'] = data[frac_cols].sum(axis=1)

    length = len(data.loc[round(data['check']) == 100, frac_cols])
    s = data.loc[data['check'] > 95, frac_cols].sum()/length

    data.loc[data['check'] < 1, frac_cols] = data.loc[data['check'] < 1, frac_cols] + s
    data['check'] = data[frac_cols].sum(axis=1)
    print(data['check'])
    exit(0)
    # print(data['total'].sum() / 1000 / 1000 / 1000)
    del heat_factor['gebaeude_1']
    data = data.merge(heat_factor, left_on='building_function', right_index=True)
    print(data['total'].sum())
    data['total'] *= data['heat_factor']
    factor = bilanz / (data['total'].sum() / 1000 / 1000)
    print("faktor:", factor)
    data['total'] = data['total'] * factor
    data['tot_gud'] = data['total'] * data['gud']
    data['tot_hh'] = data['total'] * data['hh']
    print(data['tot_gud'].sum())
    print(data['tot_hh'].sum())
    print(data['total'].sum())
    # print(data['total'].sum() / 1000 / 1000 / 1000)
    data[frac_cols] = data[frac_cols].multiply(data['total'] * 0.01, axis=0)
    # print((data['total'].sum() - data['frac_elec'].sum()) / 1000 / 1000 / 1000)
    # print(data[frac_cols].sum() / 1000 / 1000 / 1000)
    # print(data[frac_cols].sum().sum() / 1000 / 1000 / 1000)

    neuer = data.groupby('STIFT').sum()['frac_district_heating']
    grt = pd.concat([neuer, stift2name], axis=1)
    print(grt)
    # Hierbei fällt STIFT 0, also die unbestimmten FW-Nutzer unter den Tisch.
    g = grt.set_index('KLASSENNAM').groupby(by=district_heating_groups).sum()
    print(g)
    print(g.sum())
    print(grt.sum())
    print(grt.sum() - g.sum())
    exit(0)
    print(grt)
    print(grt.sum())
    f = grt.sum()['frac_district_heating'] / 100
    print(grt['frac_district_heating'])
    print(f)
    grt['prz'] = grt['frac_district_heating'].div(f)
    print(grt)

    print(subset.total_loss_contemp.sum() / subset.living_area.sum())
    print(subset.total_loss_pres.sum() / subset.living_area.sum())
    logging.info("Done: {0}".format(datetime.datetime.now() - start))


if __name__ == "__main__":
    logger.define_logging()
    create()

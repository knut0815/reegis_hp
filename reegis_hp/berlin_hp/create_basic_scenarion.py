import pandas as pd
import geopandas as gpd
import datetime
import logging
import os

import reegis_hp.berlin_hp.config as cfg
import reegis_hp.de21.demand as de21_demand

import oemof.tools.logger as logger
import demandlib.bdew as bdew

from workalendar.europe import Germany


def time_logger(txt, start):
    msg = "{0}.Elapsed time: {1}".format(txt, datetime.datetime.now() - start)
    logging.info(msg)


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
    time_logger('OEQ loaded.', start)
    # A file with a heat factor for each building type of the alkis
    # classification. Buildings like garages etc get the heat-factor 0. It is
    # possible to define building factors between 0 and 1.
    filename_heat_factor = os.path.join(cfg.get('paths', 'static'),
                                        'heat_factor_by_building_type.csv')
    heat_factor = pd.read_csv(filename_heat_factor, index_col=[0])
    del heat_factor['gebaeude_1']
    time_logger('Heat factor loaded.', start)

    # Heat demand from energy balance (de21)
    filename_heat_reference = os.path.join(cfg.get('paths', 'oeq'),
                                           'heat_reference{0}.csv'.format(year))

    if not os.path.isfile(filename_heat_reference):
        heat_reference = de21_demand.heat_demand(year).loc['BE'].div(3.6)
        heat_reference.to_csv(filename_heat_reference)
    else:
        heat_reference = pd.read_csv(filename_heat_reference, index_col=[0])
    time_logger('Heat reference fetched.', start)

    # TODO: Hier muss noch ein besserer Ort her
    # Read map with areas of district heating systems in Berlin
    chiba = cfg.get('paths', 'chiba')
    filename_map = os.path.join(chiba, 'Promotion', 'Statstik', 'Fernwaerme',
                                'Fernwaerme_2007', 'district_heat_blocks.shp')
    fw_map = gpd.read_file(filename_map)
    time_logger('District heating areas loaded.', start)
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

    # Get the columns with the fraction of the fuel
    frac_cols = [x for x in data.columns if 'frac_' in x]

    # Divide columns with 100 to get the fraction instead of percentage
    data[frac_cols] = data[frac_cols].div(100)

    # Sum up columns to check if the sum is 1.
    data['check'] = data[frac_cols].sum(axis=1)

    # Level columns if sum is between 0.95 and 1.
    data.loc[data['check'] > 0.95, frac_cols] = (
        data.loc[data['check'] > 0.95, frac_cols].multiply(
            (1 / data.loc[data['check'] > 0.95, 'check']), axis=0))

    # Update the check column.
    data['check'] = data[frac_cols].sum(axis=1)

    # Get the average values for each fraction
    length = len(data.loc[round(data['check']) == 1, frac_cols])
    s = data.loc[data['check'] > 0.95, frac_cols].sum()/length

    # add average values if fraction is missing
    data.loc[data['check'] < 0.1, frac_cols] = (
            data.loc[data['check'] < 0.1, frac_cols] + s)

    # Update the check column.
    data['check'] = data[frac_cols].sum(axis=1)
    length = float(len(data['check']))
    check_sum = data['check'].sum()
    if check_sum > length + 1 or check_sum < length - 1:
        logging.warning("The fraction columns do not equalise 1.")

    # Merge the heat-factor for each building type to the alkis types
    data = data.merge(heat_factor, left_on='building_function',
                      right_index=True)

    # Multiply the heat demand of the buildings with the heat factor
    data['total'] *= data['heat_factor']

    # Level the overall heat demand with the heat demand from the energy balance
    factor = heat_reference.sum().sum() / (data['total'].sum() / 1000 / 1000)
    data['total'] = data['total'] * factor
    # data['ghd'] = data['ghd'] * data['total']
    # data['mfh'] = data['mfh'] * data['total']
    # data.to_excel('dasf.xlsx')
    # Todo: Prozesswärme
    # print(data['tot_gud'].sum())
    # exit(0)

    # Multiply fraction columns with total heat demand to get the total demand
    # for each fuel type.
    ghd = data[frac_cols].multiply(data['total'] * data['ghd'], axis=0)
    mfh = data[frac_cols].multiply(data['total'] * data['mfh'], axis=0)

    print(ghd.sum())
    print(mfh.sum())
    print(data['total'].sum())
    exit(0)
    weather = pd.HDFStore(
        '/home/local/RL-INSTITUT/uwe.krien/reegis/de21/weather/coastDat2_de_2013.h5',
        mode='r')
    berlin_coastdat_id = [1137095, 1137096, 1138095, 1138096, 1138097, 1139095,
                          1139096]
    from matplotlib import pyplot as plt
    temperature = pd.DataFrame()
    for cd_id in berlin_coastdat_id:
        temperature[cd_id] = weather['A{0}'.format(cd_id)]['temp_air']

    temperature -= 272.15
    temperature = temperature.sum(axis=1).div(len(berlin_coastdat_id))
    temperature.plot()
    cal = Germany()
    holidays = dict(cal.holidays(year))
    plt.show()

    # Divide the heat demand by building type
    demand_ghd = data['total'].multiply(data['ghd']).sum()
    demand_mfh = data['total'].multiply(data['mfh']).sum()

    ghd = {'shlp_type': 'ghd', 'build_class': 0, 'demand': demand_ghd}
    mfh = {'shlp_type': 'mfh', 'build_class': 1, 'demand': demand_mfh}

    slp_list = [ghd, mfh]

    demand_profile = pd.DataFrame()
    for slp in slp_list:
        demand_profile[slp['shlp_type']] = bdew.HeatBuilding(
            temperature.index, holidays=holidays, temperature=temperature,
            shlp_type=slp['shlp_type'], wind_class=0,
            building_class=slp['build_class'], annual_heat_demand=slp['demand'],
            name=slp['shlp_type'], ww_incl=True
            ).get_bdew_profile()

    demand_profile = demand_profile.sum(axis=1)
    demand_profile.plot()
    plt.show()
    print(data[frac_cols].sum())

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

    logging.info("Done: {0}".format(datetime.datetime.now() - start))


if __name__ == "__main__":
    logger.define_logging()
    create()

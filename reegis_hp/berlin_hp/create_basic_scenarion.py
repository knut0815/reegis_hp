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


def time_logger(txt, ref):
    msg = "{0}.Elapsed time: {1}".format(txt, datetime.datetime.now() - ref)
    logging.info(msg)


def heat_profile_singel():
    pass


def get_heat_profiles(shlp, year):
    """

    Parameters
    ----------
    shlp : dict
    year : int

    Returns
    -------
    pandas.DataFrame

    """
    # Todo Der Pfad muss besser werden. Repository strukturieren.
    # Get the average temperature for the state of Berlin
    weather = pd.HDFStore(os.path.join(
        cfg.get('paths', 'berlin_hp'), os.path.pardir,
        'de21/weather/coastDat2_de_2013.h5'),
        mode='r')

    # Coastdat ids of the raster fields that touches Berlin
    berlin_coastdat_id = [1137095, 1137096, 1138095, 1138096, 1138097, 1139095,
                          1139096]

    # Get temperature timeseries for every data point.
    temperature = pd.DataFrame()
    for cd_id in berlin_coastdat_id:
        temperature[cd_id] = weather['A{0}'.format(cd_id)]['temp_air']
    weather.close()

    # Calculate the average temperature in degree Celsius
    temperature -= 272.15
    temperature = temperature.sum(axis=1).div(len(berlin_coastdat_id))

    # Fetch the holidays of Germany from the workalendar package
    cal = Germany()
    holidays = dict(cal.holidays(year))

    fuel_list = shlp[list(shlp.keys())[0]]['demand'].index

    profile_fuel = pd.DataFrame()
    for fuel in fuel_list:
        fuel_name = fuel.replace('frac_', '')
        profile_type = pd.DataFrame()
        for shlp_type in shlp.keys():
            shlp_name = str(shlp_type)
            profile_type[fuel_name + '_' + shlp_name] = bdew.HeatBuilding(
                temperature.index, holidays=holidays, temperature=temperature,
                shlp_type=shlp_type, wind_class=0,
                building_class=shlp[shlp_type]['build_class'],
                annual_heat_demand=shlp[shlp_type]['demand'][fuel],
                name=fuel_name + shlp_name, ww_incl=True).get_bdew_profile()

        # for district heating the systems the profile will not be summed up
        # but kept as different profiles ('district_heating_' + shlp_name).
        if fuel_name == 'district_heating':
            for n in profile_type.columns:
                profile_fuel[n] = profile_type[n]
        else:
            profile_fuel[fuel_name] = profile_type.sum(axis=1)
    # profile_fuel.plot()
    # plt.show()
    return profile_fuel


def create():
    year = 2013
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
    del heat_factor['gebaeude_1']

    # Heat demand from energy balance (de21)
    filename_heat_reference = os.path.join(
        cfg.get('paths', 'oeq'), 'heat_reference{0}.csv'.format(year))

    if not os.path.isfile(filename_heat_reference):
        heat_reference = de21_demand.heat_demand(year).loc['BE'].div(3.6)
        heat_reference.to_csv(filename_heat_reference)
    else:
        heat_reference = pd.read_csv(filename_heat_reference, index_col=[0])

    # TODO: Hier muss noch ein besserer Ort her
    # Read map with areas of district heating systems in Berlin
    chiba = cfg.get('paths', 'chiba')
    filename_map = os.path.join(chiba, 'Promotion', 'Statstik', 'Fernwaerme',
                                'Fernwaerme_2007', 'district_heat_blocks.shp')
    fw_map = gpd.read_file(filename_map)

    # Create translation Series with STIFT (numeric) and KLASSENNAM (text)
    stift2name = fw_map.groupby(['STIFT', 'KLASSENNAM']).size().reset_index(
        level='KLASSENNAM')['KLASSENNAM']
    stift2name[0] = 'unknown'  # add description 'unknown' to STIFT 0

    # Replace alphanumeric code from block id
    fw_map['gml_id'] = fw_map['gml_id'].str.replace('s_ISU5_2015_UA.', '')

    # Every building has a block id from the block the building is located.
    # Every block that touches a district heating area has the STIFT (number)
    # of this district heating system. By merging this information every
    # building gets the STIFT (number) of the district heating area.
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

    # Level the overall heat demand with the heat demand from the energy
    # balance
    factor = heat_reference.sum().sum() / (data['total'].sum() / 1000 / 1000)
    data['total'] = data['total'] * factor
    # data['ghd'] = data['ghd'] * data['total']
    # data['mfh'] = data['mfh'] * data['total']
    # data.to_excel('dasf.xlsx')
    # print(data['tot_gud'].sum())
    # exit(0)

    # Todo: Prozesswärme

    # Create a dictionary for each demand profile group
    shlp = {'ghd': {'build_class': 0},
            'mfh': {'build_class': 1}}

    # Add the annual demand to the profile dictionary.
    for t in shlp.keys():
        # Multiply fraction columns with total heat demand to get the total
        # demand for each fuel type
        shlp[t]['demand'] = data[frac_cols].multiply(data['total'] * data[t],
                                                     axis=0).sum()

    # Create the standardised heat load profiles (shlp) for each group
    heat_profiles = get_heat_profiles(shlp, year)

    # Create a summable column for each demand group for district heating
    cols = []
    for shlp_type in shlp.keys():
        name = 'district_' + shlp_type
        data[name] = (data['frac_district_heating'] *
                      data[shlp_type] * data['total'])
        cols.append(name)

    # Group district heating by district heating systems (STIFT = id)
    district_by_stift = data.groupby('STIFT').sum()[cols]

    # Group district heating by own definition (ini) of district heating systems
    district_groups = pd.DataFrame(
        pd.concat([district_by_stift, stift2name], axis=1)).set_index(
            'KLASSENNAM').groupby(by=district_heating_groups).sum()

    # Calculate the fraction of each distric heating group.
    frac_district_groups = district_groups.div(district_groups.sum())

    # Create standardised heat load profile for each group
    for nr in frac_district_groups.index:
        print(nr)
        heat_profiles[nr] = (
            (heat_profiles['district_heating_mfh'] *
             frac_district_groups.loc[nr, 'district_mfh']) +
            (heat_profiles['district_heating_ghd'] *
             frac_district_groups.loc[nr, 'district_ghd']))
    del heat_profiles['district_heating_ghd']
    del heat_profiles['district_heating_mfh']

    print(heat_profiles.sum().sum())
    return heat_profiles

    # DAS IST DAS ERGEBNIS-DATAFRAME() mit Lastkurven für alle demands!!!
    # Jetzt noch die PV und Wind Kurven! Vielleicht nochmal bei Julia gucken.
    # Oder in den anderen Scripten. Dachte eigentlich da wäre schon was. Sonst
    # gucken ob aus de21 was recyled werden kann.


if __name__ == "__main__":
    logger.define_logging()
    start = datetime.datetime.now()
    create()
    logging.info("Done: {0}".format(datetime.datetime.now() - start))

"""
Getting the renewable power plants of Germany.

To use this script you have to download the
renewable_power_plants_DE.info.csv file and copy it to the data folder.

Get information about the used csv-file.
csv = pd.read_csv(
    os.path.join('data_original', 'renewable_power_plants_DE.info.csv'),
    squeeze=True, index_col=[0])
print(csv.download)
print(csv.info)
print(csv.editor)
print(csv.date)

Or just start the script and follow the instructions.

"""
import pandas as pd
import numpy as np
import os
from shapely.geometry import Point
import datetime
from shapely.wkt import loads as wkt_loads
import geopandas as gpd
import requests
import logging
import warnings
import pyproj
import shutil

from oemof.tools import logger


logger.define_logging()


def read_original_file(category, paths, pattern, overwrite):
    """Read file if exists."""

    orig_csv_file = os.path.join(paths[category],
                                 pattern['original'].format(cat=category))
    fixed_csv_file = os.path.join(paths[category],
                                  pattern['fixed'].format(cat=category))

    # If a fixed file is present it will be used instead of the original file.
    if os.path.isfile(fixed_csv_file):
        orig_csv_file = fixed_csv_file

    # Download non existing files. If you think that there are newer files you
    # have to set overwrite=True to overwrite existing with downloaded files.
    if not os.path.isfile(orig_csv_file) or overwrite:
        csv = pd.read_csv(os.path.join(paths['powerplants_basic'],
                                       pattern['info'].format(cat=category)),
                          squeeze=True, index_col=[0])
        logging.warning("File not found. Try to download it from server.")
        logging.warning("Check URL if download does not work.")
        req = requests.get(csv.download)
        with open(orig_csv_file, 'wb') as fout:
            fout.write(req.content)
        logging.warning("Downloaded from {0} and copied to '{1}'.".format(
            csv.download, orig_csv_file))
        logging.warning("This script is tested with the file of {0}.".format(
            csv.date))
        req = requests.get(csv.readme)
        with open(os.path.join(paths[category],
                               pattern['readme'].format(cat=category)),
                  'wb') as fout:
            fout.write(req.content)
        req = requests.get(csv.json)
        with open(os.path.join(paths[category],
                               pattern['json'].format(cat=category)),
                  'wb') as fout:
            fout.write(req.content)

    df = pd.read_csv(orig_csv_file)
    if 'id' not in df:
        df['id'] = df.index
    return df


def convert_utm_code(df):
    # *** Convert utm if present ***
    utm_zones = list()
    # Get all utm zones.
    if 'utm_zone' in df:
        df_utm = df.loc[(df.lon.isnull()) & (df.utm_zone.notnull())]

        utm_zones = df_utm.utm_zone.unique()

    # Loop over utm zones and convert utm coordinates to latitude/longitude.
    for zone in utm_zones:
        my_utm = pyproj.Proj(
            "+proj=utm +zone={0},+north,+ellps=WGS84,".format(str(int(zone))) +
            "+datum=WGS84,+units=m,+no_defs")
        utm_df = df_utm.loc[df_utm.utm_zone == int(zone),
                            ('utm_east', 'utm_north')]
        coord = my_utm(utm_df.utm_east.values, utm_df.utm_north.values,
                       inverse=True)
        df.loc[(df.lon.isnull()) & (df.utm_zone == int(zone)), 'lat'] = coord[1]
        df.loc[(df.lon.isnull()) & (df.utm_zone == int(zone)), 'lon'] = coord[0]
    return df


def guess_coordinates_by_postcode(df):
    # *** Use postcode ***
    if 'postcode' in df:
        df_pstc = df.loc[(df.lon.isnull() & df.postcode.notnull())]
        if len(df_pstc) > 0:
            pstc = pd.read_csv(os.path.join('data', 'geometries',
                                            'postcode.csv'),
                               index_col='zip_code')
        for idx, val in df_pstc.iterrows():
            try:
                # If the postcode is not number the integer conversion will
                # raise a ValueError. Some postcode look like this '123XX'.
                # It would be possible to add the mayor regions to the postcode
                # map in order to search for the first two/three digits.
                postcode = int(val.postcode)
                if postcode in pstc.index:
                    df.loc[df.id == val.id, 'lon'] = wkt_loads(
                        pstc.loc[postcode].values[0]).centroid.x
                    df.loc[df.id == val.id, 'lat'] = wkt_loads(
                        pstc.loc[postcode].values[0]).centroid.y
                # Replace the last number with a zero and try again.
                elif round(postcode / 10) * 10 in pstc.index:
                    postcode = round(postcode / 10) * 10
                    df.loc[df.id == val.id, 'lon'] = wkt_loads(
                        pstc.loc[postcode].values[0]).centroid.x
                    df.loc[df.id == val.id, 'lat'] = wkt_loads(
                        pstc.loc[postcode].values[0]).centroid.y
                else:
                    logging.debug("Cannot find postcode {0}.".format(postcode))
            except ValueError:
                logging.debug("Cannot find postcode {0}.".format(val.postcode))
    return df


def guess_coordinates_by_spatial_names(df, fs_column, cap_col, total_cap, stat):
    # *** Use municipal_code and federal_state to define coordinates ***
    if fs_column in df:
        if 'municipality_code' in df:
            if df.municipality_code.dtype == str:
                df.loc[df.municipality_code == 'AWZ', fs_column] = 'AWZ_NS'
        if 'postcode' in df:
            df.loc[df.postcode == '000XX', fs_column] = 'AWZ'
        states = df.loc[df.lon.isnull()].groupby(
            fs_column).sum()[cap_col]
        logging.debug("Fraction of undefined capacity by federal state " +
                      "(percentage):")
        for (state, capacity) in states.iteritems():
            logging.debug("{0}: {1:.4f}".format(
                state, capacity / total_cap * 100))
            stat.loc[state, 'undefined_capacity'] = capacity

        # A simple table with the centroid of each federal state.
        f2c = pd.read_csv(os.path.join('data', 'basic',
                                       'centroid_federal_state'),
                          index_col='name')

        # Use the centroid of each federal state if the federal state is given.
        # This is not very precise and should not be used for a high fraction of
        # plants.
        f2c = f2c.applymap(wkt_loads).centroid
        for l in df.loc[(df.lon.isnull() & df[fs_column].notnull())].index:
            if df.loc[l, fs_column] in f2c.index:
                df.loc[l, 'lon'] = f2c[df.loc[l, fs_column]].x
                df.loc[l, 'lat'] = f2c[df.loc[l, fs_column]].y
    return df


def log_undefined_capcity(df, cap_col, total_cap, msg):
    logging.debug(msg)
    undefined_cap = df.loc[df.lon.isnull()][cap_col].sum()
    logging.debug("{0} percent of capacity is undefined.".format(
        undefined_cap / total_cap * 100))
    return undefined_cap


def complete_geometries(df, paths, cap_col, category, time=None,
                        fs_column='federal_state'):
    """
    Try different methods to fill missing coordinates.
    """

    if time is None:
        time = datetime.datetime.now()

    # Get index of incomplete rows.
    incomplete = df.lon.isnull()

    statistics = pd.DataFrame()

    # Calculate total capacity
    total_capacity = df[cap_col].sum()
    statistics.loc['original', 'undefined_capacity'] = log_undefined_capcity(
        df, cap_col, total_capacity,
        "IDs without coordinates found. Trying to fill the gaps.")

    df = convert_utm_code(df)
    statistics.loc['utm', 'undefined_capacity'] = log_undefined_capcity(
        df, cap_col, total_capacity,
        "Reduced undefined plants by utm conversion.")

    df = guess_coordinates_by_postcode(df)
    statistics.loc['postcode', 'undefined_capacity'] = log_undefined_capcity(
        df, cap_col, total_capacity, "Reduced undefined plants by postcode.")

    df = guess_coordinates_by_spatial_names(df, fs_column, cap_col,
                                            total_capacity, statistics)
    statistics.loc['name', 'undefined_capacity'] = log_undefined_capcity(
        df, cap_col, total_capacity,
        "Reduced undefined plants by federal_state centroid.")

    # Store table of undefined sets to csv-file
    if incomplete.any():
        df.loc[incomplete].to_csv(os.path.join(
            paths['messages'],
            '{0}_incomplete_geometries_before.csv'.format(category)))

    incomplete = df.lon.isnull()
    if incomplete.any():
        df.loc[incomplete].to_csv(os.path.join(
            paths['messages'],
            '{0}_incomplete_geometries_after.csv'.format(category)))
    logging.debug("Gaps stored to: {0}".format(paths['messages']))

    statistics['total_capacity'] = total_capacity
    statistics.to_csv(os.path.join(paths['messages'],
                                   'statistics_{0}_pp.csv'.format(category)))

    # Log information
    geo_check = not df.lon.isnull().any()
    if not geo_check:
        logging.warning("Plants with unknown geometry.")
    logging.info('Geometry check: {0}'.format(str(geo_check)))
    logging.info("Geometry supplemented: {0}".format(
        str(datetime.datetime.now() - time)))
    return df


def remove_cols(df, cols):
    """Safely remove columns from dict."""
    for key in cols:
        try:
            del df[key]
        except KeyError:
            pass
    return df


def clean_df(df, rmv_ls=None, str_columns=None, float_columns=None, time=None):
    """Remove obsolete columns and set consistent type to columns."""
    if time is None:
        time = datetime.datetime.now()

    if rmv_ls is not None:
        df = remove_cols(df, rmv_ls)

    if str_columns is not None:
        df.loc[:, str_columns] = df[str_columns].applymap(str)

    if float_columns is not None:
        df.loc[:, float_columns] = df[float_columns].applymap(float)
    logging.info("Cleaned: {0}".format(str(datetime.datetime.now() - time)))
    return df


def lat_lon2point(df):
    """Create shapely point object of latitude and longitude."""
    return Point(df['lon'], df['lat'])


def create_geo_df(df, time=None):
    """Convert pandas.DataFrame to geopandas.geoDataFrame"""
    if time is None:
        time = datetime.datetime.now()
    df['geom'] = df.apply(lat_lon2point, axis=1)
    logging.info("Geom: {0}".format(str(datetime.datetime.now() - time)))

    return gpd.GeoDataFrame(df, crs='epsg:4326', geometry='geom')


def add_spatial_name(gdf, path_spatial_file, name, category, icol='gid',
                     time=None, ignore_invalid=False):
    """Add name of containing region to new column for all points."""
    logging.info("Add spatial name for column: {0}".format(name))
    if time is None:
        time = datetime.datetime.now()

    # Read spatial file (with polygons).
    spatial_df = pd.read_csv(path_spatial_file, index_col=icol)

    # Use the length to create an output.
    length = len(spatial_df.index)

    # Write datasets without coordinates to a file for later analyses.
    gdf_invalid = gdf.loc[~gdf.is_valid].copy()

    if len(gdf_invalid) > 0 and not ignore_invalid:
        path = os.path.join('data', 'powerplants', 'messages',
                            '{0}_{1}_invalid.csv'.format(category, name))
        gdf_invalid.to_csv(path)
        logging.warning("Power plants with invalid geometries present.")
        logging.warning("See '{0}' file for more information.".format(path))
        logging.warning("It is possible to fix the original file manually.")
        logging.warning("Repair file and rename it from '...something.csv'" +
                        " to 'something_fixed.csv' to skip this message.")
        logging.warning(
            "Or set ignore_invalid=True to ignore invalid geometries.")

    # Find points that intersect with polygon and pass name of the polygon to
    # a new column (name of the new column is defined by 'name' parameter.
    gdf_valid = gdf.loc[gdf.is_valid].copy()
    for i, v in spatial_df.geom.iteritems():
        length -= 1
        logging.info("Remains: {0}".format(str(length)))
        gdf_valid.loc[gdf_valid.intersects(wkt_loads(v)), name] = i
    logging.info("Spatial name added to {0}: {1}".format(name,
                 str(datetime.datetime.now() - time)))

    # If points do not intersect with any polygon, a buffer around the point is
    # created.
    if len(gdf_valid.loc[gdf_valid[name].isnull()]) > 0:
        logging.info("Some plants do not intersect. Buffering {0}...".format(
            name
        ))
        gdf_valid = find_intersection_with_buffer(gdf_valid, spatial_df, name)
    else:
        logging.info("All plants intersect. No buffering necessary.")
    return gdf_valid


def find_intersection_with_buffer(gdf, spatial_df, column):
    """Find intersection of points outside the regions by buffering the point
    until the buffered point intersects with a region.
    """
    for row in gdf.loc[gdf[column].isnull()].iterrows():
        point = row[1].geom
        intersec = False
        reg = 0
        buffer = 0
        for n in range(500):
            if not intersec:
                for i, v in spatial_df.iterrows():
                    if not intersec:
                        my_poly = wkt_loads(v.geom)
                        if my_poly.intersects(point.buffer(n / 100)):
                            intersec = True
                            reg = i
                            buffer = n
                            gdf.loc[gdf.id == row[1].id, column] = reg
        if intersec:
            logging.debug("Region found for {0}: {1}, Buffer: {2}".format(
                row[1].id, reg, buffer))
        else:
            warnings.warn(
                "{0} does not intersect with any region. Please check".format(
                    row[1].id))
    logging.warning("Some points needed buffering to fit. " +
                    "See debug file for more information.")
    return gdf


def group_re_powerplants(paths, pattern, overwrite=False):
    category = 'renewable'
    repp = pd.read_csv(os.path.join(paths[category],
                                    pattern['prepared'].format(cat=category)),
                       parse_dates=['commissioning_date',
                                    'decommissioning_date']
                       )

    non_groupable = os.path.join(
        paths['messages'],
        '{0}_non_groupable_plants.csv'.format(category))
    repp[repp.electrical_capacity.isnull()].to_csv(non_groupable)

    repp = repp[repp.electrical_capacity.notnull()]

    # Replace nan values by a string to avoid errors in string operations.
    repp.region.fillna('XXYY', inplace=True)

    # Set not existing commissioning dates to an unrealistic value to make it
    # possible to find them afterwards. Nan values will be ignored by group.
    repp.commissioning_date.fillna(pd.datetime(2099, 9, 9), inplace=True)
    repp['year'] = repp.commissioning_date.map(lambda x: int(x.year))
    repp.decommissioning_date.fillna(pd.datetime(2050, 1, 1), inplace=True)
    years = repp.year.unique()

    # Get all possible types
    re_source = repp.energy_source_level_2.unique()
    repp.energy_source_level_2.fillna('nan', inplace=True)

    # Create an empty MultiIndex DataFrame to take the values.
    my_idx = pd.MultiIndex(levels=[[], [], [], []], labels=[[], [], [], []],
                           names=['source', 'year', 'region', 'coastdat'])
    df = pd.DataFrame(index=my_idx, columns=['capacity'])

    # Group DataFrame with coastdat (Wind/Solar)
    repp_gc = repp.groupby(
        ['energy_source_level_2', 'region', 'coastdat_id', 'commissioning_date',
         'decommissioning_date']).sum().electrical_capacity

    # Group DataFrame without coastdat (everything else)
    repp_g = repp.groupby(
        ['energy_source_level_2', 'region', 'commissioning_date',
         'decommissioning_date']).sum().electrical_capacity

    # Sort index for faster indexing.
    repp_gc = repp_gc.sortlevel()
    repp_g = repp_g.sortlevel()

    # Create list with non existing files.
    if overwrite:
        re_source_new = re_source
    else:
        re_source_new = list()
        for t in re_source:
            filepath = GROUPED.format('{0}_cap.csv'.format(t.lower()))
            if not os.path.isfile(filepath):
                re_source_new.append(t)
    logging.info("Will process the following types: {0}".format(re_source_new))
    # Loop over list with non existing files or all files if overwrite=True
    for t in re_source_new:
        regions = repp_g.loc[t].index.get_level_values(0).unique()
        for r in regions:
            if t in ['Wind', 'Solar']:
                coastdat_ids = repp_gc.loc[t, r].index.get_level_values(
                    0).unique()
            else:
                coastdat_ids = list(('0000000',))
            for c in coastdat_ids:
                logging.info('{0}: {1} - {2}'.format(t, r, c))
                if t in ['Wind', 'Solar']:
                    sub = repp_gc.loc[(t, r, c)]
                else:
                    sub = repp_g.loc[(t, r,)]
                for y in years:
                    start = sub[
                        (sub.index.get_level_values(0) < pd.datetime(y, 1, 1)) &
                        (sub.index.get_level_values(1) > pd.datetime(y, 1, 1))
                        ].sum()
                    next_y = sub[
                        (sub.index.get_level_values(0) < pd.datetime(y + 1, 1,
                                                                     1)) &
                        (sub.index.get_level_values(1) > pd.datetime(y + 1, 1,
                                                                     1))
                        ].sum()
                    if next_y == start:
                        df.loc[(t, y, r, c)] = next_y
                    else:
                        cap = start
                        for m in range(11):
                            cap += (sub[
                                        (sub.index.get_level_values(0) <
                                         pd.datetime(y, m + 2, 1)) &
                                        (sub.index.get_level_values(1) >
                                         pd.datetime(y, m + 2,
                                                     1))].sum() - cap) * (
                                       (11 - m) / 12)
                        df.loc[(t, y, r, c)] = cap

        # Store DataFrame to csv-file
        df = df.sortlevel()
        filepath = GROUPED.format('{0}_cap.csv'.format(t.lower()))
        df.to_csv(filepath)

        # Clear DataFrame
        df = pd.DataFrame(index=my_idx, columns=['capacity'])

    # Concat files if the main file does not exist.
    df = pd.DataFrame(index=my_idx, columns=['capacity'])
    filepath_all = GROUPED.format('{0}_cap.csv'.format('renewable'))
    if not os.path.isfile(filepath_all) or overwrite:
        for t in re_source:
            filepath = GROUPED.format('{0}_cap.csv'.format(t.lower()))
            df = pd.concat([df, pd.read_csv(filepath, index_col=[0, 1, 2, 3])])
        df = df.sortlevel()
        df.to_csv(filepath_all)


def group_conventional_power_plants(paths, pattern, overwrite=False):
    cpp = pd.read_csv(os.path.join('data', 'powerplants', 'prepared',
                                   'conventional_power_plants_DE_prepared.csv'),
                      index_col='id')
    del cpp['Unnamed: 0']
    cpp.region.fillna('XXYY', inplace=True)
    cpp.fuel.fillna('unknown', inplace=True)
    cpp.shutdown.fillna(2050, inplace=True)

    # Create an empty MultiIndex DataFrame to take the values.
    my_idx = pd.MultiIndex(levels=[[], [], []], labels=[[], [], []],
                           names=['fuel', 'year', 'region'])
    df = pd.DataFrame(index=my_idx, columns=['capacity', 'efficiency'])

    # Calculate maximal input capacity using the maximal output and the
    # efficiency.
    cpp['max_in'] = cpp['capacity_net_bnetza'] / cpp['efficiency_estimate']

    cpp_by_region_fuel = cpp.groupby(['fuel', 'region', 'commissioned',
                                      'shutdown'])
    cpp_g = cpp_by_region_fuel[['capacity_net_bnetza', 'max_in']].sum()

    cpp_g['efficiency_avg'] = 0
    print()
    filepath_all = os.path.join(paths['conventional'],
                                pattern['grouped'].format(cat='conventional'))
    if os.path.isfile(filepath_all) and not overwrite:
        type_fuel = list()
        years = list()
        logging.info("File exists. Skipping 'group_conventional_power_plants'.")
        logging.info("Set overwrite=True to change this behaviour.")
    else:
        type_fuel = cpp_g.index.get_level_values(0).unique()
        years = sorted(cpp_g.index.get_level_values(2).unique())
        logging.info("Grouping conventional power plants...")

    for t in type_fuel:
        logging.info(t)
        regions = cpp_g.loc[t].index.get_level_values(0).unique()
        for r in regions:
            for y in years:
                sub = cpp_g.loc[(t, r)]
                tmp = sub.loc[((sub.index.get_level_values(0) <= y) &
                              (sub.index.get_level_values(1) >= y))].sum(axis=0)
                if tmp['max_in'] != 0:
                    tmp['efficiency_avg'] = (tmp['capacity_net_bnetza'] /
                                             tmp['max_in'])
                else:
                    tmp['efficiency_avg'] = np.nan
                df.loc[(t, y, r)] = tuple(
                    tmp[['capacity_net_bnetza', 'efficiency_avg']])

    if not os.path.isfile(filepath_all) or overwrite:
        df = df.sortlevel()
        df.to_csv(filepath_all)


def prepare_conventional_power_plants(paths, pattern, overwrite=False):
    category = 'conventional'
    if (os.path.isfile(os.path.join(paths[category],
                                    pattern['prepared'].format(cat=category)))
            and not overwrite):
        logging.warning("Will not overwrite existing file: {0}".format(
            pattern['prepared'].format(cat=category)))
        logging.warning("Skip {0} power plants".format(category))
    else:
        start = datetime.datetime.now()

        # Read original file or download it from original source
        cpp = read_original_file(category, paths, pattern, overwrite)
        logging.info(
            "File read: {0}".format(str(datetime.datetime.now() - start)))

        cpp = complete_geometries(cpp, paths, 'capacity_net_bnetza', category,
                                  start, fs_column='state')

        # Create GeoDataFrame from original DataFrame
        gcpp = create_geo_df(cpp, start)

        # Add region column (DE01 - DE21)
        geo_file = os.path.join('data', 'geometries', 'polygons_de21_vg.csv')
        gcpp = add_spatial_name(gcpp, geo_file, 'region', category, time=start)

        # Add column with name of the federal state (Bayern, Berlin,...)
        geo_file = os.path.join('data', 'geometries', 'federal_states.csv')
        gcpp = add_spatial_name(gcpp, geo_file, 'federal_state', category,
                                time=start, icol='iso')

        # Write new table to shape-file
        gcpp['region'] = gcpp['region'].apply(str)
        gcpp.to_file(os.path.join(paths[category],
                                  pattern['shp'].format(cat=category)))

        # Write new table to csv file
        cpp['region'] = gcpp['region']
        cpp['federal_state'] = gcpp['federal_state']
        cpp.to_csv(os.path.join(paths[category],
                                pattern['prepared'].format(cat=category)))

    group_conventional_power_plants(paths, pattern)


def prepare_re_power_plants(paths, pattern, overwrite=False):
    category = 'renewable'
    if (os.path.isfile(os.path.join(paths[category],
                                    pattern['prepared'].format(cat=category)))
            and not overwrite):
        logging.warning("Will not overwrite existing file: {0}".format(
            pattern['prepared'].format(cat=category)))
        logging.warning("Skip {0} power plants".format(category))
    else:
        remove_list = ['tso', 'dso', 'dso_id', 'eeg_id', 'bnetza_id',
                       'federal_state', 'postcode', 'municipality_code',
                       'municipality', 'address', 'address_number', 'utm_zone',
                       'utm_east', 'utm_north', 'data_source', 'comment']

        start = datetime.datetime.now()

        # Read original file or download it from original source
        ee = read_original_file(category, paths, pattern, overwrite)
        logging.info("File read: {0}".format(
            str(datetime.datetime.now() - start)))

        # Trying to supplement missing coordinates
        ee = complete_geometries(ee, 'electrical_capacity', category, start)

        # Remove unnecessary column and fix column types.
        ee = clean_df(ee, rmv_ls=remove_list)

        # Create GeoDataFrame from original DataFrame
        gee = create_geo_df(ee, start)

        # Add region column (DE01 - DE21)
        gee = add_spatial_name(gee, os.path.join(
            'data', 'geometries', 'polygons_de21_vg.csv'), 'region', category,
              time=start)

        # Add column with coastdat id
        gee = add_spatial_name(gee, os.path.join(
            'data', 'geometries', 'coastdat_grid.csv'), 'coastdat_id', category,
                               time=start)

        # Fix type of columns
        gee['region'] = gee['region'].apply(str)
        gee['coastdat_id'] = gee['coastdat_id'].apply(int)

        # Write new table to shape-file
        gee.to_file(os.path.join('data', 'powerplants', 'prepared',
                                 '{0}_powerplants.shp'.format(category)))

        # Write new table to csv file
        ee = remove_cols(ee, ['geom', 'lat', 'lon'])
        ee['region'] = gee['region']
        ee['coastdat_id'] = gee['coastdat_id']
        ee.to_csv(os.path.join(paths[category],
                               pattern['prepared'].format(cat=category)))

    # Grouping the plants by type, year, region (and coastdat for Wind/Solar)
    group_re_powerplants(category, overwrite=overwrite)


class PowerPlantsDE21:

    def __init__(self):
        self.cpp = pd.read_csv(GROUPED.format('conventional'),
                               index_col=[0, 1, 2])
        self.repp = pd.read_csv(GROUPED.format('renewable'),
                                index_col=[0, 1, 2, 3])

    def fuels(self):
        return list(self.cpp.index.get_level_values(0).unique())

    def cpp_region_fuel(self, year):
        return self.cpp.groupby(level=(1, 2, 0)).sum().loc[year]

    def repp_region_fuel(self, year):
        return self.repp.groupby(level=(1, 2, 0)).sum().loc[year]


if __name__ == "__main__":
    prepare_conventional_power_plants('conventional', overwrite=False)
    prepare_re_power_plants('renewable', overwrite=False)
    logging_source = os.path.join(os.path.expanduser('~'), '.oemof',
                                  'log_files', 'oemof.log')

    logging_target = os.path.join('data', 'powerplants', 'messages',
                                  '{0}_prepare_open_data.log')
    dtstring = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    shutil.copyfile(logging_source, logging_target.format(dtstring))
    pp = PowerPlantsDE21()
    print(pp.cpp_region_fuel(2016))
    print(pp.repp_region_fuel(2016))
    copp = pd.read_csv('/home/uwe/git_local/reegis-hp/reegis_hp/de21/data/powerplants/prepared/conventional_power_plants_DE_prepared.csv')
    copp.loc[copp.fuel == 'Biomass and biogas'].to_csv('cpp_bio.csv')
    renpp = pd.read_csv('/home/uwe/git_local/reegis-hp/reegis_hp/de21/data/powerplants/prepared/renewable_power_plants_DE_prepared.csv')
    renpp.loc[
        (renpp.energy_source_level_2 == 'Bioenergy') &
        (renpp.electrical_capacity > 1)].to_csv('repp_bio.csv')

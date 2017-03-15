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
FIXED = False

ORIG_CSV_FILE = os.path.join(
    'data', 'powerplants', 'original', '{0}_power_plants_DE.csv')
FIXED_CSV_FILE = os.path.join(
    'data', 'powerplants', 'original', '{0}_power_plants_DE_fixed.csv')
EDITED_CSV_FILE = os.path.join(
    'data', 'powerplants', 'prepared', '{0}_power_plants_DE_prepared.csv')
INFO_FILE = os.path.join(
    'data', 'powerplants', '{0}_power_plants_DE.info.csv')
README = os.path.join(
    'data', 'powerplants', 'original', '{0}_readme.md')
JSON = os.path.join(
    'data', 'powerplants', 'original', '{0}_datapackage.json')


def read_original_file(p_type, overwrite):
    """Read file if exists."""
    global FIXED

    orig_csv_file = ORIG_CSV_FILE.format(p_type)
    fixed_csv_file = FIXED_CSV_FILE.format(p_type)
    info_file = INFO_FILE.format(p_type)
    readme = README.format(p_type)
    json = JSON.format(p_type)

    # Create folder structure
    if not os.path.isdir('data'):
        os.makedirs('data')
    if not os.path.isdir(os.path.join('data', 'powerplants')):
        os.makedirs(os.path.join('data', 'powerplants'))
    for folder in ['prepared', 'messages', 'original', 'grouped']:
        if not os.path.isdir(os.path.join('data', 'powerplants', folder)):
            os.makedirs(os.path.join('data', 'powerplants', folder))

    if os.path.isfile(fixed_csv_file):
        orig_csv_file = fixed_csv_file
        FIXED = True

    # Download non existing files. If you think that there are newer files you
    # have to set overwrite=True to overwrite existing with downloaded files.
    if not os.path.isfile(orig_csv_file) or overwrite:
        csv = pd.read_csv(info_file, squeeze=True, index_col=[0])
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
        with open(readme, 'wb') as fout:
            fout.write(req.content)
        req = requests.get(csv.json)
        with open(json, 'wb') as fout:
            fout.write(req.content)

    df = pd.read_csv(orig_csv_file)
    if 'id' not in df:
        df['id'] = df.index
    return df


def complete_geometries(df, cap_col, category, time=None,
                        fs_column='federal_state'):
    """
    Try different methods to fill missing coordinates.
    """

    if time is None:
        time = datetime.datetime.now()

    # Get index of incomplete rows.
    incomplete = df.lon.isnull()

    # Calculate weight of changes
    logging.debug("IDs without coordinates found. Trying to fill the gaps.")
    total_capacity = df[cap_col].sum()
    undefined_cap = df.loc[df.lon.isnull()][cap_col].sum()
    logging.debug("{0} percent of capacity is undefined.".format(
        undefined_cap / total_capacity * 100))

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

    logging.debug("Reduced undefined plants by utm conversion.")
    undefined_cap = df.loc[df.lon.isnull()][cap_col].sum()
    logging.debug("{0} percent of capacity is undefined.".format(
        undefined_cap / total_capacity * 100))

    # *** Use postcode
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

    logging.debug("Reduced undefined plants by postcode.")
    undefined_cap = df.loc[df.lon.isnull()][cap_col].sum()
    logging.debug("{0} percent of capacity is undefined.".format(
        undefined_cap / total_capacity * 100))

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
                state, capacity / total_capacity * 100))

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

        logging.debug("Reduced undefined plants by federal_state centroid.")
        undefined_cap = df.loc[df.lon.isnull()][cap_col].sum()
        logging.debug("{0} percent of capacity is undefined.".format(
            undefined_cap / total_capacity * 100))

    # Store table of undefined sets to csv-file
    filepath = os.path.join(
        'data', 'powerplants', 'messages',
        '{0}_incomplete_geometries.csv'.format(category))
    df.loc[incomplete].to_csv(filepath)
    logging.debug("Gaps stored to: {0}".format(filepath))

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
                     time=None):
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
    if len(gdf_invalid) > 0 and not FIXED:
        path = os.path.join('data', 'powerplants', 'messages',
                            '{0}_{1}_invalid.csv'.format(category, name))
        gdf_invalid.to_csv(path)
        logging.warning("Power plants with invalid geometries present.")
        logging.warning("See '{0}' file for more information.".format(path))
        logging.warning("It is possible to fix the original file manually.")
        logging.warning("Rename original file from '...something.csv' to " +
                        "'something_fixed.csv' to skip this message.")
        logging.warning("Power plants with invalid geometries will be ignored.")

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


def prepare_conventional_power_plants(category, overwrite=False):

    if os.path.isfile(EDITED_CSV_FILE.format(category)) and not overwrite:
        logging.warning("Will not overwrite existing file: {0}".format(
            EDITED_CSV_FILE.format(category)))
        logging.warning("Skip {0} power plants".format(category))
    else:
        str_cols = ['id', 'country_code', 'company', 'name_bnetza',
                    'block_bnetza', 'name_uba', 'postcode', 'city', 'street',
                    'state', 'commissioned_original', 'status', 'fuel',
                    'energy_source_level_1', 'energy_source_level_2',
                    'energy_source_level_3', 'technology', 'type', 'eeg', 'chp',
                    'merge_comment', 'efficiency_source', 'network_node',
                    'voltage', 'network_operator', 'geom', 'region']

        start = datetime.datetime.now()

        # Read original file or download it from original source
        cpp = read_original_file(category, overwrite)
        logging.info(
            "File read: {0}".format(str(datetime.datetime.now() - start)))

        cpp = complete_geometries(cpp, 'capacity_net_bnetza', category, start,
                                  fs_column='state')

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
        gcpp.to_file(os.path.join('data', 'powerplants', 'prepared',
                                  '{0}_powerplants.shp'.format(category)))

        # Write new table to csv file
        cpp['region'] = gcpp['region']
        cpp['federal_state'] = gcpp['federal_state']
        cpp.to_csv(EDITED_CSV_FILE.format(category))

        # Write new table to hdf file
        cpp = clean_df(cpp, str_columns=str_cols)
        cpp.to_hdf(
            os.path.join('data', 'powerplants', 'prepared',
                         '{0}_power_plants_DE.prepared.hdf'.format(category)
                         ), 'data', mode='w')


def prepare_re_power_plants(category, overwrite=False):

    if os.path.isfile(EDITED_CSV_FILE.format(category)) and not overwrite:
        logging.warning("Will not overwrite existing file: {0}".format(
            EDITED_CSV_FILE.format(category)))
        logging.warning("Skip {0} power plants".format(category))
    else:
        remove_list = ['tso', 'dso', 'dso_id', 'eeg_id', 'bnetza_id',
                       'federal_state', 'postcode', 'municipality_code',
                       'municipality', 'address', 'address_number', 'utm_zone',
                       'utm_east', 'utm_north', 'data_source', 'comment']

        str_cols = ['commissioning_date', 'decommissioning_date',
                    'energy_source_level_1', 'energy_source_level_2',
                    'energy_source_level_3', 'technology', 'voltage_level']

        float_cols = ['electrical_capacity', 'thermal_capacity']

        start = datetime.datetime.now()

        # Read original file or download it from original source
        ee = read_original_file(category, overwrite)
        logging.info("File read: {0}".format(
            str(datetime.datetime.now() - start)))

        # Trying to supplement missing coordinates
        ee = complete_geometries(ee, 'electrical_capacity', category, start)

        # Remove unnecessary column and fix column types.
        ee = clean_df(ee, rmv_ls=remove_list, str_columns=str_cols,
                      float_columns=float_cols)

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
        ee.to_csv(EDITED_CSV_FILE.format(category))

        # Write new table to hdf file
        ee.to_hdf(
            os.path.join('data', 'powerplants', 'prepared',
                         '{0}_power_plants_DE.prepared.hdf'.format(category)),
            'data', mode='w')


if __name__ == "__main__":
    prepare_conventional_power_plants('conventional', overwrite=True)
    prepare_re_power_plants('renewable', overwrite=False)
    logging_source = os.path.join(os.path.expanduser('~'), '.oemof',
                                  'log_files', 'oemof.log')
    logging_target = os.path.join('data', 'powerplants', 'messages',
                                  'prepare_open_data.log')
    shutil.copyfile(logging_source, logging_target)

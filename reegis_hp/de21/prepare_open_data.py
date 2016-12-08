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


def read_original_file():
    """Read file if exists."""
    orig_csv_file = os.path.join('original_data',
                                 'renewable_power_plants_DE.csv')

    if not os.path.isfile(orig_csv_file):
        csv = pd.read_csv(orig_csv_file, squeeze=True, index_col=[0])
        print("Download file from {0} and copy it to '{1}'.".format(
            csv.download, orig_csv_file))
        print("This script is tested with the file of {0}.".format(csv.date))
        print("Run this script again if the file exists.")
        exit(0)

    return pd.read_csv(orig_csv_file)


def complete_geometries(df, time=None):
    """Use centroid of federal state if geometries does not exist."""
    if time is None:
        time = datetime.datetime.now()
    f2c = pd.read_csv('original_data/centroid_federal_state', index_col='name')
    f2c = f2c.applymap(wkt_loads).centroid

    for l in df.loc[df.lon.isnull()].index:
        df.loc[l, 'lon'] = f2c[df.loc[l, 'federal_state']].x
        df.loc[l, 'lat'] = f2c[df.loc[l, 'federal_state']].y

    print('Geometry check:', not ee.lon.isnull().any())
    print('Geometry complete:', datetime.datetime.now() - time)
    return df


def remove_cols(df, cols):
    """Safely remove columns from dict."""
    for key in cols:
        try:
            del df[key]
        except KeyError:
            pass
    return df


def clean_df(df, time=None):
    """Remove obsolete columns and set consistent type to columns."""
    if time is None:
        time = datetime.datetime.now()

    remove_list = ['tso', 'dso', 'dso_id', 'eeg_id', 'bnetza_id',
                   'federal_state', 'postcode', 'municipality_code',
                   'municipality', 'address', 'address_number', 'utm_zone',
                   'utm_east', 'utm_north', 'data_source', 'comment']

    df = remove_cols(df, remove_list)
    str_cols = ['commissioning_date', 'decommissioning_date',
                'energy_source_level_1', 'energy_source_level_2',
                'energy_source_level_3', 'technology', 'voltage_level']
    df.loc[:, str_cols] = df[str_cols].applymap(str)
    float_cols = ['electrical_capacity', 'thermal_capacity']
    df.loc[:, float_cols] = df[float_cols].applymap(float)
    print('Cleaned:', datetime.datetime.now() - time)
    return df


def lat_lon2point(df):
    """Create shapely point object of latitude and longitude."""
    return Point(df['lon'], df['lat'])


def create_geo_df(df, time=None):
    """Convert pandas.DataFrame to geopandas.geoDataFrame"""
    if time is None:
        time = datetime.datetime.now()
    df['geom'] = df.apply(lat_lon2point, axis=1)
    print('Geom:', datetime.datetime.now() - time)

    return gpd.GeoDataFrame(ee, crs='epsg:4326', geometry='geom')


def add_spatial_name(gdf, path_spatial_file, name, icol='gid', time=None):
    """Add name of containing region to new column for all points."""
    if time is None:
        time = datetime.datetime.now()
    spatial_df = pd.read_csv(path_spatial_file, index_col=icol)
    length = len(spatial_df.index)
    for i, v in spatial_df.geom.iteritems():
        length -= 1
        print("Remains:", length)
        gdf.loc[gdf.intersects(wkt_loads(v)), name] = i
    print("Spatial name added to {0}:".format(name),
          datetime.datetime.now() - time)
    return gdf


def fill_region_with_coastdat(df, time=None):
    """If region name is None use location of coastdat point."""
    if time is None:
        time = datetime.datetime.now()
    t = pd.read_csv('original_data/coastdat2region.csv', index_col='id',
                    squeeze=True)
    for i, v in df.region.iteritems():
        if v == 'None':
            df.loc[i, 'region'] = t[df.loc[i, 'coastdat_id']]
    print("Filled region with coastdat:", datetime.datetime.now() - time)
    return df


if __name__ == "__main__":
    start = datetime.datetime.now()
    ee = read_original_file()
    print('File read:', datetime.datetime.now() - start)
    ee = complete_geometries(ee, start)
    ee = clean_df(ee)
    gee = create_geo_df(ee, start)
    gee = add_spatial_name(gee, 'geometries/polygons_de21.csv', 'region',
                           time=start)
    gee = add_spatial_name(gee, 'geometries/coastdat_grid.csv', 'coastdat_id',
                           time=start)
    gee['region'] = gee['region'].apply(str)
    gee['coastdat_id'] = gee['coastdat_id'].apply(int)
    gee = fill_region_with_coastdat(gee)
    gee.to_file('data/ee_powerplants.shp')
    ee = remove_cols(ee, ['geom', 'lat', 'lon'])
    ee['region'] = gee['region']
    ee['coastdat_id'] = gee['coastdat_id']
    ee.to_csv('data/renewable_power_plants_DE.edited.csv')
    ee.to_hdf('data/renewable_power_plants_DE.edited.hdf', 'data', mode='w')

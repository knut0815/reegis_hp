import os
import pandas as pd
import configuration as config
from shapely.geometry import Point
import powerplants as pp
import numpy as np


def lat_lon2point(df):
    """Create shapely point object of latitude and longitude."""
    return Point(df['Wikipedia', 'longitude'], df['Wikipedia', 'latitude'])


def pumped_hydroelectric_storage(c):
    phes_raw = pd.read_csv(os.path.join(c.paths['static'],
                                        c.files['hydro_storages']),
                           header=[0, 1]).sort_index(1)

    phes = phes_raw['dena'].copy()

    # add geometry from wikipedia
    phes_raw = phes_raw[phes_raw['Wikipedia', 'longitude'].notnull()]
    phes['geom'] = (phes_raw.apply(lat_lon2point, axis=1))

    # add energy from ZFES because dena values seem to be corrupted
    phes['energy'] = phes_raw['ZFES', 'energy']
    phes['name'] = phes_raw['ZFES', 'name']
    # TODO: 0.75 should come from config file
    phes['efficiency'] = phes['efficiency'].fillna(0.75)

    # remove storages that do not have an entry for energy capacity
    phes = phes[phes.energy.notnull()]

    # create a GeoDataFrame with geom column
    gphes = pp.create_geo_df(phes)

    # Add column with region id
    gphes = pp.add_spatial_name(
        c, gphes, os.path.join(c.paths['geometry'],
                               c.files['region_polygons']),
        'region', 'offshore')

    # # Add column with coastdat id
    # gphes = pp.add_spatial_name(
    #     c, gphes, os.path.join(c.paths['geometry'],
    #                            c.files['coastdatgrid_polygons']),
    #     'coastdat_id', 'offshore')

    # copy results from GeoDataFrame to DataFrame and remove obsolete columns
    phes['region'] = gphes['region']
    del phes['geom']
    del phes['name']
    del phes['energy_inflow']

    # create turbine and pump efficiency from overall efficiency (square root)
    # multiply the efficiency with the capacity to group with "sum()"
    phes['pump_eff'] = np.sqrt(phes.efficiency) * phes.pump
    phes['turbine_eff'] = np.sqrt(phes.efficiency) * phes.turbine

    phes = phes.groupby('region').sum()

    # divide by the capacity to get the efficiency and remove overall efficiency
    phes['pump_eff'] = phes.pump_eff / phes.pump
    phes['turbine_eff'] = phes.turbine_eff / phes.turbine
    del phes['efficiency']

    phes.to_csv(os.path.join(c.paths['storages'],
                             c.files['hydro_storages_de21']))


if __name__ == "__main__":
    cfg = config.get_configuration()
    pumped_hydroelectric_storage(cfg)

__copyright__ = "Uwe Krien"
__license__ = "GPLv3"


import weather
import powerplants as pp
import feedin
import time_series
import configuration as config
from oemof.tools import logger


def run():
    """pass"""
    c = config.get_configuration()

    # Store weather data
    if not c.general['skip_weather']:
        weather.fetch_coastdat2_year_from_db(c.paths['weather'],
                                             c.paths['geometry'],
                                             c.pattern['weather'],
                                             c.files['region_geometry'],
                                             overwrite=c.general['overwrite'])

        # Calculate the average wind speed for all available weather data sets.
        weather.get_average_wind_speed(c.paths['weather'],
                                       c.files['grid_geometry'],
                                       c.paths['geometry'],
                                       c.pattern['weather'],
                                       c.files['average_wind_speed'])

    if not c.general['skip_conv_power_plants']:
        pp.prepare_conventional_power_plants(
            c, overwrite=c.general['overwrite'])

    if not c.general['skip_re_power_plants']:
        pp.prepare_re_power_plants(c, overwrite=c.general['overwrite'])

    if not c.general['skip_feedin_weather']:
        feedin.normalised_feedin_by_weather(c, overwrite=c.general['overwrite'])
    if not c.general['skip_feedin_region']:
        feedin.normalised_feedin_by_region(c, overwrite=c.general['overwrite'])
    if not c.general['skip_time_series']:
        time_series.get_timeseries(c, overwrite=c.general['overwrite'])


if __name__ == "__main__":
    # initialise logger
    logger.define_logging()
    run()

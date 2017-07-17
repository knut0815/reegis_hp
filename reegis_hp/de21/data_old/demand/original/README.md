
DATAPACKAGE: TIME SERIES
===========================================================================

by Open Power System Data: http://www.open-power-system-data.org/

Package Version: 2017-03-06

Load, wind and solar, prices in hourly resolution

This data package contains different kinds of timeseries data relevant for
power system modelling, namely electricity consumption (load) for 36
European countries as well as wind and solar power generation and
capacities and prices for a growing subset of countries. The timeseries
become available at different points in time depending on the sources. The
data has been downloaded from the sources, resampled and merged in a large
CSV file with hourly resolution. Additionally, the data available at a
higher resolution (Some renewables in-feed, 15 minutes) is provided in a
separate file. All data processing is conducted in python and pandas and
has been documented in the Jupyter notebooks linked below.

The data package covers the geographical region of 35 European countries.

We follow the Data Package standard by the Frictionless Data project, a
part of the Open Knowledge Foundation: http://frictionlessdata.io/


Documentation and script
===========================================================================

This README only contains the most basic information about the data package.
For the full documentation, please see the notebook script that was used to
generate the data package. You can find it at:

https://nbviewer.jupyter.org/github/Open-Power-System-Data/datapackage_timeseries/blob/2017-03-06/main.ipynb

Or on GitHub at:

https://github.com/Open-Power-System-Data/datapackage_timeseries/blob/2017-03-06/main.ipynb


Version history
===========================================================================

* 2017-03-06  update datasets up to 2016-12-31 and reformat output files
* 2016-10-28 harmonized column names for wind generation
* 2016-10-27 Included data from CEPS and PSE
* 2016-07-14 Included data from Energinet.DK, Elia and Svenska Kraftnaet


Resources
===========================================================================

* [Package description page](http://data.open-power-system-data.org/time_series/2017-03-06/)
* [ZIP Package](http://data.open-power-system-data.org/time_series/opsd-time_series-2017-03-06.zip)
* [Script and documentation](https://github.com/Open-Power-System-Data/datapackage_timeseries/blob/2017-03-06/main.ipynb)
* [Original input data](http://data.open-power-system-data.org/time_series/2017-03-06/original_data/)


Sources
===========================================================================

* CEPS
* Svenska Kraftnaet
* own calculation
* BNetzA and Netztransparenz.de
* TenneT
* PSE
* Energinet.dk
* TransnetBW
* Amprion
* ENTSO-E Data Portal
* 50Hertz


Field documentation
===========================================================================


time_series_60min_singleindex.csv
---------------------------------------------------------------------------

* utc_timestamp
    - Type: datetime
    - Format: fmt:%Y-%m-%dT%H%M%SZ
    - Description: Start of timeperiod in Coordinated Universal Time
* cet_cest_timestamp
    - Type: datetime
    - Format: fmt:%Y-%m-%dT%H%M%S%z
    - Description: Start of timeperiod in Central European (Summer-) Time
* interpolated_values
    - Type: string
    - Description: marker to indicate which columns are missing data in source data and has been interpolated (e.g. DE_transnetbw_solar_generation;)
* AT_load_
    - Type: number (float)
    - Description: Consumption in Austria in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* BA_load_
    - Type: number (float)
    - Description: Consumption in Bosnia and Herzegovina in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* BE_load_
    - Type: number (float)
    - Description: Consumption in Belgium in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* BG_load_
    - Type: number (float)
    - Description: Consumption in Bulgaria in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* CH_load_
    - Type: number (float)
    - Description: Consumption in Switzerland in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* CS_load_
    - Type: number (float)
    - Description: Consumption in Serbia and Montenegro in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* CY_load_
    - Type: number (float)
    - Description: Consumption in Cyprus in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* CZ_load_
    - Type: number (float)
    - Description: Consumption in Czechia in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* CZ_solar_generation
    - Type: number (float)
    - Description: Actual solar generation in Czechia in MW
    - Source: [CEPS](http://www.ceps.cz/ENG/Data/Vsechna-data/Pages/odhad-vyroby-obnovitelnych-zdroju.aspx)
* CZ_wind_generation
    - Type: number (float)
    - Description: Actual wind generation in Czechia in MW
    - Source: [CEPS](http://www.ceps.cz/ENG/Data/Vsechna-data/Pages/odhad-vyroby-obnovitelnych-zdroju.aspx)
* DE_load_
    - Type: number (float)
    - Description: Consumption in Germany in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* DE_price_day_ahead
    - Type: number (float)
    - Description: Day-ahead spot price for Germany
    - Source: [Energinet.dk](http://www.energinet.dk/en/el/engrosmarked/udtraek-af-markedsdata/Sider/default.aspx)
* DE_solar_capacity
    - Type: number (float)
    - Description: Electrical capacity of solar in Germany in MW
    - Source: [BNetzA and Netztransparenz.de](http://data.open-power-system-data.org/renewable_power_plants/)
* DE_solar_generation
    - Type: number (float)
    - Description: Actual solar generation in Germany in MW
    - Source: own calculation
* DE_solar_profile
    - Type: number (float)
    - Description: Share of solar capacity producing in Germany
    - Source: own calculation
* DE_wind_capacity
    - Type: number (float)
    - Description: Electrical capacity of wind in Germany in MW
    - Source: [BNetzA and Netztransparenz.de](http://data.open-power-system-data.org/renewable_power_plants)
* DE_wind_generation
    - Type: number (float)
    - Description: Actual wind generation in Germany in MW
    - Source: own calculation
* DE_wind_profile
    - Type: number (float)
    - Description: Share of wind capacity producing in Germany
    - Source: own calculation
* DE_wind_offshore_capacity
    - Type: number (float)
    - Description: Electrical capacity of wind_offshore in Germany in MW
    - Source: [BNetzA and Netztransparenz.de](http://data.open-power-system-data.org/renewable_power_plants/)
* DE_wind_offshore_generation
    - Type: number (float)
    - Description: Actual wind_offshore generation in Germany in MW
    - Source: own calculation
* DE_wind_offshore_profile
    - Type: number (float)
    - Description: Share of wind_offshore capacity producing in Germany
    - Source: own calculation
* DE_wind_onshore_capacity
    - Type: number (float)
    - Description: Electrical capacity of wind_onshore in Germany in MW
    - Source: [BNetzA and Netztransparenz.de](http://data.open-power-system-data.org/renewable_power_plants/)
* DE_wind_onshore_generation
    - Type: number (float)
    - Description: Actual wind_onshore generation in Germany in MW
    - Source: own calculation
* DE_wind_onshore_profile
    - Type: number (float)
    - Description: Share of wind_onshore capacity producing in Germany
    - Source: own calculation
* DE_50hertz_solar_forecast
    - Type: number (float)
    - Description: Forecasted solar generation in DE_50hertz balancing area in MW
    - Source: [50Hertz](http://www.50hertz.com/en/Grid-Data/Photovoltaics/Archive-Photovoltaics)
* DE_50hertz_solar_generation
    - Type: number (float)
    - Description: Actual solar generation in DE_50hertz balancing area in MW
    - Source: [50Hertz](http://www.50hertz.com/en/Grid-Data/Photovoltaics/Archive-Photovoltaics)
* DE_50hertz_wind_forecast
    - Type: number (float)
    - Description: Forecasted wind generation in DE_50hertz balancing area in MW
    - Source: [50Hertz](http://www.50hertz.com/en/Grid-Data/Wind-power/Archive-Wind-power)
* DE_50hertz_wind_generation
    - Type: number (float)
    - Description: Actual wind generation in DE_50hertz balancing area in MW
    - Source: [50Hertz](http://www.50hertz.com/en/Grid-Data/Wind-power/Archive-Wind-power)
* DE_50hertz_wind_offshore_forecast
    - Type: number (float)
    - Description: Forecasted wind_offshore generation in DE_50hertz balancing area in MW
    - Source: [50Hertz](http://www.50hertz.com/en/Grid-Data/Wind-power/Archive-Wind-power)
* DE_50hertz_wind_offshore_generation
    - Type: number (float)
    - Description: Actual wind_offshore generation in DE_50hertz balancing area in MW
    - Source: [50Hertz](http://www.50hertz.com/en/Grid-Data/Wind-power/Archive-Wind-power)
* DE_50hertz_wind_onshore_forecast
    - Type: number (float)
    - Description: Forecasted wind_onshore generation in DE_50hertz balancing area in MW
    - Source: [50Hertz](http://www.50hertz.com/en/Grid-Data/Wind-power/Archive-Wind-power)
* DE_50hertz_wind_onshore_generation
    - Type: number (float)
    - Description: Actual wind_onshore generation in DE_50hertz balancing area in MW
    - Source: [50Hertz](http://www.50hertz.com/en/Grid-Data/Wind-power/Archive-Wind-power)
* DE_amprion_solar_forecast
    - Type: number (float)
    - Description: Forecasted solar generation in DE_amprion balancing area in MW
    - Source: [Amprion](http://www.amprion.net/en/photovoltaic-infeed)
* DE_amprion_solar_generation
    - Type: number (float)
    - Description: Actual solar generation in DE_amprion balancing area in MW
    - Source: [Amprion](http://www.amprion.net/en/photovoltaic-infeed)
* DE_amprion_wind_forecast
    - Type: number (float)
    - Description: Forecasted wind generation in DE_amprion balancing area in MW
    - Source: [Amprion](http://www.amprion.net/en/wind-feed-in)
* DE_amprion_wind_generation
    - Type: number (float)
    - Description: Actual wind generation in DE_amprion balancing area in MW
    - Source: [Amprion](http://www.amprion.net/en/wind-feed-in)
* DE_amprion_wind_onshore_generation
    - Type: number (float)
    - Description: Actual wind_onshore generation in DE_amprion balancing area in MW
    - Source: own calculation
* DE_tennet_solar_forecast
    - Type: number (float)
    - Description: Forecasted solar generation in DE_tennet balancing area in MW
    - Source: [TenneT](http://www.tennettso.de/site/en/Transparency/publications/network-figures/actual-and-forecast-photovoltaic-energy-feed-in)
* DE_tennet_solar_generation
    - Type: number (float)
    - Description: Actual solar generation in DE_tennet balancing area in MW
    - Source: [TenneT](http://www.tennettso.de/site/en/Transparency/publications/network-figures/actual-and-forecast-photovoltaic-energy-feed-in)
* DE_tennet_wind_forecast
    - Type: number (float)
    - Description: Forecasted wind generation in DE_tennet balancing area in MW
    - Source: [TenneT](http://www.tennettso.de/site/en/Transparency/publications/network-figures/actual-and-forecast-wind-energy-feed-in)
* DE_tennet_wind_generation
    - Type: number (float)
    - Description: Actual wind generation in DE_tennet balancing area in MW
    - Source: [TenneT](http://www.tennettso.de/site/en/Transparency/publications/network-figures/actual-and-forecast-wind-energy-feed-in)
* DE_tennet_wind_offshore_generation
    - Type: number (float)
    - Description: Actual wind_offshore generation in DE_tennet balancing area in MW
    - Source: [TenneT](http://www.tennettso.de/site/en/Transparency/publications/network-figures/actual-and-forecast-wind-energy-feed-in)
* DE_tennet_wind_onshore_generation
    - Type: number (float)
    - Description: Actual wind_onshore generation in DE_tennet balancing area in MW
    - Source: own calculation
* DE_transnetbw_solar_forecast
    - Type: number (float)
    - Description: Forecasted solar generation in DE_transnetbw balancing area in MW
    - Source: [TransnetBW](https://www.transnetbw.com/en/transparency/market-data/key-figures)
* DE_transnetbw_solar_generation
    - Type: number (float)
    - Description: Actual solar generation in DE_transnetbw balancing area in MW
    - Source: [TransnetBW](https://www.transnetbw.com/en/transparency/market-data/key-figures)
* DE_transnetbw_wind_forecast
    - Type: number (float)
    - Description: Forecasted wind generation in DE_transnetbw balancing area in MW
    - Source: [TransnetBW](https://www.transnetbw.com/en/transparency/market-data/key-figures)
* DE_transnetbw_wind_generation
    - Type: number (float)
    - Description: Actual wind generation in DE_transnetbw balancing area in MW
    - Source: [TransnetBW](https://www.transnetbw.com/en/transparency/market-data/key-figures)
* DE_transnetbw_wind_onshore_generation
    - Type: number (float)
    - Description: Actual wind_onshore generation in DE_transnetbw balancing area in MW
    - Source: own calculation
* DK_load_
    - Type: number (float)
    - Description: Consumption in Denmark in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* DK_wind_offshore_generation
    - Type: number (float)
    - Description: Actual wind_offshore generation in Denmark in MW
    - Source: [Energinet.dk](http://www.energinet.dk/en/el/engrosmarked/udtraek-af-markedsdata/Sider/default.aspx)
* DK_wind_onshore_generation
    - Type: number (float)
    - Description: Actual wind_onshore generation in Denmark in MW
    - Source: [Energinet.dk](http://www.energinet.dk/en/el/engrosmarked/udtraek-af-markedsdata/Sider/default.aspx)
* DK_east_price_day_ahead
    - Type: number (float)
    - Description: Day-ahead spot price for DK_east balancing area
    - Source: [Energinet.dk](http://www.energinet.dk/en/el/engrosmarked/udtraek-af-markedsdata/Sider/default.aspx)
* DK_east_solar_generation
    - Type: number (float)
    - Description: Actual solar generation in DK_east balancing area in MW
    - Source: [Energinet.dk](http://www.energinet.dk/en/el/engrosmarked/udtraek-af-markedsdata/Sider/default.aspx)
* DK_east_wind_generation
    - Type: number (float)
    - Description: Actual wind generation in DK_east balancing area in MW
    - Source: [Energinet.dk](http://www.energinet.dk/en/el/engrosmarked/udtraek-af-markedsdata/Sider/default.aspx)
* DK_west_load_
    - Type: number (float)
    - Description: Consumption in DK_west balancing area in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* DK_west_price_day_ahead
    - Type: number (float)
    - Description: Day-ahead spot price for DK_west balancing area
    - Source: [Energinet.dk](http://www.energinet.dk/en/el/engrosmarked/udtraek-af-markedsdata/Sider/default.aspx)
* DK_west_solar_generation
    - Type: number (float)
    - Description: Actual solar generation in DK_west balancing area in MW
    - Source: [Energinet.dk](http://www.energinet.dk/en/el/engrosmarked/udtraek-af-markedsdata/Sider/default.aspx)
* DK_west_wind_generation
    - Type: number (float)
    - Description: Actual wind generation in DK_west balancing area in MW
    - Source: [Energinet.dk](http://www.energinet.dk/en/el/engrosmarked/udtraek-af-markedsdata/Sider/default.aspx)
* EE_load_
    - Type: number (float)
    - Description: Consumption in Estonia in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* ES_load_
    - Type: number (float)
    - Description: Consumption in Spain in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* FI_load_
    - Type: number (float)
    - Description: Consumption in Finland in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* FR_load_
    - Type: number (float)
    - Description: Consumption in France in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* GB_load_
    - Type: number (float)
    - Description: Consumption in United Kingdom in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* GR_load_
    - Type: number (float)
    - Description: Consumption in Greece in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* HR_load_
    - Type: number (float)
    - Description: Consumption in Croatia in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* HU_load_
    - Type: number (float)
    - Description: Consumption in Hungary in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* IE_load_
    - Type: number (float)
    - Description: Consumption in Ireland in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* IS_load_
    - Type: number (float)
    - Description: Consumption in Iceland in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* IT_load_
    - Type: number (float)
    - Description: Consumption in Italy in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* LT_load_
    - Type: number (float)
    - Description: Consumption in Lithuania in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* LU_load_
    - Type: number (float)
    - Description: Consumption in Luxembourg in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* LV_load_
    - Type: number (float)
    - Description: Consumption in Latvia in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* ME_load_
    - Type: number (float)
    - Description: Consumption in Montenegro in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* MK_load_
    - Type: number (float)
    - Description: Consumption in Macedonia, Republic of in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* NI_load_
    - Type: number (float)
    - Description: Consumption in Northern Ireland in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* NL_load_
    - Type: number (float)
    - Description: Consumption in Netherlands in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* NO_load_
    - Type: number (float)
    - Description: Consumption in Norway in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* NO_price_day_ahead
    - Type: number (float)
    - Description: Day-ahead spot price for Norway
    - Source: [Energinet.dk](http://www.energinet.dk/en/el/engrosmarked/udtraek-af-markedsdata/Sider/default.aspx)
* PL_load_
    - Type: number (float)
    - Description: Consumption in Poland in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* PL_wind_generation
    - Type: number (float)
    - Description: Actual wind generation in Poland in MW
    - Source: [PSE](http://www.pse.pl/index.php?modul=21&id_rap=24)
* PT_load_
    - Type: number (float)
    - Description: Consumption in Portugal in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* RO_load_
    - Type: number (float)
    - Description: Consumption in Romania in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* RS_load_
    - Type: number (float)
    - Description: Consumption in Serbia in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* SE_load_
    - Type: number (float)
    - Description: Consumption in Sweden in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* SE_price_day_ahead
    - Type: number (float)
    - Description: Day-ahead spot price for Sweden
    - Source: [Energinet.dk](http://www.energinet.dk/en/el/engrosmarked/udtraek-af-markedsdata/Sider/default.aspx)
* SE_solar_generation
    - Type: number (float)
    - Description: Actual solar generation in Sweden in MW
    - Source: [Svenska Kraftnaet](http://www.svk.se/aktorsportalen/elmarknad/statistik/)
* SE_wind_generation
    - Type: number (float)
    - Description: Actual wind generation in Sweden in MW
    - Source: [Svenska Kraftnaet](http://www.svk.se/aktorsportalen/elmarknad/statistik/)
* SE_3_price_day_ahead
    - Type: number (float)
    - Description: Day-ahead spot price for SE_3 balancing area
    - Source: [Energinet.dk](http://www.energinet.dk/en/el/engrosmarked/udtraek-af-markedsdata/Sider/default.aspx)
* SE_4_price_day_ahead
    - Type: number (float)
    - Description: Day-ahead spot price for SE_4 balancing area
    - Source: [Energinet.dk](http://www.energinet.dk/en/el/engrosmarked/udtraek-af-markedsdata/Sider/default.aspx)
* SI_load_
    - Type: number (float)
    - Description: Consumption in Slovenia in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* SK_load_
    - Type: number (float)
    - Description: Consumption in Slovakia in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)
* UA_west_load_
    - Type: number (float)
    - Description: Consumption in UA_west balancing area in MW
    - Source: [ENTSO-E Data Portal](https://www.entsoe.eu/data/data-portal/consumption/Pages/default.aspx)


time_series_15min_singleindex.csv
---------------------------------------------------------------------------

* utc_timestamp
    - Type: datetime
    - Format: fmt:%Y-%m-%dT%H%M%SZ
    - Description: Start of timeperiod in Coordinated Universal Time
* cet_cest_timestamp
    - Type: datetime
    - Format: fmt:%Y-%m-%dT%H%M%S%z
    - Description: Start of timeperiod in Central European (Summer-) Time
* interpolated_values
    - Type: string
    - Description: marker to indicate which columns are missing data in source data and has been interpolated (e.g. DE_transnetbw_solar_generation;)
* CZ_solar_generation
    - Type: number (float)
    - Description: Actual solar generation in Czechia in MW
    - Source: [CEPS](http://www.ceps.cz/ENG/Data/Vsechna-data/Pages/odhad-vyroby-obnovitelnych-zdroju.aspx)
* CZ_wind_generation
    - Type: number (float)
    - Description: Actual wind generation in Czechia in MW
    - Source: [CEPS](http://www.ceps.cz/ENG/Data/Vsechna-data/Pages/odhad-vyroby-obnovitelnych-zdroju.aspx)
* DE_solar_capacity
    - Type: number (float)
    - Description: Electrical capacity of solar in Germany in MW
    - Source: [BNetzA and Netztransparenz.de](http://data.open-power-system-data.org/renewable_power_plants/)
* DE_solar_generation
    - Type: number (float)
    - Description: Actual solar generation in Germany in MW
    - Source: own calculation
* DE_solar_profile
    - Type: number (float)
    - Description: Share of solar capacity producing in Germany
    - Source: own calculation
* DE_wind_capacity
    - Type: number (float)
    - Description: Electrical capacity of wind in Germany in MW
    - Source: [BNetzA and Netztransparenz.de](http://data.open-power-system-data.org/renewable_power_plants)
* DE_wind_generation
    - Type: number (float)
    - Description: Actual wind generation in Germany in MW
    - Source: own calculation
* DE_wind_profile
    - Type: number (float)
    - Description: Share of wind capacity producing in Germany
    - Source: own calculation
* DE_wind_offshore_capacity
    - Type: number (float)
    - Description: Electrical capacity of wind_offshore in Germany in MW
    - Source: [BNetzA and Netztransparenz.de](http://data.open-power-system-data.org/renewable_power_plants/)
* DE_wind_offshore_generation
    - Type: number (float)
    - Description: Actual wind_offshore generation in Germany in MW
    - Source: own calculation
* DE_wind_offshore_profile
    - Type: number (float)
    - Description: Share of wind_offshore capacity producing in Germany
    - Source: own calculation
* DE_wind_onshore_capacity
    - Type: number (float)
    - Description: Electrical capacity of wind_onshore in Germany in MW
    - Source: [BNetzA and Netztransparenz.de](http://data.open-power-system-data.org/renewable_power_plants/)
* DE_wind_onshore_generation
    - Type: number (float)
    - Description: Actual wind_onshore generation in Germany in MW
    - Source: own calculation
* DE_wind_onshore_profile
    - Type: number (float)
    - Description: Share of wind_onshore capacity producing in Germany
    - Source: own calculation
* DE_50hertz_solar_forecast
    - Type: number (float)
    - Description: Forecasted solar generation in DE_50hertz balancing area in MW
    - Source: [50Hertz](http://www.50hertz.com/en/Grid-Data/Photovoltaics/Archive-Photovoltaics)
* DE_50hertz_solar_generation
    - Type: number (float)
    - Description: Actual solar generation in DE_50hertz balancing area in MW
    - Source: [50Hertz](http://www.50hertz.com/en/Grid-Data/Photovoltaics/Archive-Photovoltaics)
* DE_50hertz_wind_forecast
    - Type: number (float)
    - Description: Forecasted wind generation in DE_50hertz balancing area in MW
    - Source: [50Hertz](http://www.50hertz.com/en/Grid-Data/Wind-power/Archive-Wind-power)
* DE_50hertz_wind_generation
    - Type: number (float)
    - Description: Actual wind generation in DE_50hertz balancing area in MW
    - Source: [50Hertz](http://www.50hertz.com/en/Grid-Data/Wind-power/Archive-Wind-power)
* DE_50hertz_wind_offshore_forecast
    - Type: number (float)
    - Description: Forecasted wind_offshore generation in DE_50hertz balancing area in MW
    - Source: [50Hertz](http://www.50hertz.com/en/Grid-Data/Wind-power/Archive-Wind-power)
* DE_50hertz_wind_offshore_generation
    - Type: number (float)
    - Description: Actual wind_offshore generation in DE_50hertz balancing area in MW
    - Source: [50Hertz](http://www.50hertz.com/en/Grid-Data/Wind-power/Archive-Wind-power)
* DE_50hertz_wind_onshore_forecast
    - Type: number (float)
    - Description: Forecasted wind_onshore generation in DE_50hertz balancing area in MW
    - Source: [50Hertz](http://www.50hertz.com/en/Grid-Data/Wind-power/Archive-Wind-power)
* DE_50hertz_wind_onshore_generation
    - Type: number (float)
    - Description: Actual wind_onshore generation in DE_50hertz balancing area in MW
    - Source: [50Hertz](http://www.50hertz.com/en/Grid-Data/Wind-power/Archive-Wind-power)
* DE_amprion_solar_forecast
    - Type: number (float)
    - Description: Forecasted solar generation in DE_amprion balancing area in MW
    - Source: [Amprion](http://www.amprion.net/en/photovoltaic-infeed)
* DE_amprion_solar_generation
    - Type: number (float)
    - Description: Actual solar generation in DE_amprion balancing area in MW
    - Source: [Amprion](http://www.amprion.net/en/photovoltaic-infeed)
* DE_amprion_wind_forecast
    - Type: number (float)
    - Description: Forecasted wind generation in DE_amprion balancing area in MW
    - Source: [Amprion](http://www.amprion.net/en/wind-feed-in)
* DE_amprion_wind_generation
    - Type: number (float)
    - Description: Actual wind generation in DE_amprion balancing area in MW
    - Source: [Amprion](http://www.amprion.net/en/wind-feed-in)
* DE_amprion_wind_onshore_generation
    - Type: number (float)
    - Description: Actual wind_onshore generation in DE_amprion balancing area in MW
    - Source: own calculation
* DE_tennet_solar_forecast
    - Type: number (float)
    - Description: Forecasted solar generation in DE_tennet balancing area in MW
    - Source: [TenneT](http://www.tennettso.de/site/en/Transparency/publications/network-figures/actual-and-forecast-photovoltaic-energy-feed-in)
* DE_tennet_solar_generation
    - Type: number (float)
    - Description: Actual solar generation in DE_tennet balancing area in MW
    - Source: [TenneT](http://www.tennettso.de/site/en/Transparency/publications/network-figures/actual-and-forecast-photovoltaic-energy-feed-in)
* DE_tennet_wind_forecast
    - Type: number (float)
    - Description: Forecasted wind generation in DE_tennet balancing area in MW
    - Source: [TenneT](http://www.tennettso.de/site/en/Transparency/publications/network-figures/actual-and-forecast-wind-energy-feed-in)
* DE_tennet_wind_generation
    - Type: number (float)
    - Description: Actual wind generation in DE_tennet balancing area in MW
    - Source: [TenneT](http://www.tennettso.de/site/en/Transparency/publications/network-figures/actual-and-forecast-wind-energy-feed-in)
* DE_tennet_wind_offshore_generation
    - Type: number (float)
    - Description: Actual wind_offshore generation in DE_tennet balancing area in MW
    - Source: [TenneT](http://www.tennettso.de/site/en/Transparency/publications/network-figures/actual-and-forecast-wind-energy-feed-in)
* DE_tennet_wind_onshore_generation
    - Type: number (float)
    - Description: Actual wind_onshore generation in DE_tennet balancing area in MW
    - Source: own calculation
* DE_transnetbw_solar_forecast
    - Type: number (float)
    - Description: Forecasted solar generation in DE_transnetbw balancing area in MW
    - Source: [TransnetBW](https://www.transnetbw.com/en/transparency/market-data/key-figures)
* DE_transnetbw_solar_generation
    - Type: number (float)
    - Description: Actual solar generation in DE_transnetbw balancing area in MW
    - Source: [TransnetBW](https://www.transnetbw.com/en/transparency/market-data/key-figures)
* DE_transnetbw_wind_forecast
    - Type: number (float)
    - Description: Forecasted wind generation in DE_transnetbw balancing area in MW
    - Source: [TransnetBW](https://www.transnetbw.com/en/transparency/market-data/key-figures)
* DE_transnetbw_wind_generation
    - Type: number (float)
    - Description: Actual wind generation in DE_transnetbw balancing area in MW
    - Source: [TransnetBW](https://www.transnetbw.com/en/transparency/market-data/key-figures)
* DE_transnetbw_wind_onshore_generation
    - Type: number (float)
    - Description: Actual wind_onshore generation in DE_transnetbw balancing area in MW
    - Source: own calculation


Feedback
===========================================================================

Thank you for using data provided by Open Power System Data. If you have
any question or feedback, please do not hesitate to contact us.

For this data package, contact:
Jonathan Muehlenpfordt <muehlenpfordt@neon-energie.de>

For general issues, find our team contact details on our website:
http://www.open-power-system-data.org















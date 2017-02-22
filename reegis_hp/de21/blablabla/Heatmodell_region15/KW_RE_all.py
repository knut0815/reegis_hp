
import pandas as pd
import os


kw = pd.read_csv('data/Kw_Re_all_form.csv')

#print(kw.columns)

kw_sort = kw.groupby(['RE','chp','state','city', 'fuel','technology','id'])

kw_sortiert=kw_sort[['capacity_n','capacity_g', 'chp_capaci','efficiency','Efficien_2','type']].sum()
kw_sortiert.to_csv("kw_sortiert.csv")

kw_fuel = kw.groupby(['RE','chp','state','city', 'fuel','technology'])
#oder vielleicht type statt technology??
kw_fuel_zf_cap = kw_fuel ['capacity_n','capacity_g', 'chp_capaci'].sum()

kw_fuel_zf_eff = kw_fuel ['efficiency','Efficien_2'].mean()


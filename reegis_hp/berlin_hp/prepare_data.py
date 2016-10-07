import pandas as pd


def chp_berlin(p):

    power_plants = dict()
    filename = "/home/uwe/chiba/RLI/data/kraftwerke_vattenfall_zentral.csv"
    power_plants['vattenfall_zentral'] = pd.read_csv(filename)
    power_plants['vattenfall'] = power_plants['vattenfall_zentral'].groupby(
        'Hauptbrennstoff')[['them. Leistung MW', 'el Leistung MW']].sum()
    power_plants['vattenfall'].rename(columns={'them. Leistung MW': 'power_th',
                                               'el Leistung MW': 'power_el'},
                                      inplace=True)
    power_plants['vattenfall'].rename(index=p.trans, inplace=True)

    filename = "/home/uwe/chiba/RLI/data/kraftwerke_btb_zentral.csv"
    power_plants['btb_zentral'] = pd.read_csv(filename)
    power_plants['btb'] = power_plants['btb_zentral'].groupby(
        'Energietraeger')[['therm Leistung MW', 'el Leistung MW']].sum()
    power_plants['btb'].rename(columns={'therm Leistung MW': 'power_th',
                                        'el Leistung MW': 'power_el'},
                               inplace=True)
    power_plants['btb'].rename(index=p.trans, inplace=True)

    filename = "/home/uwe/chiba/RLI/data/kraftwerke_dezentral.csv"
    power_plants['kw_dezentral'] = pd.read_csv(filename, ';')
    power_plants['dezentral'] = power_plants['kw_dezentral'].groupby(
        'Brennstoff')[['th Leistung MW', 'el Leistung MW']].sum()
    power_plants['dezentral'].rename(columns={'th Leistung MW': 'power_th',
                                              'el Leistung MW': 'power_el'},
                                     inplace=True)
    power_plants['dezentral'].rename(index=p.trans, inplace=True)

    power_plants['district_z'] = power_plants['vattenfall']
    power_plants['district_dz'] = pd.concat(
        [power_plants['btb'], power_plants['dezentral']], axis=0)

    power_plants['district_dz'] = power_plants['district_dz'].groupby(
        power_plants['district_dz'].index).sum() * 10e+6
    power_plants['district_z'] = power_plants['district_z'].groupby(
        power_plants['district_z'].index).sum() * 10e+6
    return power_plants

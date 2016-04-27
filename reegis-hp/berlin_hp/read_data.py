import pandas as pd
import os

basic_path = '/home/uwe/chiba/RLI/data'

# wohn_gew_schul = pd.read_csv('/home/uwe/blubber.csv', ';')
# wohn_gew_schul.index += 1
# wohn_gew_schul.to_csv(os.path.join(basic_path, 'wohn_gew_schul.csv'))
#
# iwu_typen = pd.read_csv('/home/uwe/heiztyp2iwu.csv')
# iwu_typen.index += 1
# iwu_typen.to_csv(os.path.join(basic_path, 'iwu_typen.csv'))
#
# stadtstrukturtypen = pd.read_csv('/home/uwe/stadtstruk.csv', ';')
# stadtstrukturtypen.drop('heiztyp', 1, inplace=True)
# stadtstrukturtypen.index += 1
# stadtstrukturtypen.to_csv(os.path.join(basic_path, 'stadtstruktur.csv'))

iwu_typen = pd.read_csv(os.path.join(basic_path, 'iwu_typen.csv'), index_col=0)
wohn_gew_schul = pd.read_csv(
    os.path.join(basic_path, 'wohn_gew_schul.csv'), index_col=0)
stadtstrukturtypen = pd.read_csv(
    os.path.join(basic_path, 'stadtstruktur.csv'), index_col=0)

iwu_typen['EFHv84'] *= wohn_gew_schul.Wohnungen
iwu_typen['EFHn84'] *= wohn_gew_schul.Wohnungen
iwu_typen['MFHv84'] *= wohn_gew_schul.Wohnungen
iwu_typen['MFHn84'] *= wohn_gew_schul.Wohnungen
iwu_typen['Platte'] *= wohn_gew_schul.Wohnungen
iwu_typen['Buero'] = wohn_gew_schul.Buero
iwu_typen['Schule'] = wohn_gew_schul.Schule

print(iwu_typen.sum(1))
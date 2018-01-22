import oemof.db as db
import pandas as pd


def powerplants():
    btb_zentral = db.db_table2pandas(
        db.connection(), 'berlin', 'kraftwerke_btb_zentral')
    dezentral = db.db_table2pandas(
        db.connection(), 'berlin', 'kraftwerke_liste_dezentral')
    vattenfall = db.db_table2pandas(
        db.connection(), 'berlin', 'kraftwerke_vattenfall_zentral')
    btb_zentral['out_th'] = btb_zentral['therm Leistung MW'] * (
        btb_zentral['JNGth'] / 100)
    btb_zentral['out_el'] = btb_zentral['el Leistung MW'] * (
        btb_zentral['JNGel'] / 100)

    # Read Vattenfall's power plants.
    vattenfall = db.db_table2pandas(
        db.connection(), 'berlin', 'kraftwerke_vattenfall_zentral')
    vattenfall['brennstoffe'] = vattenfall.Hauptbrennstoff
    hauptbrennstoff = list()
    for brennstoff in vattenfall.Hauptbrennstoff:
        hauptbrennstoff.append(brennstoff.split(',')[0].lower())
    vattenfall['Hauptbrennstoff'] = hauptbrennstoff
    vattenfall_group = vattenfall.groupby(by='Hauptbrennstoff').sum()

    print(vattenfall_group)
    exit(0)

    btb_group = btb_zentral.groupby(by='Energietraeger').sum()
    btb_group['JNGth'] = btb_group['out_th'] / btb_group['therm Leistung MW']
    btb_group['JNGel'] = btb_group['out_el'] / btb_group['el Leistung MW']
    print(btb_group)


if __name__ == "__main__":
    powerplants()
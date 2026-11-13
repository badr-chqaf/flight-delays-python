# Mini-projet ue données 
# Sortie : "data/derived/vols_mois_compagnie_avion_destination.csv" (UTF-8, avec en-tête, séparateur ",")

import pandas as pd

FLIGHTS_PATH = "data/derived/flights_analyse.csv"
AIRLINES_PATH = "data/raw/airlines.csv"
OUTPUT_PATH = "data/derived/vols_mois_compagnie_avion_destination.csv"

# 1 Lecture des fichiers

flights_analyse = pd.read_csv(FLIGHTS_PATH,sep=",",encoding="utf-8")
airlines = pd.read_csv(AIRLINES_PATH, sep=";",encoding="utf-8")
assert len(flights_analyse) == 336776, "Population attendue : 336 776 vols" 
print("Vols :", flights_analyse.shape)
print("Compagnies :", airlines.shape)


# 2 Jointure gauche : sans perte ni multiplication de vols

n_avant = len(flights_analyse)
flights_analyse = flights_analyse.merge(airlines, on="carrier", how="left", validate="many_to_one")
flights_analyse = flights_analyse.rename(columns={"name": "carrier_name"})
n_apres= len(flights_analyse)
assert n_avant == n_apres, "La jointure a changé le nombre de vols"
assert flights_analyse["carrier_name"].notna().all(), "carrier_name manquant pour certains vols"


# 3 tailnum manquant : gardé comme groupe explicite

print("nombres de tailnum manquants", flights_analyse["tailnum"].isna().sum())      #on a bien 2512 comme prévu dans les consignes 

flights_analyse["tailnum"] = flights_analyse["tailnum"].fillna("NON_RENSEIGNE")


# 4 Agrégation : un mois × une compagnie × un avion × une destination

GROUP_KEYS = ["month", "carrier", "tailnum", "dest"]  # clé candidate
assert flights_analyse[GROUP_KEYS].notna().all().all(), "Clé de groupement incomplète" # La clé doit être complète avant de grouper 

#Definition obligatoires
flights_analyse["retard_15"] = flights_analyse["dep_delay"] > 15

'''
pour le reste (n_vols, n_partis, ...) "count" les compte directement, donc pas besoin de les définir et transformer
en true false pour les sommer ensuite
'''

vols_agreges = (flights_analyse.groupby(["month", "carrier", "carrier_name", "tailnum", "dest"],dropna=False,).agg(
        n_vols=("month", "size"),
        n_partis=("dep_time", "count"),
        n_retard_observe=("dep_delay", "count"), 
        n_distance_observee=("distance", "count"),
        n_temps_vol_observe=("air_time", "count"),
        n_retard_15=("retard_15", "sum"),
        retard_moyen=("dep_delay", "mean"),
        distance_moyenne=("distance", "mean"),
    ).reset_index())

print("Table agrégée :", vols_agreges.shape)

'''
#5 Contrôles obligatoires : 1. les colonnes obligatoires sont présentes et dans l’ordre demandé 
                            2. la clé month + carrier + tailnum + dest est complète et unique 
                            3. carrier_name est renseigné pour toutes les lignes 
                            4. tous les effectifs sont des entiers positifs ou nuls 
                            5. n_retard_15 <= n_retard_observe <= n_partis <= n_vols 
                            6. n_temps_vol_observe <= n_partis et n_distance_observee <= n_vols 
                            7. les sommes des effectifs se réconcilient avec la table au grain « vol »
'''

EXPECTED_COLUMNS = ["month", "carrier", "carrier_name", "tailnum", "dest","n_vols", "n_partis", "n_retard_observe", "n_distance_observee","n_temps_vol_observe", "n_retard_15", "retard_moyen", "distance_moyenne",]

def controle(table):
    assert table.columns.tolist() == EXPECTED_COLUMNS, "1. Colonnes absentes ou mal ordonnées"     
    assert table[GROUP_KEYS].notna().all().all() and not table.duplicated(subset=GROUP_KEYS).any(), "2. Clé incomplète ou non unique"
    assert table["carrier_name"].notna().all(), "3. carrier_name manquant"
    for c in ["n_vols", "n_partis", "n_retard_observe","n_distance_observee", "n_temps_vol_observe", "n_retard_15"]:
        assert pd.api.types.is_integer_dtype(table[c]) and table[c].ge(0).all(), "4. un effectif n'est pas un entier >= 0"
    
    assert ((table["n_retard_15"] <= table["n_retard_observe"]) 
        & (table["n_retard_observe"] <= table["n_partis"]) 
        & (table["n_partis"] <= table["n_vols"])).all(), "5. Ordre des effectifs non respecté"

    assert ((table["n_temps_vol_observe"] <= table["n_partis"]) 
        & (table["n_distance_observee"] <= table["n_vols"])).all(), "6. Effectifs observés incohérents"

    assert table["n_vols"].sum() == len(flights_analyse), "7. n_vols"
    assert table["n_partis"].sum() == flights_analyse["dep_time"].notna().sum(), "7. n_partis"
    assert table["n_retard_observe"].sum() == flights_analyse["dep_delay"].notna().sum(), "7. n_retard_observe"
    assert table["n_distance_observee"].sum() == flights_analyse["distance"].notna().sum(), "7. n_distance_observee"
    assert table["n_temps_vol_observe"].sum() == flights_analyse["air_time"].notna().sum(), "7. n_temps_vol_observe"
    assert table["n_retard_15"].sum() == (flights_analyse["dep_delay"] > 15).sum(), "7. n_retard_15"
    
controle(vols_agreges)        # contrôle de la table en mémoire
print("Contrôles OK :", vols_agreges.shape)


# 6. Export puis relecture du fichier écrit

vols_agreges.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

vols_relus= pd.read_csv(OUTPUT_PATH)
controle(vols_relus)    #contrôle du fichier relu
print("Export OK :", OUTPUT_PATH, vols_relus.shape)


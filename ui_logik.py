import streamlit as st
from struktur import Struktur
from optimierung import TopologieOptimierer
import numpy as np
from solver import solve
import os
import pickle
from datetime import datetime

# Funktion um aktuelles System zu lösen
def loese_aktuelle_struktur(struktur:Struktur):
    K, F, fixiert, mapping = struktur.system_aufbauen()
    u = solve(K.copy(), F, fixiert)
    return u, mapping
    
# Struktur aufbauen, wie in der main.py die test_optimierung
def struktur_bauen(nx, nz, dx, dz, lager_modus):
    s = Struktur()
    
    s.gitter_erzeugen_knoten(nx, nz, dx, dz)
    
    #dx/dz als Federsteifigkeiten, später evtl getrennt in der Sidebar anwenden? k_h, k_v; k_d ?
    # wir verwenden dx und dz auch als abstand, dass ist verwirrend hab hier federsteifigkeit konkret übergeben
    k_h = 1.0 #horizontal
    k_v = 1.0 #vertikal
    k_d = 1.0 / np.sqrt(2) #diagonal 
    s.gitter_erzeugen_federn(k_h, k_v, k_d)

    # entweder wir spannen ganze spalte ein oder nur direkt der Knoten am Lager
    if lager_modus == "Knotenspalte":
        # ganze linke spalte ein Festlager
        for j in range(nz):
            k_id = s.knoten_id(0, j)
            s.lager_setzen(k_id, True, True)
        # ganze rechte Spalte ein Loslager
        #for j in range(nz):
            #k_id = s.knoten_id(nx-1, j)
            #s.lager_setzen(k_id, False, True)

    # ansonsten einfach nur Knoten fest genau am Lager
    else:
        k_id_lager1 = s.knoten_id(0, 0)
        k_id_lager2 = s.knoten_id(nx-1, 0)

        s.lager_setzen(k_id_lager1, True, True)
        s.lager_setzen(k_id_lager2, False, True)


    #Default Kraft mittig oben setzten 
    f_default = -1.0 #nach unten gerichtete Kraft 

    #oberste reihe 
    top_j = nz - 1 

    #je nachdem ob knoten anzahl nx gerade oder ungerade ist eine oder zwei kräft
    if nx % 2 == 1: 
        mid_i = nx // 2 
        k_last = s.knoten_id(mid_i, top_j)
        s.kraft_setzen(k_last, fx = 0.0, fz=f_default)
    
    else: 
        mid_i_l = nx // 2 - 1
        mid_i_r = nx // 2 
        k_l = s.knoten_id(mid_i_l, top_j)
        k_r = s.knoten_id(mid_i_r, top_j)
        s.kraft_setzen(k_l, fx = 0.0, fz=0.5 * f_default)
        s.kraft_setzen(k_r, fx=0.0, fz=0.5 * f_default)

    return s

def einzellast_setzen(struktur:Struktur, neuer_last_knoten_id, fx, fz):
    #einzelne Kraft auf einen Knoten setzten
    #optional die vorherige last löschen damit sich die kräfte nicht überlagern 

    alter_last_knoten_id = st.session_state.get("last_knoten_id")

    #alte Last zurücksetzen wenn vorhanden 
    if alter_last_knoten_id is not None and alter_last_knoten_id in struktur.knoten:
        struktur.kraft_loeschen(alter_last_knoten_id)

    #neue Last setzen 
    struktur.kraft_setzen(neuer_last_knoten_id, fx=fx, fz=fz)
    st.session_state.last_knoten_id = neuer_last_knoten_id

def lager_typ_anwenden(struktur:Struktur, knoten_id, lager_typ):
    #Lagerbedinungen setzen an einem Knoten 
    if lager_typ == "Kein Lager": 
        struktur.lager_loeschen(knoten_id)
    elif lager_typ == "Festlager":
        struktur.lager_setzen(knoten_id, True, True)
    elif lager_typ == "Loslager (x frei, z fix)":
        struktur.lager_setzen(knoten_id, False, True)
    elif lager_typ == "Loslager (x fix, z frei)":
        struktur.lager_setzen(knoten_id, True, False)

#Übernimmt alle Entwurf Kräfte und Entwurf Lager aus dem Session-State in die Struktur
def entwurf_auf_struktur_anwenden(struktur:Struktur):

    #Kräfte anwenden
    for knoten_id, (fx, fz) in st.session_state.entwurf_kraefte.items():
        struktur.kraft_setzen(knoten_id, fx=float(fx), fz=float(fz))

    #Lager anwenden
    for knoten_id, lager_typ in st.session_state.entwurf_lager.items():
        lager_typ_anwenden(struktur, knoten_id, lager_typ)

    #Ergebnis ist veraltet, solve muss neu laufen 
    st.session_state.u = None 
    st.session_state.mapping = None   

#prüft ob das system prinzipiell gelagert ist 
def pruefe_lagerung_genug(struktur:Struktur):
    lager_ids = struktur.lager_knoten_id()
    if not lager_ids:
        return False 
    
    #mindestens 1 mal in x und einmal in z fixiert
    fix_x = any(struktur.knoten[k].fix_x for k in lager_ids)
    fix_z = any(struktur.knoten[k].fix_z for k in lager_ids)
    return fix_x and fix_z

def reset_ui_state_bei_neuer_struktur():
    st.session_state.kraft_knoten_id = None
    st.session_state.last_knoten_id = None
    st.session_state.entwurf_kraefte = {}
    st.session_state.entwurf_lager = {}
    st.session_state.u = None
    st.session_state.mapping = None


def checkpoint_speichern(zustand: dict, ordner: str = "checkpoints", dateiname: str | None = None):
    os.makedirs(ordner, exist_ok=True)

    if dateiname is None:
        zeit = datetime.now().strftime("%Y%m%d_%H%M%S")
        dateiname = f"checkpoint_{zeit}.pkl"

    pfad = os.path.join(ordner, dateiname)

    with open(pfad, "wb") as f:
        pickle.dump(zustand, f)

    return pfad

def checkpoint_laden(pfad: str) -> dict:
    with open(pfad, "rb") as f:
        return pickle.load(f)

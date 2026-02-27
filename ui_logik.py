import streamlit as st
from struktur import Struktur
from optimierung import TopologieOptimierer
import numpy as np
from solver import solve
import os
import pickle
from datetime import datetime

def loese_aktuelle_struktur(struktur:Struktur):
    """
    Baut das aktuelle GLS der aktuellen Struktur auf und löst es.

    Argument:
        struktur (Struktur): aktuelle Struktur mit Knoten/Federn/Lagern/Kräften

    Returns:
        tuple[np.ndarray | None, dict]:
            - u -> Verschiebungsvektor oder None
            - mapping -> DOF-Mapping {knoten_id: (ix, iz)}
    """
    K, F, fixiert, mapping = struktur.system_aufbauen()
    u = solve(K.copy(), F, fixiert)
    return u, mapping
    
def struktur_bauen(nx, nz, dx, dz, lager_modus):
    """
    Erzeugt ein Default-Gitter, inklusive Federn, Lagern, und eine Default Last.

    Argumente:
        nx (int): Anzahl Knoten in x-Richtung
        nz (int): Anzahl Knoten in z-Richtung
        dx (float): Knotenabstand in x
        dz (float): Knotenabstand in z
        lager_modus (str): "Knoten einzeln" oder "Knotenspalte"

    Returns:
        Struktur: fertig initialisierte Struktur
    """
    s = Struktur()
    
    s.gitter_erzeugen_knoten(nx, nz, dx, dz)
    
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
    """
    Setzt eine einzalne Kraft auf einen Knoten und entfernt optional die vorherige Last.
    Der Nutzer soll nicht mehrere Lasten aus Versehen aufsummieren, daher wird die vorherige Last (aus st.session_state) zuerst gelöscht

    Argumente:
        struktur (Struktur): aktuelle Struktur
        neuer_last_knoten_id (int): Knoten-ID für neue Last
        fx (float): Kraft in x
        fz (float): Kraft in z
    """

    alter_last_knoten_id = st.session_state.get("last_knoten_id")

    #alte Last zurücksetzen wenn vorhanden 
    if alter_last_knoten_id is not None and alter_last_knoten_id in struktur.knoten:
        struktur.kraft_loeschen(alter_last_knoten_id)

    #neue Last setzen 
    struktur.kraft_setzen(neuer_last_knoten_id, fx=fx, fz=fz)
    st.session_state.last_knoten_id = neuer_last_knoten_id

def lager_typ_anwenden(struktur:Struktur, knoten_id, lager_typ):
    """
    Übersetzt den Lager-String aus der UI in echte Lagerbedingungen (fix_x/fix_z)

    Argumente:
        struktur (Struktur): aktuelle Struktur
        knoten_id (int): Knoten-ID
        lager_typ (str): UI-Label (z.B. "Festlager", "Loslager (x frei, z fix)" ...)
    """

    #Lagerbedinungen setzen an einem Knoten 
    if lager_typ == "Kein Lager": 
        struktur.lager_loeschen(knoten_id)
    elif lager_typ == "Festlager":
        struktur.lager_setzen(knoten_id, True, True)
    elif lager_typ == "Loslager (x frei, z fix)":
        struktur.lager_setzen(knoten_id, False, True)
    elif lager_typ == "Loslager (x fix, z frei)":
        struktur.lager_setzen(knoten_id, True, False)

def entwurf_auf_struktur_anwenden(struktur:Struktur):
    """
    Übernimmt alle Entwurf-Lager und Entwurf-Kräft aus sessionstates in die Struktur.
    -> In der UI werden Änderungen zunächst als "Entwurf" gespeichert,
        damit man mehrere Sachen einstellen kann, ohne sofort die Struktur zu verändern.
    -> Erst beim Klick auf "Entwürfe anwenden" werden die Werte wirklich gesetzt.
    """
    #Kräfte anwenden
    for knoten_id, (fx, fz) in st.session_state.entwurf_kraefte.items():
        struktur.kraft_setzen(knoten_id, fx=float(fx), fz=float(fz))

    #Lager anwenden
    for knoten_id, lager_typ in st.session_state.entwurf_lager.items():
        lager_typ_anwenden(struktur, knoten_id, lager_typ)

    #Ergebnis ist veraltet, solve muss neu laufen 
    st.session_state.u = None 
    st.session_state.mapping = None   

def pruefe_lagerung_genug(struktur:Struktur):
    """
    Prüft eine minimale Lagerbedingung fpr eine eindeutige Lösung.
    - Mindestens ein Lagerknoten existiert
    - Mindestens ein Freiheitsgrad in x ist fixiert
    - Mindestens ein Freiheitsgrad in z ist fixiert

    Aber das ist keine Stabilitätsanalyse, aber ein guter Vorab-Check für die UI.

    Returns:
        bool: True wenn "prinzipiell gelagert", sonst False
    """
    lager_ids = struktur.lager_knoten_id()
    if not lager_ids:
        return False 
    
    #mindestens 1 mal in x und einmal in z fixiert
    fix_x = any(struktur.knoten[k].fix_x for k in lager_ids)
    fix_z = any(struktur.knoten[k].fix_z for k in lager_ids)
    return fix_x and fix_z

def reset_ui_state_bei_neuer_struktur():
    """
    Setzt UI-Zustände zurück, wenn eine neue Struktur erzeugt wird.
    Dadurch wird verhindert, dass alte Entwürfe (Kräfte/Lager) auf die neue Struktur durchschlagen 
    oder ein altes Solver-Ergebnis (u/mapping) fälschlicherweise angezeigt wird
    """
    st.session_state.kraft_knoten_id = None
    st.session_state.last_knoten_id = None
    st.session_state.entwurf_kraefte = {}
    st.session_state.entwurf_lager = {}
    st.session_state.u = None
    st.session_state.mapping = None


def checkpoint_speichern(zustand: dict, ordner: str = "checkpoints", dateiname: str | None = None):
    """
    Speichert einen beliebigen Python-Zustand als Pickle-Datei

    Arguemnte:
        zustand (dict): Optimierer-Zustand (Struktur + Parameter + Verlauf)
        ordner (str): Zielordner
        dateiname (str | None): Dateiname wie unten 

    Returns:
        str: Dateipfad zu der gespeicherten Pickle-Datei
    """
    
    os.makedirs(ordner, exist_ok=True)

    if dateiname is None:
        zeit = datetime.now().strftime("%Y%m%d_%H%M%S")
        dateiname = f"checkpoint_{zeit}.pkl"

    pfad = os.path.join(ordner, dateiname)

    with open(pfad, "wb") as f:
        pickle.dump(zustand, f)

    return pfad

def checkpoint_laden(pfad: str) -> dict:
    """
    Lädt einen gespeicherten Checkpoint -> Pickle-Datei

    Argumente:
        pfad (str): Pfad zur Pickle-Datei

    Returns:
        dict: wiederhergestellter Zustand
    """
    with open(pfad, "rb") as f:
        return pickle.load(f)

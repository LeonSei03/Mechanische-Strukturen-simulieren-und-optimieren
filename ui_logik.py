import streamlit as st
from struktur import Struktur
from optimierung import TopologieOptimierer
import numpy as np
from solver import solve
import matplotlib.pyplot as plt
import os
import pickle
from datetime import datetime

# ToDo's für streamlit
# schauen ob lagerung richtig hinhaut, plot sieht aus als wenns passt, aber iwi auch komisch
# evtl mehr einstellmöglichkeiten, um linkes lager mal loslager zu machen anstatt nur rechts
# vllt nicht auf 3 spalten aufteilen, damit plot größer ist evtl untereinander
# optimierten plot noch anzeigen


# Funktion um aktuelles System zu lösen
def loese_aktuelle_struktur(struktur:Struktur):
    K, F, fixiert, mapping = struktur.system_aufbauen()
    u = solve(K.copy(), F, fixiert)
    return u, mapping

# Funktion um alle aktiven Knoten darzustellen
#def plot_knoten(struktur, u=None, mapping=None, skalierung=1.0, title="Struktur", show_federn = True, show_ids = False):
    #fig, ax = plt.subplots()
    
    #Hier federn undeformiert
    #if show_federn:
       # for f_id in struktur.aktive_federn_ids():
       #     f = struktur.federn[f_id]
      #      ki = struktur.knoten[f.knoten_i]
     #       kj = struktur.knoten[f.knoten_j]
    #        ax.plot([ki.x, kj.x], [ki.z, kj.z], linewidth=0.8)

    # ursprüngliche Koordinaten
   # xs, zs = struktur.koordinaten_knoten()
   # ax.scatter(xs, zs, label="undeformiert")

    # Verformte Koordinaten
   # if u is not None and mapping is not None:
        #Hier federn deformiert 
       # if show_federn:
      #      for f_id in struktur.aktive_federn_ids():
     #           f = struktur.federn[f_id]
    #            #falls in mapping noch nicht alle Knoten vorhanden sind
   #             if f.knoten_i not in mapping or f.knoten_j not in mapping:
  #                  continue
 #               ki = struktur.knoten[f.knoten_i]
#                kj = struktur.knoten[f.knoten_j]

      #          iix, iiz = mapping[f.knoten_i]
     #           jjx, jjz = mapping[f.knoten_j]

   #             xi = ki.x + skalierung * u[iix]
    #            zi = ki.z + skalierung * u[iiz]
  #              xj = kj.x + skalierung * u[jjx]
 #               zj = kj.z + skalierung * u[jjz]

#                ax.plot([xi, xj], [zi, zj], linewidth = 0.8)

 #       xs_d, zs_d = struktur.koordinaten_knoten_mit_verschiebung(u, mapping, skalierung=skalierung)
#        ax.scatter(xs_d, zs_d, label=f"deformiert (skalierung={skalierung})")

    #ax.set_aspect("equal", adjustable="box")
   # ax.set_title(title)
  #  ax.set_xlabel("x")
 #   ax.set_ylabel("z")
#    ax.legend()

    #return fig
    
# Struktur aufbauen, wie in der main.py die test_optimierung
#
def struktur_bauen(nx, nz, dx, dz, lager_modus):
    s = Struktur()
    
    s.gitter_erzeugen_knoten(nx, nz, dx, dz)
    
    #dx/dz als Federsteifigkeiten, später evtl getrennt in der Sidebar anwenden? k_h, k_v; k_d ?
    s.gitter_erzeugen_federn(dx, dz, 1.0 / np.sqrt(2))

    # entweder wir spannen ganze spalte ein oder nur direkt der Knoten am Lager
    if lager_modus == "Knotenspalte":
        # ganze linke spalte ein Festlager
        for j in range(nz):
            k_id = s.knoten_id(0, j)
            s.lager_setzen(k_id, True, True)
        # ganze rechte Spalte ein Loslager
        for j in range(nz):
            k_id = s.knoten_id(nx-1, j)
            s.lager_setzen(k_id, False, True)

    # ansonsten einfach nur Knoten fest genau am Lager
    else:
        k_id_lager1 = s.knoten_id(0, 0)
        k_id_lager2 = s.knoten_id(nx-1, 0)

        s.lager_setzen(k_id_lager1, True, True)
        s.lager_setzen(k_id_lager2, False, True)

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
        
#Funktion um Kräfte und Lagerknoten zu markieren (unterschiedlich darstellen)
def sammle_plot_marker(struktur:Struktur): 
    festlager_ids = []
    loslager_ids = []
    kraft_ids = []

    for k_id in struktur.aktive_knoten_ids():
        k = struktur.knoten[k_id]

        #Lager 
        if k.fix_x or k.fix_z: 
            if k.fix_x and k.fix_z:
                festlager_ids.append(k_id) #Festlager
            else: 
                loslager_ids.append(k_id) #Loslager

        #Kraft 
        if k.kraft_x != 0 or k.kraft_z != 0:
            kraft_ids.append(k_id)

    return festlager_ids, loslager_ids, kraft_ids


def plot_struktur(struktur:Struktur, u = None, mapping = None, skalierung = 1.0, titel = "Struktur", federn_anzeigen = False, knoten_ids_anzeigen = False, highlight_knoten_id = None):
    #Knoten zeichen und feder (optional)
    fig, ax = plt.subplots(figsize=(11, 4.5), dpi = 120)
    ax.grid(True, linewidth = 0.2)
    ax.margins(0.12)
        
    #Hier federn undeformiert
    if federn_anzeigen:
        for f_id in struktur.aktive_federn_ids():
            f = struktur.federn[f_id]
            k_i = struktur.knoten[f.knoten_i]
            k_j = struktur.knoten[f.knoten_j]
            ax.plot([k_i.x, k_j.x], [k_i.z, k_j.z], linewidth=0.8, color="black")

        #undeformierte Knotenstruktur
    xs, zs = struktur.koordinaten_knoten()
    ax.scatter(xs, zs, s=18, label="Knoten undeformiert")

    #Marker ids
    festlager_ids, loslager_ids, kraft_ids = sammle_plot_marker(struktur)

    if festlager_ids:
        x = [struktur.knoten[i].x for i in festlager_ids]
        z = [struktur.knoten[i].z for i in festlager_ids]
        ax.scatter(x, z, s=18, marker="s", color="green", label="Festlager")

    if loslager_ids:
        x = [struktur.knoten[i].x for i in loslager_ids]
        z = [struktur.knoten[i].z for i in loslager_ids]
        ax.scatter(x, z, s=18, marker="s", color="black", label="Loslager")

    #Kraft als Pfeil dazu zeichnen 
    pfeil_skalierung = 0.5
    for k_id in kraft_ids:
        k = struktur.knoten[k_id]
        ax.arrow(k.x, k.z, pfeil_skalierung*k.kraft_x, pfeil_skalierung*k.kraft_z, head_width=0.1, head_length=0.2, length_includes_head=True, color="red")


    #Knoten ID-Texte 
    if knoten_ids_anzeigen:
        for k_id in struktur.aktive_knoten_ids():
            k = struktur.knoten[k_id]
            ax.text(k.x, k.z, str(k_id), fontsize = 5)

#===========================================MUSS ICH MIR NOCH ANSCHAUEN===================================================
    #ausgewählter Knoten(z.B Lastknoten wird gehighlighted)
    #if highlight_knoten_id is not None and highlight_knoten_id in struktur.knoten:
     #   k = struktur.knoten[highlight_knoten_id]
      #  ax.scatter([k.x], [k.z], s=18, marker = "o", label = "Auswahl Lastknoten", color="red")

    #Alle Lastknoten rot markieren
    kraft_knoten_ids = [k_id for k_id, k in struktur.knoten.items() if k.kraft_x != 0 or k.kraft_z != 0]

    if kraft_knoten_ids:
        xs = [struktur.knoten[k_id].x for k_id in kraft_knoten_ids]
        zs = [struktur.knoten[k_id].z for k_id in kraft_knoten_ids]
        ax.scatter(xs, zs, s=18, color="red", marker="o", label="Kraftknoten")


    if u is not None and mapping is not None: 
        #deformierte Knoten und Federn 
        xs_d, zs_d = struktur.koordinaten_knoten_mit_verschiebung(u, mapping, skalierung=skalierung)
        ax.scatter(xs_d, zs_d, s = 18, label = f"Knoten (deformiert x{skalierung})")

        if federn_anzeigen: 
            for f_id in struktur.aktive_federn_ids():
                feder = struktur.federn[f_id]
                #kleine sicherheit falls feder nicht in mapping 
                if feder.knoten_i not in mapping or feder.knoten_j not in mapping: 
                    continue
                k_i = struktur.knoten[feder.knoten_i]
                k_j = struktur.knoten[feder.knoten_j]

                iix, iiz = mapping[feder.knoten_i]
                jjx, jjz = mapping[feder.knoten_j]

                xi = k_i.x + skalierung * u[iix]
                zi = k_i.z + skalierung * u[iiz]
                xj = k_j.x + skalierung * u[jjx]
                zj = k_j.z + skalierung * u[jjz]

                ax.plot([xi, xj], [zi, zj], linewidth = 0.8, color="gray")
    
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(titel)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.legend()
    return fig
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

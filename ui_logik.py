import streamlit as st
from struktur import Struktur
from optimierung import TopologieOptimierer
import numpy as np
from solver import solve
import matplotlib.pyplot as plt #https://matplotlib.org/stable/api/matplotlib_configuration_api.html
import matplotlib.cm as cm 
import matplotlib.colors as mcolors 
import os
import pickle
from datetime import datetime

# Funktion um aktuelles System zu lösen
def loese_aktuelle_struktur(struktur:Struktur):
    K, F, fixiert, mapping = struktur.system_aufbauen()
    u = solve(K.copy(), F, fixiert)
    return u, mapping

#funktion um knotenposition für die lager und kraft marker zu bestimmen 
def knoten_pos(struktur:Struktur, knoten_id: int, u=None, mapping=None, skalierung: float = 1.0):
    '''
    Funktion gibt die Plot-Position eines Knoten zurück 
    - Ohne u/mapping die undeformierte Position (x, z) 
    - Mit u/mapping die defomierte Position (x + u_x * skalierung und z + u_z * skalierung)
    '''
    k = struktur.knoten[knoten_id]
    x, z = k.x, k.z

    #Wenn eine Lösung mit u vorhanden ist und der Knoten im mapping ist dann deformierte Position verwenden 
    if u is not None and mapping is not None and knoten_id in mapping:
        ix, iz = mapping[knoten_id]
        x += float(skalierung) * float(u[ix])
        z += float(skalierung) * float(u[iz])

    return x, z 
    
# Struktur aufbauen, wie in der main.py die test_optimierung
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

#Funktionen für Heatmap
def norm_min_max(werte: list[float]):
    '''
    Erzeugt eine Normalize-Objekt mit Min/Max-Werten für die Colormap
    - Wert wird auf 0...1 Skaliert damit cmap() eine passende Farbe liefert
    '''

    if not werte: 
        return None 
    
    vmin = float(min(werte))
    vmax = float(max(werte))

    #Wenn alle Werte gleich sind die Skala minimal aufteilen damit Matplotlib nicht zickt (division durch 0)
    if np.isclose(vmin, vmax):
        vmax = vmin + 1e-9

    #Werte mit mcolors auf einen Farbbereich übersetzen
    return mcolors.Normalize(vmin=vmin, vmax=vmax)

def plot_struktur(struktur:Struktur, u = None, mapping = None, skalierung = 1.0, titel = "Struktur", federn_anzeigen = False, knoten_ids_anzeigen = False, lastpfad_knoten=None, heatmap_modus = "Keine", colorbar_anzeigen = True):
    
    #Heatmap 
    cmap = cm.get_cmap("viridis")

    #Standardfarben wenn keine Heatmap aktiv ist 
    farbe_knoten_undeformiert = "slategray"
    farbe_knoten_deformiert = "dimgray"

    #Transparent schalten (paramter alpha) nachdem gesolved wird, um was zu erkennen 
    geloest = (u is not None) and (mapping is not None)
    transparenz = 0.35 if geloest else 1.0

    knoten_vals = None 
    federn_vals = None 
    norm = None 
    colorbar_label = None 

    heatmap_aktiv = (heatmap_modus != "Keine") and (u is not None) and (mapping is not None)

    if heatmap_aktiv: 
        if heatmap_modus == "Verschiebung (Knoten)":
        #Knotenwerte hier |u|
            knoten_vals = {}
            for k_id in struktur.aktive_knoten_ids():
                if k_id not in mapping: 
                    continue
                ix,iz = mapping[k_id]
                ux = float(u[ix])
                uz = float(u[iz])
                knoten_vals[k_id] = (ux*ux + uz*uz) ** 0.5 

            #Federwerte (mittelwert der Endknoten somit werden Federn und knoten gemeinsam eingefärbt)
            federn_vals = {}
            for f_id in struktur.aktive_federn_ids():
                f = struktur.federn[f_id]
                vi = knoten_vals.get(f.knoten_i)
                vj = knoten_vals.get(f.knoten_j)

                if vi is None or vj is None: 
                    continue
                federn_vals[f_id] = 0.5 * (vi + vj)

            werte = list(knoten_vals.values()) + list(federn_vals.values())
            norm = norm_min_max(werte)
            colorbar_label = "|u|"

        elif heatmap_modus == "Federenergie": 
            federn_vals = struktur.feder_energien_aus_u(u, mapping)
            knoten_vals = struktur.knoten_scores_aus_federenergien(federn_vals, mapping, modus="halb")

            werte = list(knoten_vals.values()) + list(federn_vals.values())
            norm = norm_min_max(werte)
            colorbar_label = "E_feder"

        elif heatmap_modus == "Federkraft":
            federn_vals = struktur.feder_kraefte_aus_u(u, mapping, betrag=True)

            #Knotenwerte aus Federkräften verwendung von max(|N|) aller anliegenden Federn 
            angrenzende_kraefte = {k_id: [] for k_id in mapping.keys()}
            for f_id, N in federn_vals.items():
                f = struktur.federn[f_id]
                if f.knoten_i in angrenzende_kraefte: 
                    angrenzende_kraefte[f.knoten_i].append(N)
                if f.knoten_j in angrenzende_kraefte: 
                    angrenzende_kraefte[f.knoten_j].append(N)

            knoten_vals = {}
            for k_id, lst in angrenzende_kraefte.items():
                if lst: 
                    knoten_vals[k_id] = float(max(lst))

            werte = list(knoten_vals.values()) + list(federn_vals.values())
            norm = norm_min_max(werte)
            colorbar_label = "|N_feder|"

    #Hier noch ein hinweis im plot, falls Heatmap gewählt ist aber noch nicht Solve gedrückt wurde
    if heatmap_modus != "Keine" and not heatmap_aktiv:
        titel = f"{titel} (Heatmap erst nach Solve sichtbar!!)"

    
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

            #Standardfabre für die Federn undeformiert
            col = farbe_knoten_undeformiert

            #Falls Heatmap für die Federn aktiv ist Farbe aus federn_vals 
            if federn_vals is not None and norm is not None: 
                v = federn_vals.get(f_id)
                if v is not None: 
                    col = cmap(norm(v))

            ax.plot([k_i.x, k_j.x], [k_i.z, k_j.z], linewidth=0.8, color=col, alpha=transparenz, zorder = 0)

    #undeformierte Knotenstruktur
    xs, zs, cols = [], [], []

    for k_id in struktur.aktive_knoten_ids():
        k = struktur.knoten[k_id]
        xs.append(k.x)
        zs.append(k.z)

        #Standardfabre bei keiner Heatmap 
        col = farbe_knoten_undeformiert

        #Falls Heatmap aktiv: Farbe aus knoten_vals
        if knoten_vals is not None and norm is not None: 
            v = knoten_vals.get(k_id)
            if v is not None: 
                col = cmap(norm(v))

        cols.append(col)

    ax.scatter(xs, zs, s=18, c=cols, alpha=transparenz, label="Knoten undeformiert", zorder = 1)

    #Marker ids
    festlager_ids, loslager_ids, kraft_ids = sammle_plot_marker(struktur)

    if festlager_ids:
        x = [knoten_pos(struktur, i, u, mapping, skalierung)[0] for i in festlager_ids]
        z = [knoten_pos(struktur, i, u, mapping, skalierung)[1] for i in festlager_ids]
        ax.scatter(x, z, s=18, marker="s", color="green", label="Festlager", zorder = 3)

    if loslager_ids:
        x = [knoten_pos(struktur, i, u, mapping, skalierung)[0] for i in loslager_ids]
        z = [knoten_pos(struktur, i, u, mapping, skalierung)[1] for i in loslager_ids]
        ax.scatter(x, z, s=18, marker="s", color="black", label="Loslager", zorder = 3)

    #Kraft als Pfeil dazu zeichnen 
    pfeil_skalierung = 0.5
    for k_id in kraft_ids:
        k = struktur.knoten[k_id]
        x0, z0 = knoten_pos(struktur, k_id, u, mapping, skalierung)
        ax.arrow(x0, z0, pfeil_skalierung*k.kraft_x, pfeil_skalierung*k.kraft_z, head_width=0.1, head_length=0.2, length_includes_head=False, color="red", zorder = 5)


    #Knoten ID-Texte 
    if knoten_ids_anzeigen:
        for k_id in struktur.aktive_knoten_ids():
            k = struktur.knoten[k_id]
            x_txt, z_txt = knoten_pos(struktur, k_id, u, mapping, skalierung)
            ax.text(x_txt, z_txt, str(k_id), fontsize = 5)

    #Alle Lastknoten rot markieren
    #kraft_knoten_ids = [k_id for k_id, k in struktur.knoten.items() if k.kraft_x != 0 or k.kraft_z != 0]

    if kraft_ids:
        xs_k = [knoten_pos(struktur, k_id, u, mapping, skalierung)[0] for k_id in kraft_ids]
        zs_k = [knoten_pos(struktur, k_id, u, mapping, skalierung)[1] for k_id in kraft_ids]
        ax.scatter(xs_k, zs_k, s=18, color="red", marker="o", label="Kraftknoten", zorder=7)


    if u is not None and mapping is not None: 
        #deformierte Knoten und Federn 
        xs_d, zs_d, cols_d = [], [], []

        for k_id in struktur.aktive_knoten_ids():
            x, z = knoten_pos(struktur, k_id, u, mapping, skalierung)

            xs_d.append(x)
            zs_d.append(z)

            #Standardfarbe 
            col = farbe_knoten_deformiert

            #Falls Heatmap aktiv 
            if knoten_vals is not None and norm is not None: 
                v = knoten_vals.get(k_id)
                if v is not None: 
                    col = cmap(norm(v))

            cols_d.append(col)

        ax.scatter(xs_d, zs_d, s = 18, c=cols_d, edgecolors="black", linewidths=0.4, label = f"Knoten (deformiert x{skalierung})", zorder = 2)

        if federn_anzeigen: 
            for f_id in struktur.aktive_federn_ids():
                feder = struktur.federn[f_id]

                xi, zi = knoten_pos(struktur, feder.knoten_i, u, mapping, skalierung)
                xj, zj = knoten_pos(struktur, feder.knoten_j, u, mapping, skalierung)
                
                #Standardfarbe Federn deformiert gleich wie knoten 
                col = farbe_knoten_deformiert

                #Heatmapfarbe für Feder wenn aktiv 
                if federn_vals is not None and norm is not None: 
                    v = federn_vals.get(f_id)
                    if v is not None:
                        col = cmap(norm(v))

                ax.plot([xi, xj], [zi, zj], linewidth = 0.8, color=col, zorder = 1)

        # Lastpfade anzeigen lassen
        if lastpfad_knoten is not None:

            # Falls mehrere Pfade -> direkt so verwenden
            pfade = lastpfad_knoten

            for pfad in pfade:

                if len(pfad) < 2:
                    continue

                xs = []
                zs = []

                for k_id in pfad:
                    k = struktur.knoten[k_id]

                    # deformiert
                    if u is not None and mapping is not None and k_id in mapping:
                        ix, iz = mapping[k_id]
                        xs.append(k.x + skalierung * u[ix])
                        zs.append(k.z + skalierung * u[iz])
                    else:
                        # undeformiert
                        xs.append(k.x)
                        zs.append(k.z)

                ax.plot(xs, zs, linewidth=2, color="red")

    # Colorbar also die Farblegende
    if colorbar_anzeigen and heatmap_aktiv and norm is not None:
        mappable = cm.ScalarMappable(norm=norm, cmap=cmap)
        mappable.set_array([])  
        fig.colorbar(mappable, ax=ax, fraction=0.03, pad=0.02, label=colorbar_label)

    ax.set_aspect("equal", adjustable="box")
    ax.set_title(titel)
    ax.set_xlabel("x")
    ax.set_ylabel("z")
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

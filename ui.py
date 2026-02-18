import streamlit as st
from struktur import Struktur
from optimierung import TopologieOptimierer
import numpy as np
from solver import solve
import matplotlib.pyplot as plt

# ToDo's für streamlit
# schauen ob lagerung richtig hinhaut, plot sieht aus als wenns passt, aber iwi auch komisch
# evtl mehr einstellmöglichkeiten, um linkes lager mal loslager zu machen anstatt nur rechts
# vllt nicht auf 3 spalten aufteilen, damit plot größer ist evtl untereinander
# optimierten plot noch anzeigen


# Funktion um aktuelles System zu lösen
def loese_aktuelle_struktur(struktur):
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

def einzellast_setzen(struktur, neuer_last_knoten_id, fx, fz):
    #einzelne Kraft auf einen Knoten setzten
    #optional die vorherige last löschen damit sich die kräfte nicht überlagern 

    alter_last_knoten_id = st.session_state.get("last_knoten_id")

    #alte Last zurücksetzen wenn vorhanden 
    if alter_last_knoten_id is not None and alter_last_knoten_id in struktur.knoten:
        struktur.kraft_loeschen(alter_last_knoten_id)

    #neue Last setzen 
    struktur.kraft_setzen(neuer_last_knoten_id, fx=fx, fz=fz)
    st.session_state.last_knoten_id = neuer_last_knoten_id

def lager_typ_anwenden(struktur, knoten_id, lager_typ):
    #Lagerbedinungen setzen an einem Knoten 
    if lager_typ == "Kein Lager": 
        struktur.lager_loeschen(knoten_id)
    elif lager_typ == "Festlager":
        struktur.lager_setzen(knoten_id, True, True)
    elif lager_typ == "Loslager (x frei, z fix)":
        struktur.lager_setzen(knoten_id, False, True)
    elif lager_typ == "Loslager (x fix, z frei)":
        struktur.lager_setzen(knoten_id, True, False)


def plot_struktur(struktur, u = None, mapping = None, skalierung = 10.0, titel = "Strultur", federn_anzeigen = True, knoten_ids_anzeigen = False, highlight_knoten_id: int | None = None):
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
            ax.plot([k_i.x, k_j.x], [k_i.z, k_j.z], linewidth=0.8)

    #undeformierte Knotenstruktur
    xs, zs = struktur.koordinaten_knoten()
    ax.scatter(xs, zs, s=18, label="Knoten undeformiert")

    #Knoten ID-Texte 
    if knoten_ids_anzeigen:
        for k_id in struktur.aktive_knoten_ids():
            k = struktur.knoten[k_id]
            ax.text(k.x, k.z, str(k_id), fontsize = 5)

    #ausgewählter Knoten(z.B Lastknoten wird gehighlighted)
    if highlight_knoten_id is not None and highlight_knoten_id in struktur.knoten:
        k = struktur.knoten[highlight_knoten_id]
        ax.scatter([k.x], [k.z], s=90, marker = "o", label = "Auswahl/Last")

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

                ax.plot([xi, xj], [zi, zj], linewidth = 0.8)
    
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(titel)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.legend()
    return fig



#Stremlit UI hier 
st.set_page_config(page_title="Balken Optimierung", layout="wide")
st.title("Balkenbiegung - Simulation & Topologieoptimierung")


#Session states initialisieren damit alles stabil bleibt 
if "struktur" not in st.session_state:
    st.session_state.struktur = None
if "u" not in st.session_state:
    st.session_state.u = None 
if "mapping" not in st.session_state:
    st.session_state.mapping = None 
if "historie" not in st.session_state:
    st.session_state.historie = None 
if "ausgewaehlter_knoten_id" not in st.session_state:
    st.session_state.ausgewaehlter_knoten_id = None 
if "last_knoten_id" not in st.session_state:
    st.session_state.last_knoten_id = None 


# Seitenleiste und alle Parameter die wir brauchen abfragen und als FORM, damit änderungen erst bei klick übernommen werden 
with st.sidebar.form("parameter_form"):
    st.header("Geometrie / Lager")

    nx = st.number_input("Anzahl Knoten in x (nx)", 5, 200, 30)
    nz = st.number_input("Anzahl Knoten in z (nz)", 3, 200, 15)
    dx = st.number_input("Abstand x (dx)", 0.1, 10.0, 1.0)
    dz = st.number_input("Abstand z (dz)", 0.1, 10.0, 1.0)

    lager_modus = st.selectbox("Lager (Start)", ["Knotenspalte", "Knoten einzeln"])

    st.markdown("---")
    st.header("Darstellung")

    skalierung = st.slider("Deformations-Skala (Dehnung skalieren damits anschaulicher ist)", 0.0, 25.0, 10.0)
    federn_anzeigen = st.checkbox("Federn anzeigen", value=True)
    knoten_ids_anzeigen = st.checkbox("Knoten-Ids anzeigen (debug)", value=False)

    st.markdown("---")
    st.header("Optimierung (Masse)")

    ziel_anteil = st.slider("Ziel-Massenanteil (z.B 0,5 ist die Hälfte der Masse behalten)", 0.05, 0.95, 0.50, 0.01)
    max_iter = st.number_input("Max. Iterationen", 1, 50, 5)
    max_entfernen_pro_iter = st.number_input("max_entfernen_pro_iter (max Anzahl an Knoten welche pro iter versucht wird wegzumachen)", 1, 15, 3)
    u_faktor = st.number_input("u_faktor (zugelassene Dehnung vor Rollback)", 0.1, 200.0, 3.0, 0.1)   

    uebernehmen = st.form_submit_button("Übernehmen (Struktur neu erzeugen)")

#Struktur erzeugen (beim ersten Start, oder wenn User "Übernehmen" drückt)
if uebernehmen or st.session_state.struktur is None:
    st.session_state.struktur = struktur_bauen(int(nx), int(nz), float(dx), float(dz), lager_modus)

    #Bei Neubau: Ergebnisse löschen 
    st.session_state.u = None 
    st.session_state.mapping = None
    st.session_state.historie = None 
    st.session_state.ausgewaehlter_knoten_id = None 
    st.session_state.last_knoten_id = None 

struktur = st.session_state.struktur 

#Text bevor die Struktur erstellt wird
if struktur is None:
    st.info("Erstellen Sie mit den Paramteren links in der Seitenleiste eine Struktur um daran arbeiten zu können!") 
    st.stop()
    

#Hauptlayout für Tabs bzw. Überischt 
tab_ansicht, tab_randbedingungen, tab_solve, tab_optimierung = st.tabs(["Ansicht", "Knoten bearbeiten", "Solve", "Optimierung"])

#Tab 1 Ansicht (Preview immer sichtbar)
with tab_ansicht:
    st.subheader("Vorschau / Ergebnis")

    #Masse Infos (1 Knoten = 1kg)
    aktive_knoten = struktur.aktive_knoten_ids()
    start_masse = len(aktive_knoten) #kg
    ziel_masse = int(np.ceil(start_masse * float(ziel_anteil)))
    aktuelle_masse = len(aktive_knoten)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Startmasse (kg)", start_masse)
    col_b.metric("Zielmasse (kg)", ziel_masse)
    col_c.metric("Aktuelle Masse (kg)", aktuelle_masse)

    fig = plot_struktur(struktur=struktur, u=st.session_state.u, mapping=st.session_state.mapping, skalierung=float(skalierung), titel=("Sturktur (undeformiert bzw. deformiert)"), federn_anzeigen=federn_anzeigen, knoten_ids_anzeigen=knoten_ids_anzeigen, highlight_knoten_id=st.session_state
                        .last_knoten_id or st.session_state.ausgewaehlter_knoten_id) 
    
    st.pyplot(fig, use_container_width=True)

#Tab 2 Knoten bearbeiten (mit Dropdown auswahl)
with tab_randbedingungen: 
    st.subheader("Knoten auswählen und Kraft/Lager setzen")

    aktive_ids = struktur.aktive_knoten_ids()
    if len(aktive_ids) == 0:
        st.warning("Keine aktiven Knoten vorhanden !!")
    else: 
        #wenn noch kein knoten gewählt ist nehmen wir den ersten 
        if st.session_state.ausgewaehlter_knoten_id is None: 
            st.session_state.ausgewaehlter_knoten_id = aktive_ids[0]
        
        ausgewaehlt = st.selectbox("Knoten auswählen", options=aktive_ids, index=aktive_ids.index(st.session_state.ausgewaehlter_knoten_id) if st.session_state.ausgewaehlter_knoten_id in aktive_ids else 0)
        st.session_state.ausgewaehlter_knoten_id = ausgewaehlt

        k = struktur.knoten[ausgewaehlt]
        st.info(f"Aktuell: Knoten {ausgewaehlt}, bei (x={k.x}, z={k.z})")

        st.markdown("### Kraft setzen (Einzellast)")
        fx = st.number_input("Fx", value=float(k.kraft_x))
        fz = st.number_input("Fz", value=float(k.kraft_z))

        #Krfat anwenden (wir behandeln das NOCH als einzellast, kann man ändern später!!) alte last löschen neue setzen 
        if st.button("Kraft auf ausgewählten Knoten anwenden"):
            einzellast_setzen(struktur, ausgewaehlt, fx=float(fx), fz=float(fz))
            st.success("Kraft gesetzt (vorherige Einzellast wurde gelöscht !!)")

        st.markdown("### Lager setzen")
        lager_typ = st.selectbox("Lagertyp für ausgewählten Knoten", ["Kein Lager", "Festlager", "Loslager (x frei, z fix)", "Loslager (x fix, z frei)"])

        if st.button("Lager anwenden"):
            lager_typ_anwenden(struktur, ausgewaehlt, lager_typ)
            st.success("Lager Einstellung gesetzt !!")

        if st.button("Kraft löschen (dieser Knoten)"):
            struktur.kraft_loeschen(ausgewaehlt)
            #falls das der gespeicherte Lastknoten war resetten 
            if st.session_state.last_knoten_id == ausgewaehlt: 
                st.session_state.last_knoten_id = None 
            st.success("Kraft gelöscht !!")

        if st.button("Lager löschen (dieser Knoten)"):
            struktur.lager_loeschen(ausgewaehlt)
            st.success("Lager gelöscht")

#Tab 3 Solve 
with tab_solve:
    st.subheader("System lösen")

    if st.button("Solve"):
        u, mapping = loese_aktuelle_struktur(struktur)
        if u is None: 
            st.error("Solver: System nicht lösbar (evtl. zu wenig Lager / instabil) !!")
        else: 
            st.session_state.u = u
            st.session_state.mapping = mapping 
            st.success("Gelöst !! Wechsel zu 'Ansicht' um die deformierte Struktur zu sehen !!")

# Tab 4 Optimierung 
with tab_optimierung:
    st.subheader("Topologieoptimierung (Masse reduzieren)")

    st.write("Ziel: Anzahl aktiver Knoten reduzieren (1 Knoten = 1kg), bis die Zielmasse erreicht ist!!")

    if st.button("Optimierung starten"):
        opt = TopologieOptimierer(struktur)

        historie = opt.optimierung(ziel_anteil=float(ziel_anteil), max_iter=int(max_iter), max_entfernen_pro_iter=int(max_entfernen_pro_iter), u_faktor=(u_faktor))

        st.session_state.historie = historie 

        #Nach optimierung direkt neu lösen (damit in Ansicht sofort deformiert da ist)
        u, mapping = loese_aktuelle_struktur(struktur)
        st.session_state.u = u 
        st.session_state.mapping = mapping 

        st.success("Optimierung abgeschlossen !! Schau in 'Ansicht' für das Ergebnis !!")
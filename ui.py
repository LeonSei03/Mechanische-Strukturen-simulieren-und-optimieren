import streamlit as st
import numpy as np
from optimierung import TopologieOptimierer

from ui_logik import (
    struktur_bauen,
    plot_struktur,
    loese_aktuelle_struktur,
    entwurf_auf_struktur_anwenden,
    reset_ui_state_bei_neuer_struktur
)

st.set_page_config(page_title="Balken Optimierung", layout="wide")
st.title("Balkenbiegung - Simulation & Topologieoptimierung")


#Session states initialisieren damit alles stabil bleibt 
if "entwurf_kraefte" not in st.session_state:
    st.session_state.entwurf_kraefte = {} #Knoten_id : (fx, fz)

if "entwurf_lager" not in st.session_state:
    st.session_state.entwurf_lager = {} #Knoten_id: lager_typ_string

if "kraft_knoten_id" not in st.session_state:
    st.session_state.kraft_knoten_id = None

if "lager_knoten_id" not in st.session_state:
    st.session_state.lager_knoten_id = None

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

    skalierung = st.slider("Deformations-Skala (Dehnung skalieren damits anschaulicher ist)", 0.0, 25.0, 1.0)
    federn_anzeigen = st.checkbox("Federn anzeigen", value=True)
    knoten_ids_anzeigen = st.checkbox("Knoten-Ids anzeigen (debug)", value=False)  

    uebernehmen = st.form_submit_button("Übernehmen (Struktur neu erzeugen)")

#Struktur erzeugen (beim ersten Start, oder wenn User "Übernehmen" drückt)
if uebernehmen or st.session_state.struktur is None:
    st.session_state.struktur = struktur_bauen(int(nx), int(nz), float(dx), float(dz), lager_modus)

    reset_ui_state_bei_neuer_struktur()
    st.session_state.historie = None
    st.rerun()

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
    aktuelle_masse = len(aktive_knoten)

    col_a, col_b = st.columns(2)
    col_a.metric("Startmasse (kg)", start_masse)
    col_b.metric("Aktuelle Masse (kg)", aktuelle_masse)

    fig = plot_struktur(struktur=struktur, u=st.session_state.u, mapping=st.session_state.mapping, skalierung=float(skalierung), titel=("Struktur (undeformiert bzw. deformiert)"), federn_anzeigen=federn_anzeigen, knoten_ids_anzeigen=knoten_ids_anzeigen, highlight_knoten_id=st.session_state
                        .kraft_knoten_id) 
    
    st.pyplot(fig, use_container_width=True)

#Tab 2 Knoten bearbeiten (mit Dropdown auswahl)
with tab_randbedingungen: 
    st.subheader("Knoten auswählen und Kraft/Lager setzen")

    aktive_ids = struktur.aktive_knoten_ids()
    if not aktive_ids:
        st.warning("Keine aktiven Knoten vorhanden !!")
        st.stop()

    #Default Werte
    if st.session_state.kraft_knoten_id is None: 
        st.session_state.kraft_knoten_id = aktive_ids[0]
    if st.session_state.lager_knoten_id is None:
        st.session_state.lager_knoten_id = aktive_ids[0]

    col_links, col_rechts = st.columns(2)

    #Links der Kraft Editor 
    with col_links: 
        st.markdown("## Kräfte")

        with st.form("kraft_editor"):
            kraft_knoten = st.selectbox("Knoten für Kraft", options=aktive_ids, index=aktive_ids.index(st.session_state.kraft_knoten_id) if st.session_state.kraft_knoten_id in aktive_ids else 0, key="kraft_knoten_auswahl")

            #Werte aus dem Entwurf holen, sonst aus Struktur 
            if kraft_knoten in st.session_state.entwurf_kraefte: 
                fx0, fz0 = st.session_state.entwurf_kraefte[kraft_knoten]
            else: 
                k = struktur.knoten[kraft_knoten]
                fx0, fz0 = float(k.kraft_x), float(k.kraft_z)

            fx = st.number_input("Fx", value=float(fx0), key=f"fx_entwurf_{kraft_knoten}")
            fz = st.number_input("Fz", value=float(fz0), key=f"fz_entwurf_{kraft_knoten}")
            
            c1, c2 = st.columns(2)
            speichern_kraft = c1.form_submit_button("In Entwurf speichern")
            loeschen_kraft = c2.form_submit_button("Aus Entwurf löschen")

        if speichern_kraft: 
            st.session_state.entwurf_kraefte[kraft_knoten] = (float(fx), float(fz))
            st.session_state.kraft_knoten_id = kraft_knoten
            st.success(f"Kraft Entwurf für Knoten {kraft_knoten} gespeichert !!")
            st.rerun()

        if loeschen_kraft: 
            st.session_state.entwurf_kraefte.pop(kraft_knoten, None)
            st.session_state.kraft_knoten_id = kraft_knoten
            st.success(f"Kraft Entwurf für Knoten {kraft_knoten} entfernt !!")
            st.rerun()


        #Kleine Übersicht 
        st.caption(f"Aktive Kraft Entwürfe: {len(st.session_state.entwurf_kraefte)}")
        if st.session_state.entwurf_kraefte:
            daten = []
            for k_id, (fx, fz) in st.session_state.entwurf_kraefte.items():
                k = struktur.knoten[k_id]
                daten.append({
                "Knoten": k_id,
                "x": k.x,
                "z": k.z,
                "Fx": fx,
                "Fz": fz,
             })
            st.dataframe(daten, use_container_width=True, hide_index=True)
        else:
            st.info("Keine Kraft-Entwürfe vorhanden. Default Werte eingestellt !!")


#Rechte Spalte Lager Editor 
    with col_rechts:
        st.markdown("## Lager")

        with st.form("lager_editor"):
            lager_knoten = st.selectbox("Knoten für Lager", options=aktive_ids, index=aktive_ids.index(st.session_state.lager_knoten_id) if st.session_state.lager_knoten_id in aktive_ids else 0, key="lager_knoten_auswahl")

            lager_typ_default = st.session_state.entwurf_lager.get(lager_knoten, "Kein Lager")
            lager_typ = st.selectbox("Lagertyp für ausgewählten Knoten", ["Kein Lager", "Festlager", "Loslager (x frei, z fix)", "Loslager (x fix, z frei)"], index=["Kein Lager", "Festlager", "Loslager (x frei, z fix)", "Loslager (x fix, z frei)"].index(lager_typ_default), key=f"lager_typ_entwurf_{lager_knoten}")

            c1, c2 = st.columns(2)
            speichern_lager = c1.form_submit_button("In Entwurf speichern")
            loeschen_lager = c2.form_submit_button("Aus Entwurf löschen")

        if speichern_lager: 
            st.session_state.entwurf_lager[lager_knoten] = lager_typ
            st.session_state.lager_knoten_id = lager_knoten
            st.success(f"Lager Entwurf für Knoten {lager_knoten} gespeichert !!")            
            st.rerun()
        if loeschen_lager: 
            st.session_state.entwurf_lager.pop(lager_knoten, None)
            st.session_state.lager_knoten_id = lager_knoten
            st.success(f"Lager Entwurf für Knoten {lager_knoten} entfernt !!")        
            st.rerun()

        st.caption(f"Aktive Lager Entwürfe: {len(st.session_state.entwurf_lager)}")
        if st.session_state.entwurf_lager:
            daten = []
            for k_id, lager_typ in st.session_state.entwurf_lager.items():
                k = struktur.knoten[k_id]
                daten.append({
                    "Knoten": k_id,
                    "x": k.x,
                    "z": k.z,
                    "Lager": lager_typ,
                })
            st.dataframe(daten, use_container_width=True, hide_index=True)
        else:
            st.info("Keine Lager-Entwürfe vorhanden. Default Werte eingestellt !!")

    st.markdown("---")

    #Entwürfe anwenden 

    colA, colB = st.columns([1, 1])

    with colA: 
        if st.button("Etwürfe auf Struktur anwenden"):
            entwurf_auf_struktur_anwenden(struktur)
            st.success("Entwürfe angewendet. Jetzt kann man Solve drücken !!")
            st.rerun()

    with colB: 
        if st.button("Entwürfe zurücksetzten"): 
            st.session_state.entwurf_kraefte = {}
            st.session_state.entwurf_lager = {}
            st.success("Entwürfe gelöscht!!!")
            st.rerun()

#Tab 3 Solve 
with tab_solve:
    st.subheader("System lösen")

    if st.button("Solve"):
        u, mapping = loese_aktuelle_struktur(st.session_state.struktur)
        if u is None: 
            st.error("Solver: System nicht lösbar (evtl. zu wenig Lager / instabil) !!")
        else: 
            st.session_state.u = u
            st.session_state.mapping = mapping 
            st.success("Gelöst !! Wechsel zu 'Ansicht' um die deformierte Struktur zu sehen !!")
            st.rerun()

# Tab 4 Optimierung 
# Tab 4 Optimierung
with tab_optimierung:
    st.subheader("Topologieoptimierung (Masse reduzieren)")
    st.write("Ziel: Anzahl aktiver Knoten reduzieren (1 Knoten = 1kg), bis die Zielmasse erreicht ist!!")

    # Optimierungs-Parameter gehören hierher (nicht in die Sidebar-Form)
    with st.form("optim_form"):
        ziel_anteil_opt = st.slider(
            "Ziel-Massenanteil (z.B 0,5 ist die Hälfte der Masse behalten)",
            0.05, 0.95, 0.50, 0.01
        )
        max_iter_opt = st.number_input("Max. Iterationen", 1, 50, 5)
        max_entfernen_pro_iter_opt = st.number_input(
            "max_entfernen_pro_iter (max Anzahl an Knoten welche pro iter versucht wird wegzumachen)",
            1, 200, 3
        )
        u_faktor_opt = st.number_input(
            "u_faktor (zugelassene Dehnung vor Rollback)",
            0.1, 200.0, 3.0, 0.1
        )

        opt_start = st.form_submit_button("Optimierung starten")

    if opt_start:
        # Optional: Startmasse einmal festhalten, falls noch nicht gesetzt
        if "start_masse" not in st.session_state or st.session_state.start_masse is None:
            st.session_state.start_masse = len(st.session_state.struktur.aktive_knoten_ids())

        opt = TopologieOptimierer(st.session_state.struktur)

        historie = opt.optimierung(
            ziel_anteil=float(ziel_anteil_opt),
            max_iter=int(max_iter_opt),
            max_entfernen_pro_iter=int(max_entfernen_pro_iter_opt),
            u_faktor=float(u_faktor_opt),
        )

        st.session_state.historie = historie

        # Nach Optimierung: Ansicht soll UNDEFORMIERT die optimierte Struktur zeigen
        st.session_state.u = None
        st.session_state.mapping = None

        st.success("Optimierung abgeschlossen! Ergebnis unten (undeformiert) und in 'Ansicht'.")
        st.rerun()

    # Ergebnisplot (undeformiert) im Optimierungs-Tab anzeigen
    if st.session_state.get("historie") is not None:
        st.markdown("### Optimierte Struktur (undeformiert)")
        fig_opt = plot_struktur(
            struktur=st.session_state.struktur,
            u=None,
            mapping=None,
            skalierung=1.0,
            titel="Optimierte Struktur (undeformiert)",
            federn_anzeigen=federn_anzeigen,
            knoten_ids_anzeigen=knoten_ids_anzeigen,
            highlight_knoten_id=None,
        )
        st.pyplot(fig_opt, use_container_width=True)

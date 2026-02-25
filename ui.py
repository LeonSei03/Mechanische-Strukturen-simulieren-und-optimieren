import streamlit as st
import numpy as np
from optimierung import TopologieOptimierer
import matplotlib.pyplot as plt
import io
from checkpoint_database import (
    checkpoint_eintrag_anlegen,
    checkpoints_auflisten,
    checkpoint_holen,
    checkpoint_loeschen
)

from ui_logik import (
    struktur_bauen,
    plot_struktur,
    loese_aktuelle_struktur,
    entwurf_auf_struktur_anwenden,
    reset_ui_state_bei_neuer_struktur,
    checkpoint_speichern,
    checkpoint_laden,
    pruefe_lagerung_genug
)

from animation_aufnehmen import (
    fig_zu_pil,
    pil_liste_zu_gif
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

if "start_masse" not in st.session_state: 
    st.session_state.start_masse = None 

# sessionstates für optimierung
if "optimierer" not in st.session_state:
    st.session_state.optimierer = None

if "optimierung_laeuft" not in st.session_state:
    st.session_state.optimierung_laeuft = False

if "stop_angefordert" not in st.session_state:
    st.session_state.stop_angefordert = False

if "checkpoint_pfad" not in st.session_state:
    st.session_state.checkpoint_pfad = None

#Damit die Flash-Messages angezeigt werden überall 
if "flash" not in st.session_state:
    st.session_state.flash = [] #Liste für (type und text)

# Sessionstates für die Video Animation
if "gif_frames" not in st.session_state:
    st.session_state.gif_frames = []

if "gif_recording" not in st.session_state:
    st.session_state.gif_recording = False

def flash(type: str, text: str):
    #type sind success, info, warning und error 
    st.session_state.flash.append((type, text))

def show_flash():
    if st.session_state.flash:
        for type, text in st.session_state.flash:
            getattr(st, type)(text)
        st.session_state.flash.clear()

show_flash()

# Seitenleiste und alle Parameter die wir brauchen abfragen und als FORM, damit änderungen erst bei klick übernommen werden 
with st.sidebar.form("parameter_form"):
    st.header("Geometrie / Lager")

    nx = st.number_input("Anzahl Knoten in x (nx)", 5, 200, 30)
    nz = st.number_input("Anzahl Knoten in z (nz)", 3, 200, 15)
    dx = st.number_input("Abstand x (dx)", 0.1, 10.0, 1.0)
    dz = st.number_input("Abstand z (dz)", 0.1, 10.0, 1.0)

    lager_modus = st.selectbox("Lager (Start)", ["Knoten einzeln", "Knotenspalte"])

    st.markdown("---")

    uebernehmen = st.form_submit_button("Neue Struktur erzeugen")

#aus dem Form herausgezogen für dynamische Darstellung druch automatischen rerun für Federn und Knoten ID
st.sidebar.markdown("---")
st.sidebar.subheader("### Darstellung")
skalierung = st.sidebar.slider("Deformations-Skala (Dehnung skalieren damits anschaulicher ist)", 0.1, 5.0, 1.0, 0.1, key="skalierung")
federn_anzeigen = st.sidebar.checkbox("Federn anzeigen", value=False, key="federn_anzeigen")
knoten_ids_anzeigen = st.sidebar.checkbox("Knoten-Ids anzeigen (debug)", value=False, key="knoten_ids_anzeigen")

#Heatmap Einstellungen in der Sidebar (wie Feder anzeigen IDs anzeigen)
st.sidebar.markdown("---")
st.sidebar.subheader("Heatmap")

heatmap_modus = st.sidebar.radio("Heatmap-Modus", options=["Keine", "Verschiebung (Knoten)", "Federenergie", "Federkraft"], index=0, key="heatmap_modus")

colorbar_anzeigen = st.sidebar.checkbox("Farblegende (Colorbar) anzeigen", value=True, key="colorbar_anzeigen")

#Federn müssen natürlich sichtbar sein wenn man heatmap anschaltet, also checkbox richtig setzten 
if heatmap_modus in ("Federenergie", "Federkraft"):
    federn_anzeigen = True 

#Struktur erzeugen (beim ersten Start, oder wenn User "Übernehmen" drückt)
if uebernehmen or st.session_state.struktur is None:
    st.session_state.struktur = struktur_bauen(int(nx), int(nz), float(dx), float(dz), lager_modus)
    st.session_state.start_masse = len(st.session_state.struktur.aktive_knoten_ids())
    reset_ui_state_bei_neuer_struktur()
    st.session_state.historie = None
    st.rerun()

struktur = st.session_state.struktur 

#Text bevor die Struktur erstellt wird falls noch keine da 
if struktur is None:
    st.info("Erstellen Sie mit den Paramteren links in der Seitenleiste eine Struktur um daran arbeiten zu können!") 
    st.stop()

#Hauptlayout für Tabs bzw. Überischt 
tab_ansicht, tab_optimierung, tab_plots = st.tabs(["Ansicht", "Optimierung", "Verlaufplots"])

#Tab 1 Ansicht (Preview immer sichtbar)
with tab_ansicht:
    st.subheader("Vorschau / Ergebnis")

    #Masse Infos (1 Knoten = 1kg)
    aktive_knoten = struktur.aktive_knoten_ids()
    aktuelle_masse = len(aktive_knoten)
    start_masse = st.session_state.start_masse if st.session_state.start_masse is not None else aktuelle_masse

    col_a, col_b = st.columns(2)
    col_a.metric("Startmasse (kg)", start_masse)
    col_b.metric("Aktuelle Masse (kg)", aktuelle_masse)

    lastpfad = st.session_state.struktur.finde_lastpfad_knoten()

    fig = plot_struktur(struktur=struktur, u=st.session_state.u, mapping=st.session_state.mapping, skalierung=float(skalierung), titel=("Struktur (undeformiert bzw. deformiert)"), federn_anzeigen=federn_anzeigen, knoten_ids_anzeigen=knoten_ids_anzeigen, lastpfad_knoten=lastpfad, heatmap_modus=heatmap_modus, colorbar_anzeigen=colorbar_anzeigen)
    
    st.pyplot(fig, use_container_width=True)

    # Plot als PNG herunterladen
    puffer = io.BytesIO()

    # Figure in den Buffer schreiben
    fig.savefig(puffer, format="png", bbox_inches="tight", dpi=200)
    puffer.seek(0)

    st.download_button(
    label="Optimierte Struktur als PNG herunterladen",
    data=puffer,
    file_name="struktur_ansicht.png",
    mime="image/png"
    )

    #Knoten bearbeiten (mit Dropdown auswahl)
    st.markdown("---")
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

            fx = st.number_input("Fx", value=float(fx0))#, key=f"fx_entwurf_{kraft_knoten}")
            fz = st.number_input("Fz", value=float(fz0))#, key=f"fz_entwurf_{kraft_knoten}")
            
            c1, c2 = st.columns(2)
            speichern_kraft = c1.form_submit_button("In Entwurf speichern")
            loeschen_kraft = c2.form_submit_button("Aus Entwurf löschen")

        if speichern_kraft: 
            st.session_state.entwurf_kraefte[kraft_knoten] = (float(fx), float(fz))
            st.session_state.kraft_knoten_id = kraft_knoten
            flash("success", f"Kraft Entwurf für Knoten {kraft_knoten} gespeichert !!")
            #st.success(f"Kraft Entwurf für Knoten {kraft_knoten} gespeichert !!")
            st.rerun()

        if loeschen_kraft: 
            st.session_state.entwurf_kraefte.pop(kraft_knoten, None)
            st.session_state.kraft_knoten_id = kraft_knoten
            flash("success", f"Kraft Entwurf für Knoten {kraft_knoten} entfernt !!")
            #st.success(f"Kraft Entwurf für Knoten {kraft_knoten} entfernt !!")
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
            lager_knoten = st.selectbox("Knoten für Lager", options=aktive_ids, index=aktive_ids.index(st.session_state.lager_knoten_id) if st.session_state.lager_knoten_id in aktive_ids else 0)

            lager_typ_default = st.session_state.entwurf_lager.get(lager_knoten, "Kein Lager")
        
            lager_typ = st.selectbox("Lagertyp für ausgewählten Knoten", ["Kein Lager", "Festlager", "Loslager (x frei, z fix)", "Loslager (x fix, z frei)"], index=["Kein Lager", "Festlager", "Loslager (x frei, z fix)", "Loslager (x fix, z frei)"].index(lager_typ_default))

            c1, c2 = st.columns(2)
            speichern_lager = c1.form_submit_button("In Entwurf speichern")
            loeschen_lager = c2.form_submit_button("Aus Entwurf löschen")

        if speichern_lager: 
            st.session_state.entwurf_lager[lager_knoten] = lager_typ
            st.session_state.lager_knoten_id = lager_knoten
            flash("success", f"Lager Entwurf für Knoten {lager_knoten} gespeichert !!")
            #st.success(f"Lager Entwurf für Knoten {lager_knoten} gespeichert !!")            
            st.rerun()
        if loeschen_lager: 
            st.session_state.entwurf_lager.pop(lager_knoten, None)
            st.session_state.lager_knoten_id = lager_knoten
            flash("success", f"Lager Entwurf für Knoten {lager_knoten} entfernt !!")
            #st.success(f"Lager Entwurf für Knoten {lager_knoten} entfernt !!")        
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
            flash("success", "Entwürfe angewendet. Jetzt kann man Solve drücken")
            #st.success("Entwürfe angewendet. Jetzt kann man Solve drücken !!")
            st.rerun()

    with colB: 
        if st.button("Entwürfe zurücksetzten"): 
            st.session_state.struktur = struktur_bauen(int(nx), int(nz), float(dx), float(dz), lager_modus)
            st.session_state.entwurf_kraefte = {}
            st.session_state.entwurf_lager = {}
            st.session_state.u = None 
            st.session_state.mapping = None
            flash("success", "Entwürfe gelöscht und Struktur aktualisiert")
            #st.success("Entwürfe gelöscht!!!")
            st.rerun()

    #System lösen button 
    st.subheader("System lösen")

    if st.button("Solve"):
        if not pruefe_lagerung_genug(st.session_state.struktur):
            st.error("System ist unvollständig gelagert, keine eindeutige Lösung möglich!")
        else:
            u, mapping = loese_aktuelle_struktur(st.session_state.struktur)
            if u is None: 
                st.error("Solver: System nicht lösbar (evtl. zu wenig Lager / instabil) !!")
            else: 
                st.session_state.u = u
                st.session_state.mapping = mapping 
                flash("success", "System gelöst !!")
                #st.success("Gelöst !! Wechsel zu 'Ansicht' um die deformierte Struktur zu sehen !!")
                st.rerun()

# Tab 4 Optimierung
with tab_optimierung:
    st.subheader("Topologieoptimierung (Masse reduzieren)")
    st.write("Ziel: Anzahl aktiver Knoten reduzieren (1 Knoten = 1kg), bis die Zielmasse erreicht ist!!")

    # Optimierungs-Parameter gehören hierher (nicht in die Sidebar-Form)
    with st.form("optim_form"):
        strategie_opt = st.selectbox(
            "Optimierungsstrategie",
            options=["energie", "dijkstra"],
            format_func=lambda s: "Energiebasiert (lokal)" if s == "energie" else "Dijkstra-Lastpfad (global geschützt)"
        )

        dijkstra_ring_opt = st.slider("Dijkstra: Pfad-Schutz (Nachbarschaft)", 0, 2, 0)

        ziel_anteil_opt = st.slider(
            "Ziel-Massenanteil (z.B 0,5 ist die Hälfte der Masse behalten)",
            0.05, 0.95, 0.50, 0.01
        )
        max_iter_opt = st.number_input("Max. Iterationen", 1, 200, 5)
        max_entfernen_pro_iter_opt = st.number_input(
            "max_entfernen_pro_iter (max Anzahl an Knoten welche pro iter versucht wird wegzumachen)",
            1, 200, 3
        )
        u_faktor_opt = st.number_input(
            "u_faktor (zugelassene Dehnung vor Rollback)",
            0.1, 200.0, 3.0, 0.1
        )

        start_neu = st.form_submit_button("Optimierung starten")

        st.session_state.gif_recording = st.checkbox("GIF Recording aktiv", value=st.session_state.gif_recording)

    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

    with col1:
        weiter = st.button("Weiter (1 Schritt)", use_container_width=True)

    # das man komplett einmal Optimieren kann in schnell 
    with col2:
        schnell_durchlaufen = st.button("Optimierung komplett durchlaufen (schnell, nicht stoppbar)", use_container_width=True)

    with col3:
        auto_weiter = st.button("Auto-Weiter", use_container_width=True)

    with col4:
        stop = st.button("Stop", use_container_width=True)

    with col5:
        speichern = st.button("Speichern", use_container_width=True)

    with col6:
        laden = st.button("Laden / Fortsetzen", use_container_width=True)

    with col7:
        loeschen = st.button("Checkpoint löschen", use_container_width=True)

    if start_neu:
        # neuer optimierer mit aktueller Struktur erzeugen
        opt = TopologieOptimierer(st.session_state.struktur)

        # Parameter setzen und Verschiebungsgrenze berechnen
        opt.optimierung_initialisieren(
            ziel_anteil=float(ziel_anteil_opt),
            max_iter=int(max_iter_opt),
            max_entfernen_pro_iter=int(max_entfernen_pro_iter_opt),
            u_faktor=float(u_faktor_opt),
            strategie=strategie_opt,
            dijkstra_neighbor_ring=int(dijkstra_ring_opt)
        )

        # optimierer wird im Sessionstate gespeichert
        st.session_state.optimierer = opt
        st.session_state.historie = opt.verlauf
        st.session_state.optimierung_laeuft = False
        st.session_state.stop_angefordert = False

        # Ansicht auf undeformiert setzen
        st.session_state.u = None
        st.session_state.mapping = None

        st.success("Optimierung initialisiert. Du kannst jetzt Schrittweise laufen lassen.")
        st.rerun()
    
    # zwischen zwei Iterationen greift
    if stop: 
        st.session_state.stop_angefordert = True
        st.session_state.optimierung_laeuft = False
        st.info("Stop angefordert. Optimierung hält nach dem aktuellen Schritt an.")
        st.rerun()

    # checkpoint abspeichern
    if speichern:
        if st.session_state.optimierer is None:
            st.warning("Kein Optimierungslauf vorhanden!!")
        else:
            # gesamten Zustand abspeichern
            zustand = st.session_state.optimierer.zustand_exportieren()
            
            # mit Pickle abspeichern
            pfad = checkpoint_speichern(zustand)

            opt = st.session_state.optimierer

            parameter = {
                "ziel_anteil": opt.ziel_materialanteil,
                "max_iter": opt.max_iterationen,
                "max_entfernen_pro_iter": opt.max_entfernen_pro_iteration,
                "u_faktor": opt.u_faktor,
            }

            info = {
                "iteration": opt.aktuelle_iteration,
                "aktive_knoten": len(opt.struktur.aktive_knoten_ids()),
            }

            # Eintrag in Tinydb
            doc_id = checkpoint_eintrag_anlegen(pfad=pfad, name="Checkpoint", parameter=parameter, info=info)

            st.success(f"Checkpoint gespeichert!! Database ID: {doc_id}")

    st.markdown("### Gespeicherte Checkpoints")

    alle = checkpoints_auflisten()
    
    if not alle:
        st.info("Bitte erst einen Checkpoint anlegen!!")
        ausgewahlter_doc_id = None
    else:
        optionen = []
        for d in alle:
            doc_id = d.doc_id
            zeit = d.get("zeitpunkt")
            iteration = d.get("info", {}).get("iteration", "?")

            optionen.append((doc_id, f"[{doc_id}] gestoppt bei {iteration}. Iteration | {zeit}"))
        
        labels = [txt for _, txt in optionen]
        idx = st.selectbox("Checkpoint auswählen", range(len(labels)), format_func=lambda i: labels[i])

        ausgewahlter_doc_id = optionen[idx][0]

    # Checkpoint ladne und mit optimierung fortsetzen
    if laden:
        if ausgewahlter_doc_id is None:
            st.warning("Kein Checkpoint auswählbar!!")
        else:
            # checkpoint laden
            eintrag = checkpoint_holen(int(ausgewahlter_doc_id))

            if not eintrag:
                st.error("Kein Checkpoint Eintrag gefunden!!")
            else:
                pfad = eintrag["pfad"]

                # pickle datei laden
                daten = checkpoint_laden(pfad)
                
                # optimierer neu erzeugen
                opt = TopologieOptimierer(daten["struktur"])

                # Zustand holen
                opt.zustand_importieren(daten)

            # sessionstates aktualisieren
            st.session_state.optimierer = opt
            st.session_state.struktur = opt.struktur
            st.session_state.historie = opt.verlauf

            st.session_state.optimierung_laeuft = False
            st.session_state.stop_angefordert = False

            # Ansicht zurücksetzen
            st.session_state.u = None
            st.session_state.mapping = None

            st.success("Checkpoint geladen. Du kannst jetzt weiterlaufen.")
            st.rerun()

    if loeschen:
        if ausgewahlter_doc_id is None:
            st.warning("Kein Checkpoint ist ausgewählt!!")
        else:
            ok, msg = checkpoint_loeschen(int(ausgewahlter_doc_id))

            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    if schnell_durchlaufen:
        if st.session_state.optimierer is None:
            st.warning("Bitte zuerst 'Optimierung starten (neu)' oder 'Laden / Fortsetzen'.")
        else:
            # Interaktiven Lauf deaktivieren
            st.session_state.optimierung_laeuft = False
            st.session_state.stop_angefordert = False

            # nur jeden k-ten schritt als frame speichern
            frame_stride = 2
            max_frames = 250

            # Optimierung komplett durchlaufen (nicht stoppbar)
            while not st.session_state.optimierer.optimierung_beendet:
                ok = st.session_state.optimierer.optimierung_schritt()

                # UI aktualisieren
                st.session_state.historie = st.session_state.optimierer.verlauf
                st.session_state.struktur = st.session_state.optimierer.struktur
                st.session_state.u = None
                st.session_state.mapping = None

                # Frame aufnehmen, wenn Recording aktiv
                if st.session_state.get("gif_recording", False):
                    # Nur jeden k-ten Step speichern + max_frames cap
                    if (st.session_state.optimierer.aktuelle_iteration % frame_stride == 0
                            and len(st.session_state.gif_frames) < max_frames):

                        struktur_plot = st.session_state.struktur
                        lastpfad = struktur_plot.finde_lastpfad_knoten()
                        fig_frame = plot_struktur(
                            struktur=struktur_plot,
                            u=None,
                            mapping=None,
                            skalierung=1.0,
                            titel="Optimierte Struktur (undeformiert)",
                            federn_anzeigen=federn_anzeigen,
                            knoten_ids_anzeigen=knoten_ids_anzeigen,
                            lastpfad_knoten=lastpfad,
                            heatmap_modus=heatmap_modus,
                            colorbar_anzeigen=colorbar_anzeigen,
                        )

                        img = fig_zu_pil(fig_frame, dpi=120)
                        st.session_state.gif_frames.append(img)
                
                if ok is False:
                    break
            
            # UI aktualisieren zur sicherheit
            st.session_state.historie = st.session_state.optimierer.verlauf
            st.session_state.struktur = st.session_state.optimierer.struktur
            st.session_state.u = None
            st.session_state.mapping = None

            st.success(
                f"Optimierung (Schnellmodus) beendet: "
                f"{st.session_state.optimierer.abbruch_grund}"
            )

            st.rerun()


    # einzelnen Optimierungsschritt durchführen
    if weiter:
        if st.session_state.optimierer is None:
            st.warning("Bitte zuerst 'Optimierung starten (neu)' oder 'Laden / Fortsetzen'!!")
        else:

            opt = st.session_state.optimierer

            if opt.optimierung_beendet:
                st.info(f"Optimierung ist bereits beendet: {opt.abbruch_grund}")

            else:
                ok = opt.optimierung_schritt()

                # Ui zustände aktualisieren
                st.session_state.historie = st.session_state.optimierer.verlauf
                st.session_state.struktur = st.session_state.optimierer.struktur
                
                # Ansicht undeformiert halten
                st.session_state.u = None
                st.session_state.mapping = None

                # Plot aus dem aktualisierten Zustand erstellen
                struktur_plot = st.session_state.struktur
                lastpfad = struktur_plot.finde_lastpfad_knoten()
                fig = plot_struktur(
                    struktur=struktur_plot,
                    u=None,
                    mapping=None,
                    skalierung=1.0,
                    titel="Optimierte Struktur (undeformiert)",
                    federn_anzeigen=federn_anzeigen,
                    knoten_ids_anzeigen=knoten_ids_anzeigen,
                    lastpfad_knoten=lastpfad,
                    heatmap_modus=heatmap_modus,
                    colorbar_anzeigen=colorbar_anzeigen,
                )
                st.pyplot(fig, use_container_width=True)

                # Frame speichern (nach dem Plot)
                if st.session_state.gif_recording:
                    img = fig_zu_pil(fig, dpi=120)
                    st.session_state.gif_frames.append(img)

                st.rerun() 

    if auto_weiter:
        if st.session_state.optimierer is None:
            st.warning("Bitte zuerst 'Optimierung starten (neu)' oder 'Laden / Fortsetzen'!!")
        else:
            st.session_state.optimierung_laeuft = True
            st.session_state.stop_angefordert = False
            st.rerun()

    # wenn auto_lauf aktiv ist, dann pro rerun nur einen schritt
    if st.session_state.optimierung_laeuft and st.session_state.optimierer is not None:
        if st.session_state.stop_angefordert:
            st.session_state.optimierung_laeuft = False
        else:
            if not st.session_state.optimierer.optimierung_beendet:
                st.session_state.optimierer.optimierung_schritt()

            st.session_state.historie = st.session_state.optimierer.verlauf
            st.session_state.struktur = st.session_state.optimierer.struktur

            st.session_state.u = None
            st.session_state.mapping = None

            # gif frame aufnehmen für das video
            if st.session_state.get("gif_recording", False):
                struktur_plot = st.session_state.struktur
                lastpfad = struktur_plot.finde_lastpfad_knoten()
                fig_frame = plot_struktur(
                    struktur=struktur_plot,
                    u=None,
                    mapping=None,
                    skalierung=1.0,
                    titel="Optimierte Struktur (undeformiert)",
                    federn_anzeigen=federn_anzeigen,
                    knoten_ids_anzeigen=knoten_ids_anzeigen,
                    lastpfad_knoten=lastpfad,
                    heatmap_modus=heatmap_modus,
                    colorbar_anzeigen=colorbar_anzeigen,
                )

                # fig -> PIL image und speichern
                img = fig_zu_pil(fig_frame, dpi=120)   # dein helper (oder fig_zu_pil)
                st.session_state.gif_frames.append(img)

            # Fertig?
            if st.session_state.optimierer.optimierung_beendet:
                st.session_state.optimierung_laeuft = False
                st.success(f"Optimierung beendet: {st.session_state.optimierer.abbruch_grund}")
            else:
                st.rerun()


    # Ergebnisplot (undeformiert) im Optimierungs-Tab anzeigen
    if st.session_state.get("historie") is not None:
        st.markdown("### Optimierte Struktur (undeformiert)")

        struktur_plot = st.session_state.struktur
        lastpfad = struktur_plot.finde_lastpfad_knoten()
        fig_opt = plot_struktur(
            struktur=struktur_plot,
            u=None,
            mapping=None,
            skalierung=1.0,
            titel="Optimierte Struktur (undeformiert)",
            federn_anzeigen=federn_anzeigen,
            knoten_ids_anzeigen=knoten_ids_anzeigen,
            lastpfad_knoten=lastpfad, 
            heatmap_modus=heatmap_modus, 
            colorbar_anzeigen=colorbar_anzeigen,
        )
        st.pyplot(fig_opt, use_container_width=True)
        
        # Plot als PNG herunterladen
        puffer = io.BytesIO()

        # Figure in den Buffer schreiben
        fig_opt.savefig(puffer, format="png", bbox_inches="tight", dpi=200)
        puffer.seek(0)

        st.download_button(
        label="Optimierte Struktur als PNG herunterladen",
        data=puffer,
        file_name="optimierte_struktur.png",
        mime="image/png"
        )

        colA, colB, colC = st.columns(3)
        with colA:
            if st.button("Alle letzten Frames löschen"):
                st.session_state.gif_frames = []
        with colB:
            st.write(f"Frames: {len(st.session_state.gif_frames)}")
        with colC:
            gif_fps = st.slider("GIF Speed (FPS)", 1, 20, 8)

        # GIF erstellen und Download
        colG1, colG2 = st.columns(2)

        with colG1:
            if st.button("GIF erstellen"):
                if len(st.session_state.gif_frames) == 0:
                    st.warning("Keine Frames vorhanden. Erst Recording aktivieren und ein paar Schritte laufen lassen.")
                else:
                    duration_ms = int(1000 / gif_fps)
                    gif_bytes = pil_liste_zu_gif(st.session_state.gif_frames, duration_ms=duration_ms)

                    if gif_bytes is None:
                        st.warning("GIF konnte nicht erstellt werden.")
                    else:
                        st.image(gif_bytes)
                        st.download_button(
                            label="GIF downloaden",
                            data=gif_bytes,
                            file_name="optimierung.gif",
                            mime="image/gif"
                        )

        with colG2:
            # Optional: Frames limitieren / Info
            st.write(f"Aktuell gespeicherte Frames: **{len(st.session_state.gif_frames)}**")


with tab_plots:
    st.subheader("Optimierungsverlauf")
    historie = st.session_state.get("historie")

    if not historie:
        st.info("Noch keine Optimierungshistorie verhanden, erst eine Struktur optimieren!!")
        st.stop()

    iterationen = [h.get("iteration", i) for i, h in enumerate(historie)]
    energien = [h.get("gesamtenergie") for h in historie]
    material = [h.get("material_anteil") for h in historie]
    aktive_knoten = [h.get("aktive_knoten") for h in historie]
    max_u = [h.get("max_u") for h in historie]
    u_grenze = [h.get("u_max_grenze") for h in historie]

    
    col1, col2, col3 = st.columns(3)

    with col1:
        # Plot der Gesamtenergie
        fig1 = plt.figure()
        plt.plot(iterationen, energien)
        plt.xlabel("Iteration")
        plt.ylabel("Gesamtenergie")
        plt.title("Gesamtenergie über Iterationen")
        plt.grid(True)
        st.pyplot(fig1, use_container_width=True)

    with col2:
        # Plot vom Materialanteil
        fig2 = plt.figure()
        plt.plot(iterationen, material)
        plt.xlabel("Iteration")
        plt.ylabel("Materialanteil")
        plt.title("Materialanteil über Iterationen")
        plt.grid(True)
        st.pyplot(fig2, use_container_width=True)

    with col3:
        # Plot der aktiven Knoten
        fig3 = plt.figure()
        plt.plot(iterationen, aktive_knoten)
        plt.xlabel("Iteration")
        plt.ylabel("Aktive Knoten")
        plt.title("Aktive Knoten über Iterationen")
        plt.grid(True)
        st.pyplot(fig3, use_container_width=True)

        if any(v is not None for v in max_u):
            fig4 = plt.figure()
            plt.plot(iterationen, max_u, label="max_u")
            plt.plot(iterationen, u_grenze, label="u_max_grenze")
            plt.xlabel("Iteration")
            plt.ylabel("Verschiebung")
            plt.title("Maximale Verschiebung vs. Grenze")
            plt.grid(True)
            plt.legend()
            st.pyplot(fig4, use_container_width=True)

    plt.close("all")
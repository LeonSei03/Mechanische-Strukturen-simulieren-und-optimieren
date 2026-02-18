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
def plot_knoten(struktur, u=None, mapping=None, skalierung=1.0, title="Struktur"):
    fig, ax = plt.subplots()
    
    # ursprüngliche Koordinaten
    xs, zs = struktur.koordinaten_knoten()
    ax.scatter(xs, zs, label="undeformiert")

    # Verformte Koordinaten
    if u is not None and mapping is not None:
        xs_d, zs_d = struktur.koordinaten_knoten_mit_verschiebung(u, mapping, skalierung=skalierung)
        ax.scatter(xs_d, zs_d, label=f"deformiert (skalierung={skalierung})")

        ax.set_aspect("equal", adjustable="box")
        ax.set_title(title)
        ax.set_xlabel("x")
        ax.set_ylabel("z")
        ax.legend()

        return fig
    
# Struktur aufbauen, wie in der main.py die test_optimierung
def struktur_bauen(nx, nz, dx, dz, lager_modus, last_i, last_j, fz):
    s = Struktur()
    
    s.gitter_erzeugen_knoten(nx, nz, dx, dz)
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

    last_knoten = s.knoten_id(last_i, last_j)
    s.kraft_setzen(last_knoten, fx=0.0, fz=fz)

    return s

st.set_page_config(page_title="Balken Optimierung", layout="wide")
st.title("Balkenbiegung - Simulation & Topologieoptimierung")

# Seitenleiste und alle Parameter die wir brauchen abfragen
st.sidebar.header("Geometrie / Last / Lager")

nx = st.sidebar.number_input("nx", 5, 200, 30)
nz = st.sidebar.number_input("nz", 3, 200, 15)
dx = st.sidebar.number_input("dx", 0.1, 10.0, 1.0)
dz = st.sidebar.number_input("dz", 0.1, 10.0, 1.0)

lager_modus = st.sidebar.selectbox("Lager", ["Knotenspalte", "Knoten einzeln"])

last_i = st.sidebar.number_input("Last i", 0, int(nx)-1, int(nx)//2)
last_j = st.sidebar.number_input("Last j", 0, int(nz)-1, int(nz)//2)
fz = st.sidebar.number_input("Last fz", value=-10.0)

skalierung = st.sidebar.slider("Deformations-Skala (Dehnung skalieren damits anschaulicher ist)", 0.0, 20.0, 10.0)

st.sidebar.markdown("---")

st.sidebar.header("Optimierung")
ziel_anteil = st.sidebar.slider("ziel_anteil", 0.05, 0.95, 0.35, 0.01)
max_iter = st.sidebar.number_input("max_iter (wie oft wird optimiert)", 1, 50, 3)
max_entfernen_pro_iter = st.sidebar.number_input("max_entfernen_pro_iter (max Anzahl an Knoten welche pro iter versucht wird wegzumachen)", 1, 15, 3)
u_faktor = st.sidebar.number_input("u_faktor (zugelassene Dehnung vor Rollback)", 0.1, 200.0, 3.0, 0.1)

# session states
if "struktur" not in st.session_state:
    st.session_state.struktur = None

if "historie" not in st.session_state:
    st.session_state.historie = None

# Buttons
col1, col2, col3 = st.columns(3)

# Struktur erzeugen
with col1:
    if st.button("Struktur erzeugen"):
        s = struktur_bauen(nx, nz, dx, dz, lager_modus, last_i, last_j, fz)
        st.session_state.struktur = s
        st.session_state.historie = None

# struktur lösen und plotten
with col2:
    if st.button("Solve + Plot"):
        if st.session_state.struktur is None:
            st.warning("Erst Struktur erzeugen")
        else:
            u, mapping = loese_aktuelle_struktur(st.session_state.struktur)
            if u is None:
                st.error("Solver: System nicht lösbar!!")
            else:
                fig = plot_knoten(st.session_state.struktur, u=u, mapping=mapping, skalierung=skalierung, title="Startzustand")
                st.pyplot(fig)

# optimierung durchlaufen lassen
with col3:
    if st.button("OPtimierung Starten"):
        if st.session_state.struktur is None:
            st.warning("Erst Struktur erzeugen!!")
        else:
            opt = TopologieOptimierer(st.session_state.struktur)
            historie = opt.optimierung(ziel_anteil=ziel_anteil, max_iter=max_iter, max_entfernen_pro_iter=max_entfernen_pro_iter, u_faktor=u_faktor)
            st.session_state.historie = historie

            u, mapping = loese_aktuelle_struktur(st.session_state.struktur)
            st.session_state.u = u
            st.session_state.mapping = mapping

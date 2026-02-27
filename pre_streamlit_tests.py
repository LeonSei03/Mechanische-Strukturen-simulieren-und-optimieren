from feder import Feder
from knoten import Knoten
from struktur import Struktur
from ui import Ui
from solver import solve
import numpy as np
from optimierung import TopologieOptimierer
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

# Von hier alles aufrufen und ausführen
def main():
    """ 
    ====In dieser Datei wurden Tests für Plots etc durchgeführt vor die Streamlit anwendung aufgebaut war===== 
    """
    pass

def test_lager_kraft_system():
    s = Struktur()
    s.gitter_erzeugen_knoten(2, 2, 1, 1)
    s.gitter_erzeugen_federn(1, 1, 1/np.sqrt(2))

    #Lager setzen für test erwartete ausgabe fixe DOFs soll (0, 1, 3)
    #jedem Knoten hat zwei dof (in Struktur werden die indizes dieser dofs definiert)
    #Knoten 0 -> dofs(ux, uz) -> indizes (0, 1)
    #Knoten 1 -> dofs(ux, uz) -> indizes (2, 3)
    #Knoten 3 .......................... (4, 5)
    #Knoten 4 .......................... (6, 7)
    s.lager_setzen(0, True, True) #Festlager x und z beide true 
    s.lager_setzen(1, False, True) #Loslager x frei, z fest 

    #Kraft an gewählten Knoten setztn 
    s.kraft_setzen(3, fx=0, fz=10) 

    K, F, fixiert, mapping = s.system_aufbauen()

    u = solve(K, F, fixiert)

    print(f"fixierte DOFs:\n", fixiert)
    print(f"Kraft:\n", F)
    print(f"Matrix:\n", np.round(K, 3))
    print(f"\n Verschiebungsvektor gesamt:\n", np.round(u, 3))

    print(f"Verschiebung pro Knoten:")
    #wir gehen alle Knoten durch
    for k_id in sorted(mapping.keys()): 

        #Für diesen Knoten holen wir uns den index im globalen Verschiebungsvektor für ux und uz
        dof_index_x, dof_index_z = mapping[k_id]

        #zugehörige Werte aus Verschiebungsvektor u herauslesen 
        verschiebung_x = u[dof_index_x]
        verschiebung_z = u[dof_index_z]

        print(f"Knoten {k_id}:")
        print(f"   u_x = {verschiebung_x: .4f}")
        print(f"   u_z = {verschiebung_z: .4f}")

def test_energien_scores():
    s = Struktur()
    s.gitter_erzeugen_knoten(2, 2, 1, 1)
    s.gitter_erzeugen_federn(1, 1, 1/np.sqrt(2))

    s.lager_setzen(0, True, True)
    s.lager_setzen(1, False, True)
    s.kraft_setzen(3, fx=0, fz=10)

    opt = TopologieOptimierer(s)
    scores, energien, u = opt.knoten_scores_berechnen()

    print("Federenergien:", {k: round(v, 6) for k, v in energien.items()})
    print("Knotenscores:", {k: round(v, 6) for k, v in scores.items()})


def test_optimierung():
    print("\n== TEST: Topologieoptimierung ==\n")

    # Struktur aufbauen
    s = Struktur()
    s.gitter_erzeugen_knoten(30, 15, 1.0, 1.0)
    s.gitter_erzeugen_federn(1.0, 1.0, 1.0 / np.sqrt(2))

    nx = 30
    nz = 15

    # Lager + Last setzen
    # Beispiel: links eingespannt, rechts Last
    k_id_lager1 = s.knoten_id(0, 0)
    k_id_lager2 = s.knoten_id(29, 0)

    s.lager_setzen(k_id_lager1, True, True)
    s.lager_setzen(k_id_lager2, False, True)

    '''
    # ganze Linke Spalte als Lager
    for j in range(nz):
        k_id = s.knoten_id(0, j)
        s.lager_setzen(k_id, True, True)
    
    # ganze Rechte Spalte als Lager
    for j in range(nz):
        k_id = s.knoten_id(nx-1, j)
        s.lager_setzen(k_id, False, True)
    '''
         
    last_knoten = s.knoten_id(15, 14)
    s.kraft_setzen(last_knoten, fx=0, fz=-10)

    # Optimierer erzeugen
    opt = TopologieOptimierer(s)

    print("Lager:", s.lager_knoten_id())
    print("Last:", s.last_knoten_id())
    print("Connected:", s.ist_verbunden_last_zu_lager())

    print("Start aktive Knoten:", len(s.aktive_knoten_ids()))

    # Optimierung starten
    historie = opt.optimierung(
        ziel_anteil=0.50,
        max_iter=20,
        max_entfernen_pro_iter=10,
        u_faktor=1.5
    )

    print("\n--- Verlauf ---")
    
    for eintrag in historie:
        max_u = eintrag["max_u"]
        energie = eintrag["gesamtenergie"]

        max_u_str = f"{max_u:.3f}" if max_u is not None else "-"
        energie_str = f"{energie:.3f}" if energie is not None else "-"

        print(
            f"Iter {eintrag['iteration']:2d} | "
            f"Aktiv: {eintrag['aktive_knoten']:3d} | "
            f"Anteil: {eintrag['material_anteil']:.3f} | "
            f"Entfernt: {eintrag['entfernt']:2d} | "
            f"max_u: {max_u_str} | "
            f"Eges: {energie_str}"
        )
    print("\nEnde aktive Knoten:", len(s.aktive_knoten_ids()))

    K, F, fixiert, mapping = s.system_aufbauen()
    u = solve(K.copy(), F, fixiert)
    
    xs, zs = s.koordinaten_knoten()
    xs_d, zs_d = s.koordinaten_knoten_mit_verschiebung(u, mapping, skalierung=0.025)

    plt.figure()
    plt.scatter(xs, zs)
    plt.gca().set_aspect("equal", adjustable="box")
    plt.title("Struktur (undeformed)")
    plt.xlabel("x"); plt.ylabel("z")
    print("Plot wird jetzt angezeigt...")
    plt.show()
    print("Nach dem Plot")

    plt.figure()
    plt.scatter(xs, zs, label="undeformed")
    plt.scatter(xs_d, zs_d, label="deformed")
    plt.gca().set_aspect("equal", adjustable="box")
    plt.legend()
    plt.title("Verformung (Punkte)")
    plt.xlabel("x"); plt.ylabel("z")
    plt.show()
 
def test_hilfestellung():
    s = Struktur()
    s.gitter_erzeugen_knoten(anzahl_x=2, anzahl_z=2, dx=1.0, dz=1.0)
    s.gitter_erzeugen_federn(k_h=1, k_v=1, k_d=(1 / np.sqrt(2)))

    mapping = s.dof_map()

    K = s.steifigkeitsmatrix_aufbauen(mapping)

    print("\n === Knoten Positionen ===")
    for k_id in sorted(s.knoten.keys()):
        k = s.knoten[k_id]
        print(f"Knoten {k_id}: x = {k.x}, z = {k.z}")

    print("\n === Feder zwischen Knoten ===")
    for f_id in sorted(s.federn.keys()):
        f = s.federn[f_id]
        print(f"Feder {f_id}: {f.knoten_i} -> {f.knoten_j}")


    print("\n === Einheitsvektoren & lokale Matrizen ===")
    for f_id in sorted(s.federn.keys()):
        f = s.federn[f_id]
        e = s.feder_einheitsvektor(f_id)
        K_loc = s.lokale_feder_matrix(f_id)

        print(f"\n Feder {f_id}: ({f.knoten_i},{f.knoten_j})")
        print(f"e =", np.round(e, 3))
        print("K_lokal = \n", np.round(K_loc, 3))

    print("\n === Globale Steifigkeitsmatrix ===")
    print(np.round(K, 3))



if __name__ == "__main__":
    #======================Kannst du dir beide ausführen Lassen um zu schauen was rauskommt und ob alles passt für dich!!!================

    #test_hilfestellung()
    #test_lager_kraft_system()
    #test_energien_scores()
    #test_optimierung()

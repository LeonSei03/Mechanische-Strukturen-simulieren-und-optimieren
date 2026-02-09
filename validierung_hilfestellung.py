from struktur import Struktur
import numpy as np


def test_hilfestellung():
    
    s = Struktur()
    s.gitter_erzeugen_knoten(anzahl_x=2, anzahl_z=2, dx=1.0, dz=1.0)
    s.gitter_erzeugen_federn(k_h=1, k_v=1, k_d=(1 / np.sqrt(2)))

    mapping = s.dof_map()

    K = s.steifigkeitsmatrix_aufbauen(mapping)

    print("\n === Knoten Reihenfolge ===")
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
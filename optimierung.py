from solver import solve
import numpy as np
from struktur import Struktur

class TopologieOptimierer:
    def __init__(self, struktur):
        self.struktur: Struktur = struktur

    # aktuelle Struktur lösen (ohne Optimierung) für die max verschiebung der Ausgangsstruktur
    # damit wir nachher referenz haben zur Verschiebungs nebenbedingung
    def berechne_startverschiebung(self):
        # GLS aufbauen und lösen
        K, F, fixiert, mapping = self.struktur.system_aufbauen()
        u = solve(K.copy(), F, fixiert)

        if u is None:
            raise RuntimeError("Startstruktur ist nicht lösbar!!")

        # max Verschiebung
        max_u = float(np.max(np.abs(u)))
        return max_u

    # Funktion zum berechnen der Energie jeder aktiver Feder
    def feder_energien_berechnen(self):
        #GLS aufbauen und lösen
        K, F, fixiert, mapping = self.struktur.system_aufbauen()
        u = solve(K.copy(), F, fixiert)

        if u is None:
            return None, None, None, None
        
        energien = {}

        for f_id in self.struktur.aktive_federn_ids():
            feder = self.struktur.federn[f_id]

            # zur sicherheit für inaktive Endknoten
            if feder.knoten_i not in mapping or feder.knoten_j not in mapping:
                continue

            ix, iz = mapping[feder.knoten_i]
            jx, jz = mapping[feder.knoten_j]

            # Verschiebungsvektor (local)
            u_local = np.array([u[ix], u[iz], u[jx], u[jz]], dtype=float)

            # Steifigkeitsmatrix (local)
            K_local = self.struktur.lokale_feder_matrix(f_id)

            # Energie berechnen
            E = 0.5 * float(u_local.T @ K_local @ u_local)
            energien[f_id] = E 
        
        return energien, u, mapping, (K, F, fixiert)

    # Energiebasierte Scores berechnen für alle aktiven Knoten indem jeder Endknoten die hälfte der Energie bekommt
    def knoten_scores_berechnen(self):
        out = self.feder_energien_berechnen()
        
        if out[0] is None:
            return None, None, None
        
        energien, u, mapping, _ = out

        # scores für jeden aktiven Knoten initialisieren
        scores = {k_id: 0.0 for k_id in mapping.keys()}

        # jeder Feder die halbe Energie geben
        for f_id, E in energien.items():
            feder = self.struktur.federn[f_id]
            i = feder.knoten_i
            j = feder.knoten_j

            if i in scores:
                scores[i] += 0.5 * E
            if j in scores:
                scores[j] += 0.5 * E
        
        return scores, energien, u

    # Funktion um Knoten mit geringster Energie auszuwählen
    def auswahl_knoten_zum_entfernen(self, scores, anzahl):
        kandidaten = [
            (k_id, score) for k_id, score in scores.items()
            if not self.struktur.knoten_geschuetzt(k_id)
        ]
        # kleinster Score zuerst
        kandidaten.sort(key=lambda x: x[1])
        return[k_id for k_id, _ in kandidaten[:anzahl]]
    
    # eine Funktion die einen Optimierungsschritt macht, Knotenscores berechnen, Knoten mit niedrigstem score raus macht
    # u_max eingebaut, weil K manchmal doch noch invertierbar ist, obwohl zu viel material abgetragen wurde, deswegen machen wir nun auch rollback wenn die gesamtverscchiebung zu groß ist
    # damit sagen wir quasi das die Steifigkeit erhalten bleiben muss
    # versuchen 5Knoten zu entfernen, wenn danach K singulär ist oder u_max zu groß ist passiert ein Rollback und sind haben wieder den stand von vor den 5 gelöschten knoten
    # dann probieren wir 4 knoten zu löschen usw -> adaptiv
    def optimierungs_schritt_adaptiv_rollback(self, max_entfernen, u_max=None):
        print("max_entfernen =", max_entfernen)
        
        # knotenscores berechnen basiert auf energie der federn
        scores, energien, u = self.knoten_scores_berechnen()

        if scores is None:
            return False, 0, [], None, None
        
        # kleine debug ausgabe
        print("Kandidaten total:", len([k for k in scores.keys() if not self.struktur.knoten_geschuetzt(k)]))

        # adaptives entfernen der knoten
        for n in range(max_entfernen, 0, -1):

            # knoten mit niedrigstem score aussuchen
            entfernte_ids = self.auswahl_knoten_zum_entfernen(scores, n)
            print("Versuche n =", n, "-> bekomme", len(entfernte_ids))

            if not entfernte_ids:
                continue
            
            # falls Rollback
            snapshot = self.zustand_sichern()

            # Knoten entfernen
            for k_id in entfernte_ids:
                self.struktur.knoten_entfernen(k_id)
        
            # Bedingung prüfen ob lastknoten mit lagerknoten verbunden ist, sonst Rollback
            if not self.struktur.ist_verbunden_last_zu_lager():
               # print("Rollback: Connectivity verletzt (Last nicht mehr mit Lager verbunden).") # debug ausgabe
                self.zustand_wiederherstellen(snapshot)
                continue

            # system neu aufbauen und lösen
            K, F, fixiert, mapping = self.struktur.system_aufbauen()
            u_test = solve(K.copy(), F, fixiert)

            # falls Matrix singulär ist, passiert Rollback
            if u_test is None:
                self.zustand_wiederherstellen(snapshot)
                continue

            # max Verschiebung darf nicht zu groß sein
            max_u_val = float(np.max(np.abs(u_test)))

            # wenn max Verschiebung zu groß ist Rollback
            if u_max is not None and max_u_val > u_max:
                self.zustand_wiederherstellen(snapshot)
                continue
            
            # gesamtenergie für verlauf Plot nachher speichern
            energien2, u2, mapping2, _ = self.feder_energien_berechnen()
            gesamtenergie = float(sum(energien2.values()))

            return True, len(entfernte_ids), entfernte_ids, max_u_val, gesamtenergie

        return False, 0, [], None, None

    # Funktion für die gesamte Optimierung
    def optimierung(self, ziel_anteil=0.35, max_iter=50, max_entfernen_pro_iter=3, u_faktor=1.5):
        start = len(self.struktur.aktive_knoten_ids())
        historie = []
        
        # maximale zulässige Verschiebung bestimmen
        u_start_max = self.berechne_startverschiebung()
        u_max = u_faktor * u_start_max

        for it in range(max_iter):
            aktiv = len(self.struktur.aktive_knoten_ids())
            anteil = aktiv / start

            # Zielmaterial erreicht, abbrechen
            if anteil <= ziel_anteil:
                break
            
            # einen adaptiven optimierungsschritt ausführen 
            ok, entfernt_n, entfernte_ids, max_u, gesamtenergie = self.optimierungs_schritt_adaptiv_rollback(max_entfernen=max_entfernen_pro_iter, u_max=u_max)
            
            print("ITERATION", it)
            
            # Verlaufsdaten abspeichern
            historie.append({
                "iteration": it,
                "aktive_knoten": aktiv,
                "material_anteil": anteil,
                "entfernt": entfernt_n,
                "entfernte_ids": entfernte_ids,
                "max_u": max_u,
                "gesamtenergie": gesamtenergie,
                "u_max_limit": u_max
            })

            # abbrechen falls kein fortschritt möglich
            if not ok or entfernt_n == 0:
                break

        return historie
    
    # Funktion um entfernte Knoten "wiederherzustellen" falls diese die Struktur kaputt machen
    # Problem wenn wir zu viel entfernen, kann unsere Steifigkeitsmatrix singulär werden
    # das bedeutet unser System hat zu viele Freiheitsgrade und verschiebt sich unter Last, anstatt die kraft in Energie umzuwandeln
    # -> solver kann auch nicht mehr lösen
    
    # aktuellen Zustand speichern
    def zustand_sichern(self):
        return{
            "aktive_knoten": set(self.struktur.aktive_knoten_ids()),
            "aktive_federn": set(self.struktur.aktive_federn_ids())}

    # vorherigen Zustand wiedersherstellen
    def zustand_wiederherstellen(self, snapshot):

        aktive_knoten = snapshot["aktive_knoten"]
        aktive_federn = snapshot["aktive_federn"]

        # Knoten zurücksetzen
        for k_id, knoten in self.struktur.knoten.items():
            knoten.knoten_aktiv = (k_id in aktive_knoten)

        # Federn zurücksetzen
        for f_id, feder in self.struktur.federn.items():
            feder.feder_aktiv = (f_id in aktive_federn)


    



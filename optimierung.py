from solver import solve
import numpy as np
from struktur import Struktur

class TopologieOptimierer:
    def __init__(self, struktur):
        self.struktur: Struktur = struktur

        # für step/ fortsetzen
        self.optimierung_initialisiert = False
        self.optimierung_beendet = False
        self.abbruch_grund = None

        self.start_knotenanzahl = None
        self.ziel_materialanteil = None
        self.max_iterationen = None
        self.max_entfernen_pro_iteration = None
        self.u_faktor = None

        self.u_start_max = None
        self.u_max_grenze = None

        self.aktuelle_iteration = 0
        self.verlauf = []

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

    # Funktion welche uns einen neuen optimierungslauf initialisiert
    def optimierung_initialisieren(self, ziel_anteil=0.35, max_iter=50, max_entfernen_pro_iter=3, u_faktor=1.5):
        # Anzahl aktiver Knoten am Anfang
        self.start_knotenanzahl = len(self.struktur.aktive_knoten_ids())

        # Parameter
        self.ziel_materialanteil = ziel_anteil
        self.max_iterationen = max_iter
        self.max_entfernen_pro_iteration = max_entfernen_pro_iter
        self.u_faktor = u_faktor

        # Verschiebungsgrenze (wie oben)
        self.u_start_max = self.berechne_startverschiebung()
        self.u_max_grenze = self.u_faktor * self.u_start_max

        # Iteration zurücksetzen
        self.aktuelle_iteration = 0
        self.verlauf = []

        # Steuerflags setzen
        self.optimierung_beendet = False
        self.abbruch_grund = None
        self.optimierung_initialisiert = True

    # genau eine optimierung ausführen und speichern
    def optimierung_schritt(self):
        
        if not self.optimierung_initialisiert:
            raise RuntimeError("Optimierung nicht initalisiert!!")
        
        if self.optimierung_beendet:
            return False
        
        # aktuellen Materialanteil besitmmen
        aktive_knoten = len(self.struktur.aktive_knoten_ids())
        materialanteil = aktive_knoten / self.start_knotenanzahl

        # wenn Zielmaterial erreichr wird
        if materialanteil <= self.ziel_materialanteil:
            self.optimierung_beendet = True
            self.abbruch_grund = "Ziel Materialanteil erreicht"
            return False
        
        # wenn max iterationen erreich sind
        if self.aktuelle_iteration >= self.max_iterationen:
            self.optimierung_beendet = True
            self.abbruch_grund = "Max Iterationszahl erreicht"
            return False
        
        # Funktion "optimierungs_schritt_adaptiv_rollback" aufrufen und durchführen
        ok, entfernt_n, entfernte_ids, max_u, gesamtenergie = self.optimierungs_schritt_adaptiv_rollback(max_entfernen=self.max_entfernen_pro_iteration, u_max=self.u_max_grenze)

        # Verlauf speichern
        self.verlauf.append({
            "iteration": self.aktuelle_iteration,
            "aktive_knoten": aktive_knoten,
            "material_anteil": materialanteil,
            "entfernt": entfernt_n,
            "entfernte_ids": entfernte_ids,
            "max_u": max_u,
            "gesamtenergie": gesamtenergie,
            "u_max_grenze": self.u_max_grenze
        })

        self.aktuelle_iteration += 1

        # falls kein Fortschnritt mehr möglich ist
        if not ok or entfernt_n == 0:
            self.optimierung_beendet = True
            self.abbruch_grund = "Kein weiterer Fortschritt mehr möglich"
            return False
        
        return True
    
    # Funktion welchen uns den aktuellen optimierungszustand speichert
    def zustand_exportieren(self):
        return {
            "struktur": self.struktur,
            "optimierung": {
                "optimierung_initialisiert": self.optimierung_initialisiert,
                "optimierung_beendet": self.optimierung_beendet,
                "abbruch_grund": self.abbruch_grund,
                "start_knotenanzahl": self.start_knotenanzahl,
                "ziel_materialanteil": self.ziel_materialanteil,
                "max_iterationen": self.max_iterationen,
                "max_entfernen_pro_iteration": self.max_entfernen_pro_iteration,
                "u_faktor": self.u_faktor,
                "u_start_max": self.u_start_max,
                "u_max_grenze": self.u_max_grenze,
                "aktuelle_iteration": self.aktuelle_iteration,
                "verlauf": self.verlauf
            }
        }
    
    # Funktion welche uns einen gespeicherten zustand wieder gibt
    def zustand_importieren(self, daten):
        self.struktur = daten["struktur"]
        opt = daten["optimierung"]

        self.optimierung_initialisiert = opt["optimierung_initialisiert"]
        self.optimierung_beendet = opt["optimierung_beendet"]
        self.abbruch_grund = opt["abbruch_grund"]
        self.start_knotenanzahl = opt["start_knotenanzahl"]
        self.ziel_materialanteil = opt["ziel_materialanteil"]
        self.max_iterationen = opt["max_iterationen"]
        self.max_entfernen_pro_iteration = opt["max_entfernen_pro_iteration"]
        self.u_faktor = opt["u_faktor"]
        self.u_start_max = opt["u_start_max"]
        self.u_max_grenze = opt["u_max_grenze"]
        self.aktuelle_iteration = opt["aktuelle_iteration"]
        self.verlauf = opt["verlauf"]


    def optimierung(self, ziel_anteil=0.35, max_iter=50, max_entfernen_pro_iter=3, u_faktor=1.5):
        
        self.optimierung_initialisieren(ziel_anteil, max_iter, max_entfernen_pro_iter, u_faktor)
        while not self.optimierung_beendet:
            self.optimierung_schritt()

        return self.verlauf
    



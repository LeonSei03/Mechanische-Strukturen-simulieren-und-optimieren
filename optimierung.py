from solver import solve
import numpy as np
from struktur import Struktur
from graph_strategien import dijkstra_lastpfad, knoten_in_ring_nachbarschaft

class TopologieOptimierer:
    """ 
    Grundidee der Optimierung in der Klasse Topologieoptimierung

    Wir lösen in jeder Iteration das System und geben jedem Knoten einen Score. Knoten mit kleinem 
    Score sind weniger relevan und werden zuerst entfernt. Das passiert adaptiv, also zuerst werden viele Knoten entfernt, 
    wenn eine Bedingung verletzt wird, passiert ein Rollback und es werden versucht weniger Knoten zu entfernen. Das passiert bis der 
    gewünschte Materialanteil erreiht wird, die Iterationen ausgehen oder die Bedingungen unten nciht mehr erfüllt werden können. 

    Sicherheit gibt es durch:
    - Connectivity Check, wo geschaut wird ob die Lastknoten mit den Lagerknoten verbunden sind
    - Rollback strategie, wenn u_max überschritten wird oder Matrix singulär wird, pasiert ein Rollback und es wird der vorherige Zustand wieder genommen
    - Inseln und isolierte Knoten werden entfernt
    """
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

        # für den neuen optimierungsalgorithmus (aus der HUE mit den streckenoptimierungen von einer Stadt zur anderen)
        self.strategie = "dijkstra"
        self.dijkstra_neighbor_ring = 2
        self.dijkstra_eps = 1e-12

        # Problem das die Dehnung explodiert, nun ein cap, damit diese "explosion" nicht passiert
        self.u_cap_factor = 3.0 # hier nun zb. 5 Mal die Startverschiebung als Grenze
        self.u_alpha = 0.3
        self.u_max_running = None

    def berechne_startverschiebung(self):
        """
        Damit lösen wir einmal die Anfansstruktur um die maximale verschiebung zu bestimmen.
        Diese Verschiebung dient dann als Referenz, um später die Verschiebungsgrenze für die 
        Optimierung zu bestimmen.

        Return:
            max_u -> max. Verschiebung der Startstruktur
        """

        # GLS aufbauen und lösen
        K, F, fixiert, mapping = self.struktur.system_aufbauen()
        u = solve(K.copy(), F, fixiert)

        if u is None:
            raise RuntimeError("Startstruktur ist nicht lösbar!!")

        # max Verschiebung
        max_u = float(np.max(np.abs(u)))
        return max_u

    def feder_energien_berechnen(self):
        """
        Baut das globale GLS K*u=F auf, löst dieses und berechnet pro aktiver
        die gespeicherte Federenergie

        Returns:
            tuple:
                energien (dict[int, float]): {feder_id: energie}
                u (np.ndarry): Verschiebungsvektor
                mapping: (dict[int, tuple[int, int]]): Zuordnung Knoten -> DOF Indizes
                (K,F,fixiert)
        """

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

    def knoten_scores_berechnen(self):
        """
        Auf basis der Federenergien werden die Scores der Knoten berechnet.

        Idee:
        Die Federenergie wird halb halb auf beide Endknoten verteilt. Dh Knoten mit 
        kleinem Score hängen an einer Feder mit wenig Energie und nimmt somit nicht viel Last auf und können entfernt werdne.

        Zudem wird ein smoothing über die Nachbarschaft durchgeführt, damit wir weniger Ausreißer haben
         - Score wird gemittelt mit den Nachbar Scores

        Returns:
            scores(dict[int,float]): gefilterte Scores pro Knoten
            energien(dict[int,float]): Energien pro Feder
            u(np.ndarray): Verschiebung
            mapping(dict): DOF-Mapping
        """
        out = self.feder_energien_berechnen()
        
        if out[0] is None:
            return None, None, None, None
        
        energien, u, mapping, _ = out

        # scores für jeden aktiven Knoten initialisieren
        scores = {k_id: 0.0 for k_id in mapping.keys()}

        # jeder Feder die halbe Energie geben
        for f_id, E in energien.items():
            feder = self.struktur.federn[f_id]
            for k_id in [feder.knoten_i, feder.knoten_j]:
                if k_id in scores:
                    scores[k_id] += 0.5 * E

        #filterung bzw smoothing der werte somit entfernt die optimierung eher sinnvolle Bereiche statt ausreisser
        adj = self.struktur.nachbarschaft()
        gefilterte_scores = {}
        for k_id, score in scores.items():
            nachbarn = adj.get(k_id, [])
            if nachbarn:
                #Mittelwert aus dem eingenwert und dem Nachbarn
                gefilterte_scores[k_id] = (score + sum(scores[nb] for nb in nachbarn)) / (1 + len(nachbarn))
            else: 
                #falls kein Nachbar unverändert
                gefilterte_scores[k_id] = score 

        return gefilterte_scores, energien, u, mapping

    # Funktion um Knoten mit geringster Energie auszuwählen
    def auswahl_knoten_zum_entfernen(self, scores, anzahl, energien=None, u=None, mapping=None, verboten=None):
        """
        Wählt die Knoten mit geringster Energie aus, um entfernt zu werden. 
        Wenn bei Dijkstra zu wenig Knoten übrig bleiben, wird der Ringschutz kurz entfernt um noch Kandidaten zu finden.

        Returns:
            list[int] -> Liste der Knoten IDs zum entfernen
        """

        kritisch = self._kritische_knoten_ids_nach_strategie(energien, u=u, mapping=mapping)
        
        if verboten is None:
            verboten = set()

        kandidaten = [
            (k_id, score) for k_id, score in scores.items()
            if not self.struktur.knoten_geschuetzt(k_id) and (k_id not in kritisch) and (k_id not in verboten)]

        # erst ohne Nachbarn, dann notfalls komplett ohne Lastpfad-Filter
        if len(kandidaten) < anzahl and self.strategie == "dijkstra":

            # nur einen Pfad schützen
            ring_backup = self.dijkstra_neighbor_ring
            self.dijkstra_neighbor_ring = 0
            
            kritisch = self._kritische_knoten_ids_nach_strategie(energien, u=u, mapping=mapping)
            self.dijkstra_neighbor_ring = ring_backup

            kandidaten = [
                (k_id, score) for k_id, score in scores.items()
                if not self.struktur.knoten_geschuetzt(k_id)
                and (k_id not in kritisch)
                and (k_id not in verboten)]

        # letzter Fallback
        if len(kandidaten) < anzahl:
            kandidaten = [
                (k_id, score) for k_id, score in scores.items()
                if not self.struktur.knoten_geschuetzt(k_id)]

        # kleinster Score zuerst
        kandidaten.sort(key=lambda x: x[1])
        return[k_id for k_id, _ in kandidaten[:anzahl]]
    
    def optimierungs_schritt_adaptiv_rollback(self, max_entfernen, u_max=None):
        """
        Führt einen Optimierungsschritt mit adaptivem Rollback aus.
        Grober Ablauf:
        1) Scores berechnen
        2) Versuche n Knoten zu entfernen (n = max_entfernen, ..., 1)
        3) Nach Entfernen prüfen:
           - Connectivity (Last mit Lager verbunden?)
           - Solve-Test (System lösbar?)
           - u_max (max. Verschiebung <= Grenze?)
        4) Wenn eine Bedingung verletzt ist:
           - Rollback auf Snapshot
           - n reduzieren bzw. Kandidaten in dieser Iteration verbieten
        5) Wenn erfolgreich:
           - Inseln entfernen
           - isolierte Knoten entfernen
           - Energie für Verlauf berechnen
        """
        
        print("max_entfernen =", max_entfernen)
        
        # knotenscores berechnen basiert auf energie der federn
        scores, energien, u, mapping = self.knoten_scores_berechnen()

        if scores is None:
            return False, 0, [], None, None
        
        # kleine debug ausgabe
        print("Kandidaten total:", len([k for k in scores.keys() if not self.struktur.knoten_geschuetzt(k)]))
        verboten = set()

        # adaptives entfernen der knoten
        for n in range(max_entfernen, 0, -1):

            # knoten mit niedrigstem score aussuchen
            entfernte_ids = self.auswahl_knoten_zum_entfernen(scores, n, energien=energien, u=u, mapping=mapping, verboten=verboten)
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
                print(f"[Rollback]  n={n} - Connectivity verletzt")
                self.zustand_wiederherstellen(snapshot)
                continue

            # system neu aufbauen und lösen
            K, F, fixiert, mapping = self.struktur.system_aufbauen()
            u_test = solve(K.copy(), F, fixiert)

            # falls Matrix singulär ist, passiert Rollback
            if u_test is None:
                print(f"[Rollback]  n={n} - Matrix Singulär")
                self.zustand_wiederherstellen(snapshot)
                #hier auch kandidaten aus Iteration nehmen damit man nicht stecken bleibt 
                verboten.update(entfernte_ids)
                continue

            # max Verschiebung darf nicht zu groß sein
            max_u_val = float(np.max(np.abs(u_test)))

            # wenn max Verschiebung zu groß ist Rollback
            if u_max is not None and max_u_val > u_max:
                print(f"[Rollback]  n={n} - u_max überschritten ({max_u_val:.4e} > {u_max:.4e})")
                self.zustand_wiederherstellen(snapshot)
                # Kandidaten aus der Iteration nehmen
                verboten.update(entfernte_ids)
                
                continue
            
            # Inseln entfernen
            inaktive_inseln = self._inaktive_inseln_entfernen()

            # lose einzelknoten entfernen
            lose = self.struktur.knoten_ohne_federn_entfernen()

            # gesamtenergie für verlauf Plot nachher speichern
            energien2, u2, mapping2, _ = self.feder_energien_berechnen()
            gesamtenergie = float(sum(energien2.values()))

            # Gesamte entfernten Knoten aufzählen
            gesamt_entfernt = inaktive_inseln + len(entfernte_ids)

            return True, gesamt_entfernt, entfernte_ids, max_u_val, gesamtenergie

        return False, 0, [], None, None

    def zustand_sichern(self):
        """
        Sichert den aktuellen Zustand der Struktur, also alle aktiven Knoten und Federn
        """
        return{
            "aktive_knoten": set(self.struktur.aktive_knoten_ids()),
            "aktive_federn": set(self.struktur.aktive_federn_ids())}

    def zustand_wiederherstellen(self, snapshot):
        """
        Stellt der Zustand der Struktur aus einem Snapshot wieder her.

        Argumente:
            snapshot(dict) -> Rückgabe von der Methode 'zustand_sichern()'
        """
        aktive_knoten = snapshot["aktive_knoten"]
        aktive_federn = snapshot["aktive_federn"]

        # Knoten zurücksetzen
        for k_id, knoten in self.struktur.knoten.items():
            knoten.knoten_aktiv = (k_id in aktive_knoten)

        # Federn zurücksetzen
        for f_id, feder in self.struktur.federn.items():
            feder.feder_aktiv = (f_id in aktive_federn)

    def optimierung_initialisieren(self, ziel_anteil=0.35, max_iter=50, max_entfernen_pro_iter=3, u_faktor=1.5, strategie="energie", dijkstra_neighbor_ring=0):
        """ 
        Initialisiert uns einen neuen Optimierungslauf.
        """
        
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

        self.strategie = strategie
        self.dijkstra_neighbor_ring = dijkstra_neighbor_ring

        self.u_max_running = self.u_max_grenze 

    def optimierung_schritt(self):
        """
        Führt eine Optimierungsiteration aus.
        -> Prüft die Abbruchbedingungen
        -> Bestimmt wie viele Knoten max entfernt werden dürfen
        -> Ruft Methode 'optimierungs_schritt_adaptiv_rollback()' auf
        -> Speichert Daten für Plots

        Returns:
            bool: 
                True -> Optimierungsschritt erfolgreich
                False -> Optimierung beendet
        """
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
        
        # Zielmaterial nun auf Anzahl der Knoten übertragen, das wir bei erreichter Anzahl an Knoten abbrechen
        ziel_knoten_menge = int(np.ceil(self.ziel_materialanteil * self.start_knotenanzahl))
        entfernbare_knoten = aktive_knoten - ziel_knoten_menge
        max_entfernen_bei_dieser_iter = min(self.max_entfernen_pro_iteration, max(0, entfernbare_knoten)) 

        # nun Dynamische u_max Grenze, also relativ zur aktuellen Struktur, weil davor viele Abbrüche wegen dem u_max
        out = self.feder_energien_berechnen()
        if out[0] is None:
            self.optimierung_beendet = True
            self.abbruch_grund = "Struktur nicht lösbar (vor Schritt)"
            return False

        u_max_limit = float(self.u_max_grenze)

        # Funktion "optimierungs_schritt_adaptiv_rollback" aufrufen und durchführen
        ok, entfernt_n, entfernte_ids, max_u, gesamtenergie = self.optimierungs_schritt_adaptiv_rollback(max_entfernen=max_entfernen_bei_dieser_iter, u_max=u_max_limit)

        # Verlauf speichern
        self.verlauf.append({
            "iteration": self.aktuelle_iteration,
            "aktive_knoten": aktive_knoten,
            "material_anteil": materialanteil,
            "entfernt": entfernt_n,
            "entfernte_ids": entfernte_ids,
            "max_u": max_u,
            "gesamtenergie": gesamtenergie,
            "u_max_grenze": u_max_limit
        })

        self.aktuelle_iteration += 1

        # falls kein Fortschnritt mehr möglich ist
        if not ok or entfernt_n == 0:
            self.optimierung_beendet = True
            self.abbruch_grund = "Kein weiterer Fortschritt mehr möglich"
            return False
        
        return True
    
    def zustand_exportieren(self):
        """
        Exportiert den Optimierungszustand für die Checkpoints.
        """
        randbedingungen = {}
        for k_id, k in self.struktur.knoten.items():
            randbedingungen[int(k_id)] = {
                "lager_x_fix": bool(k.fix_x),
                "lager_z_fix": bool(k.fix_z),
                "kraft_x": float(k.kraft_x),
                "kraft_z": float(k.kraft_z),
                "knoten_aktiv": bool(k.knoten_aktiv)
            }

        return {
            "struktur": self.struktur,
            "randbedingungen": randbedingungen,
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

    def zustand_importieren(self, daten):
        """
        Importiert den zuvor gespeicherten Zustand, also den Checkpoint

        Argumente:
            daten(dict): Rückgabe der MEthode 'zustand_exportieren()'
        """
        self.struktur = daten["struktur"]
        opt = daten["optimierung"]

        rand = daten.get("randbedingungen", None)
        if rand is not None:
            for k_id, rb in rand.items():
                k_id = int(k_id)

                if k_id not in self.struktur.knoten:
                    continue

                k = self.struktur.knoten[k_id]

                k.fix_x = bool(rb.get("lager_x_fix", False))
                k.fix_z = bool(rb.get("lager_z_fix", False))

                k.kraft_x = float(rb.get("kraft_x", 0.0))
                k.kraft_z = float(rb.get("kraft_z", 0.0))
                
                if "knoten_aktiv" in rb:
                    k.knoten_aktiv = bool(rb["knoten_aktiv"])

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
    

    def _hauptkomponente_ids(self):
        """
        Bestimmt die Knoten-IDs die Last aufnehmen, also die mechanisch relevanten Knoten. 
        Damit versuchen wir zu verhindern das random Knoten und Feder Stränge übrig bleiben nach dem Optimieren, welche gar keine Last aufnehmen.
        Gehen mit BFS durch den aktiven Graphen um die Hauptkomponente zu finden. 
        """
        # aktive Knoten holen
        adj = self.struktur.nachbarschaft()

        # Startknoten wählen, entweder bei Lastknoten, sonst bei erstem Lager
        last_ids = self.struktur.last_knoten_id()
        if last_ids:
            start = last_ids[0]
        else: 
            lager_ids = self.struktur.lager_knoten_id()
            start = lager_ids[0] if lager_ids else None

        # falls wir keinen start haben
        if start is None or start not in adj:
            return set()

        # mit BFS durch den Graphen
        visited = {start}
        queue = [start]

        while queue:
            v = queue.pop(0)
            for nb in adj.get(v,[]):
                if nb not in visited:
                    visited.add(nb)
                    queue.append(nb)
        return visited

    def _inaktive_inseln_entfernen(self):
        """
        Soll alle aktiven Knoten, welche nicht zur Hauptkomponente gehören (also keine Last aufnehmen) entfernen
        """
        haupt = self._hauptkomponente_ids()

        # falls keine inaktive Insel da ist, abbrechen
        if not haupt:
            return 0
        
        entfernt = 0
        aktive_ids = list(self.struktur.aktive_knoten_ids())

        for k_id in aktive_ids:
            # wenn der Knoten nicht in der hauptkomponente ist kommt er weg
            if k_id not in haupt:

                if self.struktur.knoten_geschuetzt(k_id):
                    continue

                self.struktur.knoten_entfernen(k_id)
                entfernt += 1
        
        return entfernt


    def _kritische_knoten_ids(self, include_neighbors=True):
        """
        Baut uns eine Menge von kritischen Knoten die wir in der Kandidatenauswahl nicht entfernen wollen.
        """

        kritisch = set()
        pfade = self.struktur.finde_lastpfad_knoten()

        if not pfade:
            return kritisch
        
        # wenn ein einzelner Pfad als Liste zurückkommt
        if isinstance(pfade, list) and pfade and isinstance(pfade[0], int):
            pfad_liste = [pfade]
        else:
            pfad_liste = pfade

        for pfad in pfad_liste:
            kritisch.update(pfad)

        if include_neighbors and kritisch:
            adj = self.struktur.nachbarschaft()
            nachbarn = set()
            for k in kritisch:
                for nb in adj.get(k, []):
                    nachbarn.add(nb)
            kritisch.update(nachbarn)

        return kritisch
    
    def _kritische_knoten_ids_nach_strategie(self, energien=None, u=None, mapping=None):
        """
        Gibt uns die Knoten zurück die nicht entfernt werden dürfen.
        Ist nur für die Dijkstra Strategie.

        Returns:
            set[int]: Menge der kritischen Knoten-IDs
        """

        if self.strategie != "dijkstra" or energien is None or u is None or mapping is None:
            return set()

        kraefte = self.struktur.feder_kraefte_aus_u(u, mapping, betrag=True)
        
        # Dijsktra Pfad berechnen
        pfad = dijkstra_lastpfad(self.struktur, kraefte, eps=self.dijkstra_eps, weight_mode="inv_force")

        if not pfad:
            return set()
        
        kritisch = set(pfad)

        # Optional Nachbarschaft hinzufügen
        if self.dijkstra_neighbor_ring > 0:
            kritisch = knoten_in_ring_nachbarschaft(self.struktur, kritisch, ring=self.dijkstra_neighbor_ring)

        return kritisch

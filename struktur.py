from knoten import Knoten
from feder import Feder
import numpy as np

# Klasse die das Gerüst der mechanischen Struktur aufbaut auf den Knoten und den Federn
class Struktur:
    def __init__(self):
        # dictionary für alle Knoten und Feder, keine Listen, weil sich beim Löschen dann die Indices ändern würde
        self.knoten: dict[int, Knoten] = {}
        self.federn: dict[int, Feder] = {}
        self.knoten_id_zaehler = 0
        self.feder_id_zaehler = 0

        # Anzahl der Knoten in x- und in z-Richtung
        self.anzahl_x = None
        self.anzahl_z = None

    def knoten_hinzufuegen(self, x: float, z: float) -> int:
        """
        Fügt der Struktur einen neuen Knoten hinzu.

        Argumente:
            x (float): x-Koordinate
            z (float): z-Koordinate

        Returns:
            int: Knoten-ID
        """
        k_id = self.knoten_id_zaehler

        self.knoten[k_id] = Knoten(id=k_id, x=x, z=z) # im dictionary jeden neuen Knoten abspeichern
        self.knoten_id_zaehler += 1
        return k_id

    def gitter_erzeugen_knoten(self, anzahl_x: int, anzahl_z: int, dx: float, dz: float):
        """
        Erzeugt ein regelmäßiges Knotengitter.
        Die Knoten werden zeilenweise (j, i) angelegt und erhalten IDs nach:
            k_id = j * anzahl_x + i
        
        Argumente:
            anzahl_x (int): Anzahl Knoten in x-Richtung
            anzahl_z (int): Anzahl Knoten in z-Richtung
            dx (float): Abstand zwischen Knoten in x
            dz (float): Abstand zwischen Knoten in z
        """
        self.anzahl_x = anzahl_x
        self.anzahl_z = anzahl_z

        # Gitter bauen im dictionary mit ganz vielen Knoten
        for j in range(anzahl_z):
            for i in range(anzahl_x):
                x = i * dx # dx als Abstand zwischen den Knoten, also die Federlänge dann
                z = j * dz

                self.knoten_hinzufuegen(x, z)

    def feder_hinzufuegen(self, knoten_i: int, knoten_j: int, steifigkeit: float) -> int:
        """
        Fügt eine Feder zwischen zwei Knoten hinzu

        Argumente:
            knoten_i (int): ID des ersten Knotens
            knoten_j (int): ID des zweiten Knotens
            steifigkeit (float): axiale Federsteifigkeit (k)

        Returns:
            int: Feder-ID
        """
        f_id = self.feder_id_zaehler

        self.federn[f_id] = Feder(id=f_id, knoten_i=knoten_i, knoten_j=knoten_j, steifigkeit=steifigkeit)
        self.feder_id_zaehler += 1
        return f_id

    def knoten_id(self, i: int, j: int) -> int:
        """
        Berechnet die Knoten-ID im Gitter

        Argumente:
            i (int): Index in x-Richtung
            j (int): Index in z-Richtung

        Returns:
            int: Knoten-ID
        """
        return j * self.anzahl_x + i


    def gitter_erzeugen_federn(self, k_h: float, k_v: float, k_d: float): # WICHTIG: ich weiß nicht ob die steifigkeiten der federn unterschiedlich sind je nachdem ob sie hori, verti, dia sind. also mal drei verschiedene Steifigkeiten die übergeben werden müssen
        """
        Funktion um das Gitter aus den Federn zu erzeugen, Feder kommt immer zwischen zwei benachbarte Knoten

        Argumente:
            k_h (float): Steifigkeit horizontaler Federn
            k_v (float): Steifigkeit vertikaler Federn
            k_d (float): Steifigkeit diagonaler Federn
        """
        # über alle knoten drüber iterieren und eine feder dazwischen abspeichern, x richutng, z richtung und diagonal
        for j in range(self.anzahl_z):
            for i in range(self.anzahl_x):

                a = self.knoten_id(i, j) # aktuelle Knoten ID abspeichern

                # Feder zwischen aktuellem Knoten (a) und Knoten rechts davon
                if i + 1 < self.anzahl_x:
                    b = self.knoten_id(i+1, j)
                    self.feder_hinzufuegen(a, b, k_h)

                # Feder zwischen a und drunter liegendem Knoten
                if j + 1 < self.anzahl_z:
                    c = self.knoten_id(i, j+1)
                    self.feder_hinzufuegen(a, c, k_v)

                # Feder zwischen a und diagonal liegendem Knoten, rechts oben und unten rechts
                if i + 1 < self.anzahl_x and j + 1 < self.anzahl_z:
                    d = self.knoten_id(i + 1, j + 1) # Feder diagonal negative Steigung (zweiter Knoten rechts unterhalb von a)
                    self.feder_hinzufuegen(a, d, k_d)

                    # Feder diagonal positive Steigung (gehen mit ausgangsknoten eins rechts und zweiten Knoten eins nach unten)
                    e = self.knoten_id(i + 1, j)
                    f = self.knoten_id(i, j + 1)
                    self.feder_hinzufuegen(e, f, k_d)


    def knoten_entfernen(self, k_id: int):
        """
        Deaktiviert einen Knoten sowie alle zugehörigen Federn.
        Es werden geschützte Knoten berücksichtigt.

        Argumente:
            k_id (int): Knoten-ID
        """
        if k_id not in self.knoten: #exisitert der knoten? 
            return
        if self.knoten_geschuetzt(k_id): #schutz am anfang prüfen 
            return

        self.knoten[k_id].knoten_aktiv = False #Knoten deaktivieren 

        for feder in self.federn.values(): #federn am knoten deaktivieren 
            if feder.feder_aktiv and (feder.knoten_i == k_id or feder.knoten_j == k_id):
                feder.feder_aktiv = False
  

    # Funktion zum deaktivieren von Federn, für die Optimierung
    def feder_entfernen(self, f_id: int):
        if f_id in self.federn:
            self.federn[f_id].feder_aktiv = False

    def knoten_geschuetzt(self, k_id: int) -> bool:
        """
        Funktion um Knoten zu schützen, dass sie nicht entfernt werden können

        Returns:
            bool: True wenn geschützt, ansonsten False
        """
        k = self.knoten[k_id]
        return (k.fix_x or k.fix_z or k.kraft_x != 0 or k.kraft_z != 0)
    
    #Funktion für Rückgabe aller aktiven Knoten 
    def aktive_knoten_ids(self) -> list[int]:
        return[k_id for k_id, k in self.knoten.items() if k.knoten_aktiv]
    
    #Funktion für Rückgabe aller aktiven Federn 
    def aktive_federn_ids(self) -> list[int]:
        return[f_id for f_id, f in self.federn.items() if f.feder_aktiv]
    
    def dof_map(self):
        """
        Erstellt ein DOF Mapping für alle aktiven Knoten
        Jeder aktive Knoten hat zwei Freiheitsgrade
        -> u_x 
        -> u_z

        Returns:
            dict[int, tuple[int,int]]:
                {knoten_id: (index_x, index_z)}
        """

        #nur aktive Knoten interessieren uns für gleichungssysteme
        aktive_knoten = self.aktive_knoten_ids()

        #sortieren damit die reihenfolge reproduzierbar bleibt
        aktive_knoten.sort()

        #Dictionary für zuordnung (Knoten-ID (index_x, index_z))
        mapping = {}

        #freiheitsgradzähler
        freiheitsgrad_index = 0

        #jeder knoten hat 2 dof
        for knoten_id in aktive_knoten:
            mapping[knoten_id] = (freiheitsgrad_index, freiheitsgrad_index + 1) #Tupel
            freiheitsgrad_index += 2 #um zwei erhöhen weil 2 dof 

        return mapping
    
    def fixierte_freiheitsgrade(self, dof_mapping):
        """
        Funktion zur bestimmung der definierten Freiheitsgrade (Lagerbedingungen).
    
        Argumente:
            dof_mapping (dict): Mapping aus 'dof_map'

        Returns:
            list[int]: Liste der globalen DOF-Indizes, die auf 0 gesetzt werden
        """
        #indizes sammeln bei denen die verschiebung auf 0 gesetzt wird (Lager)
        fixierte_indizes = []

        for knoten_id, (index_x, index_z) in dof_mapping.items():

            knoten = self.knoten[knoten_id]

            if knoten.fix_x:
                fixierte_indizes.append(index_x)

            if knoten.fix_z:
                fixierte_indizes.append(index_z)
        
        return fixierte_indizes
    
    def kraftvektor_aufbauen(self, dof_mapping):
        """
        Funktion zur erzeugung des globalen kraftvektors K * u = F

        Argumente:
            dof_mapping (dict): Mapping aus 'dof_map'

        Returns:
            np.ndarray: globaler Kraftvektor F
        """
        anzahl_freiheitsgrade = 2 * len(dof_mapping) #2 weil jeder Knoten zwei dof besitzt

        #Kraftvektor mit 0 initialisieren 
        F = np.zeros(anzahl_freiheitsgrade)

        for knoten_id, (index_x, index_z) in dof_mapping.items():

            knoten = self.knoten[knoten_id]

            #die am knoten gespeicherten Kräfte werden an die richtige Stelle im vektor geschrieben
            F[index_x] += knoten.kraft_x
            F[index_z] += knoten.kraft_z

        return F
    
    # berechnung einheitsrichtungsvektor der Federn
    def feder_einheitsvektor(self, feder_id):
        """
        Berechnung des Einheitsrichtungsvektor der Federn.

        Argumente:
            feder_id (int): Feder-ID
        """
        feder = self.federn[feder_id]

        knoten_i = self.knoten[feder.knoten_i]
        knoten_j = self.knoten[feder.knoten_j]

        #Richtungsvektor 
        dx = knoten_j.x - knoten_i.x
        dz = knoten_j.z - knoten_i.z

        laenge = np.sqrt(dx**2 + dz**2)

        #Falls länge 0 sicherheit 
        if laenge == 0:
            raise ValueError("Feder hat Länge 0!!")
  
        #Einheitsvektor
        e = np.array([dx / laenge, dz / laenge])

        return e

    def lokale_feder_matrix(self, feder_id):
        """
        Berechnet die lokale 4x4 Steifigkeitsmatrix einer Feder im globalen Koordinatensystem.

        Argumente:
            feder_id (int): Feder-ID

        Returns:
            np.ndarray: 4x4 lokale Steifigkeitsmatrix
        """

        feder = self.federn[feder_id]

        #Einheitsrichtungsvekrot der Feder (von knoten i zu knoten j)
        e = self.feder_einheitsvektor(feder_id)
        ex, ez = e[0], e[1]

        k = feder.steifigkeit
    
        K_lokal = k * np.array([
            [ex*ex, ex*ez, -ex*ex, -ex*ez],
            [ex*ez, ez*ez, -ex*ez, -ez*ez],
            [-ex*ex, -ex*ez, ex*ex, ex*ez],
            [-ex*ez, -ez*ez, ex*ez, ez*ez]
        ])

        return K_lokal

    def steifigkeitsmatrix_aufbauen(self, dof_mapping):
        """
        Baut die globale Steifigkeitsmatrix K aus allen aktiven Federn auf.
        Jede Feder liefert einen 4x4 Beitrag, der in die globale Matrix
        an die passenden DOF-Indizes addiert wird.

        Argumente:
            dof_mapping (dict): Mapping aus 'dof_map()'

        Returns:
            np.ndarray: globale Steifigkeitsmatrix K
        """

        anzahl_freiheitsgrade = 2 * len(dof_mapping)

        #Leere globale Matrix erstellen 
        K_global = np.zeros((anzahl_freiheitsgrade, anzahl_freiheitsgrade))

        #über alle aktiven Federn iterieren
        for feder_id in self.aktive_federn_ids():

            feder = self.federn[feder_id]

            #lokale 4x4 matrix bestimmen
            K_lokal = self.lokale_feder_matrix(feder_id)

            #zugehörige Knoten 
            knoten_i = feder.knoten_i
            knoten_j = feder.knoten_j

            #globale dof indizes 
            ix, iz = dof_mapping[knoten_i]
            jx, jz = dof_mapping[knoten_j]

            #Liste der 4 beteiligen dof 
            dofs = [ix, iz, jx, jz]

            #Lokale Matrix in globale Matrix einbauen 
            for a in range(4):
                for b in range(4):
                    K_global[dofs[a], dofs[b]] += K_lokal[a, b]

        return K_global
    
    #nun werden hier lager und kräfte definiert und gesetzt um systeme lösen zu können
    #Funktion setzt Lagerbedinungen an einem Knoten, in welche richtung verschiebungen nicht zugelassen werden 
    def lager_setzen(self, k_id: int, fix_x = False, fix_z = False) -> None: 

        #Kontrolle ob Knoten in dict existiert
        if k_id not in self.knoten:
            raise KeyError(f"Knoten {k_id} existiert nicht!!")
        
        k = self.knoten[k_id]
        k.fix_x = fix_x
        k.fix_z = fix_z

    #Funktion um eine Kraft an einem Knoten zu setzten
    def kraft_setzen(self, k_id = int, fx = 0.0, fz = 0.0) -> None: 

        #Kontrolle ob Knoten in dict existiert
        if k_id not in self.knoten:
            raise KeyError(f"Knoten {k_id} existiert nicht!!")

        k = self.knoten[k_id]
        k.kraft_x = fx
        k.kraft_z = fz
        
    #Funktionen um Lager und Kräfte wieder rückzusetzen/löschen 
    def lager_loeschen(self, k_id: int) -> None: 
        self.lager_setzen(k_id, fix_x=False, fix_z=False)

    def kraft_loeschen(self, k_id: int) -> None: 
        self.kraft_setzen(k_id, fx=0.0, fz=0.0)

    def system_aufbauen(self):
        """
        Baut das komplette lineare Gleichungssystem der Struktur K*u=F auf.

        Returns:
            tuple:
                K (np.ndarray): globale Steifigkeitsmatrix
                F (np.ndarray): globaler Kraftvektor
                fixiert (list[int]): Indizes fixierter Freiheitsgrade (Lager)
                mapping (dict): DOF-Mapping (knoten_id -> (ix, iz))
        """

        mapping = self.dof_map()
        K = self.steifigkeitsmatrix_aufbauen(mapping)
        F = self.kraftvektor_aufbauen(mapping)
        fixiert = self.fixierte_freiheitsgrade(mapping)

        return K, F, fixiert, mapping
    
    # Funktion um die Knoten ID's von den Lagern zurückzugeben
    def lager_knoten_id(self):
        return [
            k_id for k_id, k in self.knoten.items() if k.knoten_aktiv and (k.fix_x or k.fix_z)
        ]
    
    # Funktion um die Knoten ID's von den Knoten auf welche die Last direkt wirkt
    def last_knoten_id(self):
        return [
            k_id for k_id, k in self.knoten.items() if k.knoten_aktiv and (k.kraft_x != 0.0 or k.kraft_z != 0.0)
        ]
    
    #Funktionen für die Heatmap, hier hab ich Code von dir aus dem Optimierer übernommen, allerdings ohne die solve, weil bereits u berechnet 
    def feder_energien_aus_u(self, u, mapping):
        '''
        Berechnet die Energie jeder aktiven Feder aus der zuvor berechneten Verschiebung u!
        Hier wird nichts neu gelöst also kein (system_aufbauen, kein SOLVE)

        - reine Nachbearbeitung für die Darstellung im Plot
        
        Rückgabe:
        - energien: dict {f_id: Energie}
        '''
                
        energien = {}

        for f_id in self.aktive_federn_ids():
            feder = self.federn[f_id]

            # zur sicherheit für inaktive Endknoten
            if feder.knoten_i not in mapping or feder.knoten_j not in mapping:
                continue

            ix, iz = mapping[feder.knoten_i]
            jx, jz = mapping[feder.knoten_j]

            # Verschiebungsvektor (local)
            u_local = np.array([u[ix], u[iz], u[jx], u[jz]], dtype=float)

            # Steifigkeitsmatrix (local)
            K_local = self.lokale_feder_matrix(f_id)

            # Energie berechnen
            E = 0.5 * float(u_local.T @ K_local @ u_local)
            energien[f_id] = E 
        
        return energien
    
    #Ebenfalls sinngemäß aus Optimierung übernommen (keine neuberechnung hier quasi)
    def knoten_scores_aus_federenergien(self, energien, mapping, modus="halb"):
        '''
        Erzeugt Knotenwerte aus Federenergien (für die Knoten-Heatmap)

        modus: 
        - "halb": jeder Endknoten bekommt 0.5 * Energie (wie beim Opitmierer)
        - "summe": jeder Endknoten bekommt E

        Rückgabe: 
        - scores: dict {knoten_id: score}
        '''
        # scores für jeden aktiven Knoten initialisieren
        scores = {k_id: 0.0 for k_id in mapping.keys()}

        # jeder Feder die halbe Energie geben
        for f_id, E in energien.items():
            feder = self.federn[f_id]
            i = feder.knoten_i
            j = feder.knoten_j

            if modus == "halb":
                anteil = 0.5 * float(E)
            else: 
                anteil = float(E)

            if i in scores:
                scores[i] += anteil
            if j in scores:
                scores[j] += anteil
        
        return scores
    

    def feder_kraefte_aus_u(self, u, mapping, betrag=True):
        '''
        Berehnet pro aktiver Feder die axiale Federkraft N aus u

        Physik dahinter: 
        - delta = e * (u_j - u_i)
        N = k * delta

        betrag=True: 
        - gibt nur positive Werte zurück (Beträge)
        '''

        kraefte = {}

        for f_id in self.aktive_federn_ids():
            feder = self.federn[f_id]

            if feder.knoten_i not in mapping or feder.knoten_j not in mapping: 
                continue

            ix, iz = mapping[feder.knoten_i]
            jx, jz = mapping[feder.knoten_j]

            dux = float(u[jx] - u[ix])
            duz = float(u[jz] - u[iz])

            #Einheitsvektor Feder 
            e = self.feder_einheitsvektor(f_id) 
            delta = float(e[0] * dux + e[1] * duz)

            k = float(feder.steifigkeit)
            N = k * delta

            kraefte[f_id] = abs(N) if betrag else N 

        return kraefte

    def nachbarschaft(self):
        """
        Erzeugt eine Liste aus allen aktiven verbunden Knoten und Federn

        Returns:
            dict[int, list[int]]: {knoten_id: [nachbar_ids]}
        """
        aktive_knoten = set(self.aktive_knoten_ids())

        # für jeden aktiven Knoten eine leere Nachbarschaftsliste anlegen
        adj = {k_id: [] for k_id in aktive_knoten}

        # über alle aktiven Federn iterieren
        for f_id in self.aktive_federn_ids():
            f = self.federn[f_id]
            
            # endknoten der Feder abspeichern
            i = f.knoten_i
            j = f.knoten_j

            # wenn beide endknoten aktiv sind, kommen sie in die Liste
            if i in aktive_knoten and j in aktive_knoten:
                adj[i].append(j)
                adj[j].append(i)
        
        return adj
    
    def ist_verbunden_last_zu_lager(self):
        """
        Sagt ob mindestens ein aktiver Lastknoten über aktive Federn mit mindestens einem aktiven Lagerknotne verbunden ist
    
        Returns:
           bool: True wenn Connectivity erfüllt ist, ansonsten False
        """
        # aktuelle Last und lagerknoten bestimmen
        last_ids = self.last_knoten_id() or []
        lager_ids = self.lager_knoten_id() or []

        # falls keine Last oder Lager definiert sind
        if not last_ids or not lager_ids:
            return False
        
        adj = self.nachbarschaft()

        # Breitensuche von allen Lagerknoten
        visited = set(lager_ids)
        queue = list(lager_ids)

        while queue:
            # nächsten Knoten aus queue nehmen
            v = queue.pop(0)
            # alle direkten Nachbarn untersuchen
            for nb in adj.get(v, []):
                # nur weiter wenn dieser knoten noch nicht besucht wurde
                if nb not in visited:
                    visited.add(nb)
                    queue.append(nb)

        # Breitensuche für jeden Lastknoten machen
        for start_id in last_ids:
            if start_id not in visited:
                return False
            
        # gucken ob alle Lager untereinander verbunden sind
        for lag in lager_ids:
            if lag not in visited:
                return False
            
        return True
    
    # gibt eine Liste an Knoten ids zurück, welche auf dem Lastpfad zwischen Lastknoten und Lagerknoten liegen
    def finde_lastpfad_knoten(self):
        """
        Findet Pfade von Lastknoten zu Lagerknoten im aktiven Graphen.
        Hier wird eine ungewichtete Breitensuche verwendet.
        In der Dijkstra Strategie wird stattdessen ein gewichteter Pfad verwendet.

        Returns:
            list[list[int]] | None: Liste von Pfaden (je Lastknoten), oder None falls kein Pfad existiert.
        """
        # aktuelle Last- und Lagerknoten
        last_ids = self.last_knoten_id()
        lager_ids = set(self.lager_knoten_id())

        if not last_ids or not lager_ids:
            return None
        
        adj = self.nachbarschaft()
        alle_pfade = []

        for start_id in last_ids:
            if start_id not in adj:
                continue

            vorgaenger = {start_id: None}
            queue = [start_id]

            while queue:
                v = queue.pop(0)
                
                # wenn Lager erreicht wird Pfad rekonstruiert
                if v in lager_ids:
                    pfad = []
                    cur = v
                    while cur is not None:
                        pfad.append(cur)
                        cur = vorgaenger[cur]
                    pfad.reverse()
                    alle_pfade.append(pfad)
                
                for nb in adj.get(v, []):
                    if nb not in vorgaenger:
                        vorgaenger[nb] = v
                        queue.append(nb)

        if not alle_pfade:
            return None

        return alle_pfade


    # Funktion um die Aktiven Knoten Koordinaten zu speichern, für Plot
    def koordinaten_knoten(self):
        xs = []
        zs = []

        for k_id in self.aktive_knoten_ids():
            k = self.knoten[k_id]
            xs.append(k.x)
            zs.append(k.z)

        return xs, zs
    
    def koordinaten_knoten_mit_verschiebung(self, u, mapping, skalierung):
        """
        Funktion welche aktive Knotenkoordinaten plus die Verschiebungen zurückgibt        

        Returns:
            xs[list] -> Knotenposition in x plus dessen Verschiebung
            zs[list] -> Knotenposition in z plus dessen Verschiebung
        """ 
        xs = []
        zs = []

        for k_id in mapping.keys():
            k = self.knoten[k_id]
            ix, iz = mapping[k_id]

            # ursprüngliche Position + verschiebung mal Skalierung, skalierung je nachdem wie groß die Verschiebungen sind
            x_neu = k.x + skalierung * u[ix]
            z_neu = k.z + skalierung * u[iz]

            xs.append(x_neu)
            zs.append(z_neu)

        return xs, zs
    
    def knoten_ohne_federn_entfernen(self):
        """Entfernt aktive Knoten, welche keine aktiven Federn mehr dran hängen haben, um zu verhindern, dass random Knoten stehen bleiben"""

        # Grad zählen
        grad = {k_id: 0 for k_id in self.aktive_knoten_ids()}
        for f_id in self.aktive_federn_ids():
            f = self.federn[f_id]
            if f.knoten_i in grad: grad[f.knoten_i] += 1
            if f.knoten_j in grad: grad[f.knoten_j] += 1

        entfernt = 0
        for k_id, g in grad.items():
            if g == 0 and not self.knoten_geschuetzt(k_id):
                self.knoten_entfernen(k_id)
                entfernt += 1
        return entfernt
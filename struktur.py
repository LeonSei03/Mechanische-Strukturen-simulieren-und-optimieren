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

    # Funktion um Knotenobjekte zum Dict hinzuzufügen
    def knoten_hinzufuegen(self, x: float, z: float) -> int:
        k_id = self.knoten_id_zaehler

        self.knoten[k_id] = Knoten(id=k_id, x=x, z=z) # im dictionary jeden neuen Knoten abspeichern
        self.knoten_id_zaehler += 1
        return k_id


    # Funktion um das Gitter aus Knoten zu erzeugen
    def gitter_erzeugen_knoten(self, anzahl_x: int, anzahl_z: int, dx: float, dz: float):
        self.anzahl_x = anzahl_x
        self.anzahl_z = anzahl_z

        # Gitter bauen im dictionary mit ganz vielen Knoten
        for j in range(anzahl_z):
            for i in range(anzahl_x):
                x = i * dx # dx als Abstand zwischen den Knoten, also die Federlänge dann
                z = j * dz

                self.knoten_hinzufuegen(x, z)

    
    # Funktion um Federobjekte ins Dict zu schreiben
    def feder_hinzufuegen(self, knoten_i: int, knoten_j: int, steifigkeit: float) -> int:
        f_id = self.feder_id_zaehler

        self.federn[f_id] = Feder(id=f_id, knoten_i=knoten_i, knoten_j=knoten_j, steifigkeit=steifigkeit)
        self.feder_id_zaehler += 1
        return f_id


    # Funktion um aus einer Gitterposition die passende Knoten id zurückzugeben
    def knoten_id(self, i: int, j: int) -> int:
        return j * self.anzahl_x + i


    # Funktion um das Gitter aus den Federn zu erzeugen, Feder kommt immer zwischen zwei benachbarte Knoten
    def gitter_erzeugen_federn(self, k_h: float, k_v: float, k_d: float): # WICHTIG: ich weiß nicht ob die steifigkeiten der federn unterschiedlich sind je nachdem ob sie hori, verti, dia sind. also mal drei verschiedene Steifigkeiten die übergeben werden müssen
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


    # Funktion zum entfernen von Knoten, für die Optimierung
    def knoten_entfernen(self, k_id: int):

        if k_id not in self.knoten: #exisitert der knoten? 
            return
        if self.knoten_geschuetzt(k_id): #schutz am anfang prüfen 
            return

        self.knoten[k_id].knoten_aktiv = False #Knoten deaktivieren 

        for feder in self.federn.values(): #federn am knoten deaktivieren 
            if feder.feder_aktiv and (feder.knoten_i == k_id or feder.knoten_j == k_id):
                feder.feder_aktiv = False

#hab hier überarbeitet, zuerst geprüft ob knoten geschützt nicht später erst.... 

#        if k_id in self.knoten:
#            self.knoten[k_id].knoten_aktiv = False # knoten_aktiv Variable am Key k_id auf False setzen

        # alle Federn die am Knoten dran sind deaktivieren
#        for feder in self.federn.values():
#            if not feder.feder_aktiv:
#                continue
#            if self.knoten_geschuetzt(k_id):
#                return
#           if feder.knoten_i == k_id or feder.knoten_j == k_id:
#                feder.feder_aktiv = False
    

    # Funktion zum deaktivieren von Federn, für die Optimierung
    def feder_entfernen(self, f_id: int):
        if f_id in self.federn:
            self.federn[f_id].feder_aktiv = False


    # Funktion um Knoten zu schützen, dass sie nicht entfernt werden können
    def knoten_geschuetzt(self, k_id: int) -> bool:
        k = self.knoten[k_id]
        return (k.fix_x or k.fix_z or k.kraft_x != 0 or k.kraft_z != 0)
    
    #Funktion für Rückgabe aller aktiven Knoten 
    def aktive_knoten_ids(self) -> list[int]:
        return[k_id for k_id, k in self.knoten.items() if k.knoten_aktiv]
    
    #Funktion für Rückgabe aller aktiven Federn 
    def aktive_federn_ids(self) -> list[int]:
        return[f_id for f_id, f in self.federn.items() if f.feder_aktiv]
    
    #map der freiheitsgrade an richtiger position definieren
    def dof_map(self):

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
    
    #Funktion zur bestimmung der definierten Freiheitsgrade (Lagerbedingungen), gibt den Knotenindex zurück
    def fixierte_freiheitsgrade(self, dof_mapping):

        #indizes sammeln bei denen die verschiebung auf 0 gesetzt wird (Lager)
        fixierte_indizes = []

        for knoten_id, (index_x, index_z) in dof_mapping.items():

            knoten = self.knoten[knoten_id]

            if knoten.fix_x:
                fixierte_indizes.append(index_x)

            if knoten.fix_z:
                fixierte_indizes.append(index_z)
        
        return fixierte_indizes
    
    #Funktion zur erzeugung des globalen kraftvektors K * u = F
    def kraftvektor_aufbauen(self, dof_mapping):

        anzahl_freiheitsgrade = 2 * len(dof_mapping) #2 weil jeder Knoten zwei dof besitzt

        #Kraftvektor mit 0 initialisieren 
        F = np.zeros(anzahl_freiheitsgrade)

        for knoten_id, (index_x, index_z) in dof_mapping.items():

            knoten = self.knoten[knoten_id]

            #die am knoten gespeicherten Kräfte werden an die richtige Stelle im vektor geschrieben
            F[index_x] += knoten.kraft_x
            F[index_z] += knoten.kraft_z

        return F
    
    #berechnung einheitsrichtungsvektor der Federn
    def feder_einheitsvektor(self, feder_id):

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
    
    #Lokale 4x4 Steifigkeitsmatrix einer einzelnen Feder
    def lokale_feder_matrix(self, feder_id):
        

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